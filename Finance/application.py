import requests, json, base64
from requests.auth import HTTPBasicAuth
from datetime import datetime
from django.utils import timezone #type: ignore
from django.db.models import Sum, Avg, F  #type: ignore

from Students.models import Allocate_Student  #type: ignore

from .configs import api_settings
from .models import *
from .fee_manager import FeeManager

from Core.models import Term, Institution, CourseDuration

class IllegalPhoneNumberException(Exception):
	"""
	Raised when phone number is in illegal format.
	"""
	pass

def generate_invoice_number(term):
    """
    Generates a unique invoice number using:
    [Year][Term]-[CourseCode]-[RegNo]-[SequentialCount]
    """

    year = term.year.name.split("/")[0]  # e.g., '2023-2024' → '2023'

    # Count existing invoices for this student in the term (useful if allowing multiple invoices)
    existing_count = Invoice.objects.all().count() + 1

    # Format count as 3-digit number (001, 002, etc.)
    count_str = str(existing_count).zfill(3)

    # Final invoice number
    invoice_number = f"INV\\{year}\\{count_str}"

    return invoice_number

def format_phone_number(phone_number):
	"""
	Format phone number into the format 2547XXXXXXXX
	
	Arguments:
		phone_number (str) -- The phone number to format
	"""

	if len(str(phone_number)) < 9:
		raise IllegalPhoneNumberException('Phone number too short')
	else:
		return '254' + str(phone_number)[-9:]

def generate_pass_key(shortcode):
    time_stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    s = f"{shortcode}{api_settings.MPESA_PASSKEY}{time_stamp}"
    encoded = base64.b64encode(s.encode()).decode()
    return encoded, time_stamp

def get_mpesa_access_token(wallet=None):
    """
    Fetch OAuth access token from Safaricom M-Pesa API.
    If you support multiple wallets/paybills, map wallet -> consumer_key/secret.
    Otherwise, just use the default global app credentials.
    """
    token_url = f"{api_settings.SAFARICOM_API}/oauth/v1/generate?grant_type=client_credentials"

    # Decide which keys to use
    consumer_key = api_settings.MPESA_CONSUMER_KEY
    consumer_secret = api_settings.MPESA_CONSUMER_SECRET

    # Check if a valid token exists
    access_token = AccessToken.objects.filter(account_number=wallet).first()
    if access_token:
        delta = timezone.now() - access_token.created_at
        minutes = (delta.total_seconds() // 60)
        if minutes < 50:
            return access_token.token  # still valid
        else:
            access_token.delete()  # expired

    # Request a new token
    try:
        response = requests.get(
            token_url,
            auth=HTTPBasicAuth(consumer_key, consumer_secret)
        )
        response.raise_for_status()
        token = response.json().get("access_token")

        if token:
            AccessToken.objects.create(account_number=wallet, token=token, created_at=timezone.now())
        return token
    except requests.RequestException as e:
        print("Error fetching M-Pesa access token:", str(e))
        return None

def initiate_stk_push(phone_number: str, amount: int, paybill: str, account_reference: str, transaction_desc: str):
    access_token = get_mpesa_access_token(format_phone_number(phone_number))
    
    password, timestamp = generate_pass_key(paybill or api_settings.MPESA_SHORTCODE)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": int(paybill or api_settings.MPESA_SHORTCODE),
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": int(format_phone_number(phone_number)),
        "PartyB": int(paybill or api_settings.MPESA_SHORTCODE),
        "PhoneNumber": int(format_phone_number(phone_number)),
        "CallBackURL": api_settings.MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc,
    }

    url = f"{api_settings.SAFARICOM_API}/mpesa/stkpush/v1/processrequest"
    response = requests.post(url, headers=headers, json=payload)

    return response.json()

def query_stk_status(checkout_request_id):

    attempt = PaymentAttempt.objects.filter(checkout_request_id=checkout_request_id).first()
    if not attempt:
        return {
            "success": False,
            "message": "Payment attempt not found."
        }

    # Get access token
    access_token = get_mpesa_access_token(attempt.account_number)
    if not access_token:
        return {
            "success": False,
            "message": "Failed to acquire M-Pesa access token."
        }

    # Use provided shortcode or fallback to default
    shortcode = attempt.wallet.paybill or api_settings.MPESA_SHORTCODE

    password, timestamp = generate_pass_key(shortcode)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": int(shortcode),
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id
    }

    try:
        url = f"{api_settings.SAFARICOM_API}/mpesa/stkpushquery/v1/query"
        response = requests.post(url, headers=headers, json=payload)
        res_json = response.json()
        
        return res_json

    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Network error: {str(e)}"
        }

def create_receipt(attempt_id):
    try:
        attempt = PaymentAttempt.objects.get(id=attempt_id)
    except PaymentAttempt.DoesNotExist:
        print(f"PaymentAttempt with ID {attempt_id} not found.")
        return None

    try:
        institution = Institution.objects.first()
        current_term = Term.objects.get(
            name=institution.current_intake,
            year=institution.current_year
        )
    except Institution.DoesNotExist:
        print("Institution not configured.")
        return None
    except Term.DoesNotExist:
        print("Current term not found.")
        return None

    try:
        receipt = Receipt.objects.create(
            trans_id=attempt.ref_id,  # Ensure this field exists, or update to correct one
            student=attempt.student,
            wallet=attempt.wallet,
            term=current_term,
            amount=attempt.amount,
            cashier="System"
        )
        return receipt
    except Exception as e:
        print(f"Error creating receipt: {str(e)}")
        return None

def create_invoice(student_ids, voteheads, target):
    try:
        inst = Institution.objects.first()
        term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()

        students = Allocate_Student.objects.filter(id__in=student_ids)
        if not students.exists():
            return {"error": True,
                    "errMessage": "No valid students found."}

        for student in students:
            # Create Invoice Items
            part_ids = []
            part_name = ''
            for registry in voteheads:
                votehead = Account.objects.filter(id = registry["votehead"]).first()
                amount = registry["amount"]
                # Create a Fee Particular and add the fee particular id
                if target == "Course":
                    part_name = str(student.studentno.course.abbr) + "_" + str(votehead.votehead) + "_" + str(term.name)
                elif target == "Class":
                    part_name = str(student.Class.name) + "_" + str(votehead.votehead) + "_" + str(term.name)
                else:
                    part_name = str(student.studentno.regno) + "_" + str(votehead.votehead) + "_" + str(term.name)
                
                fee_narration = FeeParticular.objects.create(
                    name = part_name, 
                    course = student.Class.course, 
                    module = student.module, 
                    term = term, 
                    account = votehead, 
                    amount = amount,
                    target = target
                )
                part_ids.append(fee_narration)
                
            total_amount = sum(int(item.amount) for item in part_ids)

            # Create Invoice
            invoice = Invoice.objects.create(
                inv_no = generate_invoice_number(term), 
                student=student.studentno, 
                term=term, 
                amount=total_amount,
                state="Pending",
                is_cleared=False,
                paid_amount=0.00,
            )
            invoice.narration.set(part_ids)
            invoice.save()

        return {
            "success": True
        }
    except Exception as e:
        print(f"[ERROR]: {e}")
        return {
            "error":True,
            "errMessage": e}

def create_feestructure(course_id, voteheads):
    try:
        inst = Institution.objects.first()
        term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()

        course_duration = CourseDuration.objects.filter(id=course_id).first()
        if not course_duration:
            return {
                "error": True,
                "errorMessage": "No Course Found!"
            }
        
        feenarration = []
        
        for registry in voteheads:
            votehead = Account.objects.filter(id = registry["votehead"]).first()
            amount = registry["amount"]
            # Create a Fee Particular and add the fee particular id
            part_name = str(course_duration.course.abbr) + "_" + str(votehead.votehead) + "_" + str(term.name)

            fee_narration = FeeParticular.objects.create(
                name = part_name, 
                course = course_duration.course, 
                module = course_duration.module, 
                term = term, 
                account = votehead, 
                amount = amount,
                target = "Course"
            )
            feenarration.append(fee_narration.id)
        return {
            "success": True,
            "successMessage": f"{course_duration.course.abbr} {course_duration.module} Fee Structure Created Successfuly!",
            "feenarration": feenarration
        }
            
    except Exception as e:
        print(f"[ERROR]: {e}")
        return {
            "error":True,
            "errMessage": e}

def create_newterm_invoice(student_regno, term_id):
    try:
        target_term = Term.objects.get(id=term_id)
    except Term.DoesNotExist:
        print("Current term not found.")
        return "Current term not found."

    try:
        # Get the allocated student, including student and module info
        allocated_student = Allocate_Student.objects.get(studentno__regno=student_regno)
        student = allocated_student.studentno  # This is the actual Student instance
        module = allocated_student.module

        # Check if an invoice already exists for this student and term
        existing_invoice = Invoice.objects.filter(student=student, term=target_term).first()
        if existing_invoice:
            print(f"Invoice already exists for student {student_regno} in term {target_term}.")
            return existing_invoice

        # Get applicable fee particulars for this student's course, module, and term
        fee_narrations = FeeParticular.objects.filter(
            course=student.course,
            module=module,
            term=target_term,
            target = "Course"
        )

        if not fee_narrations.exists():
            print("No fee particulars found for this student and term.")
            return "No fee structure for this student."
        
        # Calculate total amount
        total_amount = sum(item.amount for item in fee_narrations)

        # Create the invoice without narration first (since it's ManyToMany)
        invoice = Invoice.objects.create(
            student=student,
            term=target_term,
            amount=total_amount,
            state="Pending",
            is_cleared=False,
            paid_amount=0.00,
            inv_no=generate_invoice_number(target_term)
        )
        
        # Now attach the many-to-many narration
        invoice.narration.set(fee_narrations)

        return invoice
    
    except Allocate_Student.DoesNotExist:
        print(f"Student with regno {student_regno} not found in allocation.")
        return f"Student with regno {student_regno} not found in allocation."

    except Exception as e:
        print(f"Unexpected error creating invoice: {str(e)}")
        return f"Error: {str(e)}"

def create_new_invoice(student_regno, term_id, fee_narration_ids):
    try:
        target_term = Term.objects.get(id=term_id)
    except Term.DoesNotExist:
        print("Current term not found.")
        return "Current term not found."

    try:
        # Get the allocated student, including student and module info
        allocated_student = Allocate_Student.objects.get(studentno__regno=student_regno)
        student = allocated_student.studentno  # This is the actual Student instance
        module = allocated_student.module

        # Check whether the student has a feestructure otherwise make a structure with the new changes else make a new invoice with the new changes
        fee_structure = Invoice.objects.filter(student = student, term = target_term)
        if fee_structure:
            # Calculate total amount
            fee_narrations = FeeParticular.objects.filter (id__in = fee_narration_ids)
        else:
            fee_narrations = FeeParticular.objects.filter(course = student.course, module = module, term = target_term, target = "Course")
        
        total_amount = sum(item.amount for item in fee_narrations)
        # Create the invoice without narration first (since it's ManyToMany)
        invoice = Invoice.objects.create(
            student=student,
            term=target_term,
            amount=total_amount,
            state="Pending",
            is_cleared=False,
            paid_amount=0.00,
            inv_no=generate_invoice_number(target_term)
        )
          
        # Now attach the many-to-many narration
        invoice.narration.set(fee_narrations)
        invoice.save()

        return invoice
    
    except Allocate_Student.DoesNotExist:
        print(f"Student with regno {student_regno} not found in allocation.")
        return f"Student with regno {student_regno} not found in allocation."

    except Exception as e:
        print(f"Unexpected error creating invoice: {str(e)}")
        return f"Error: {str(e)}"
    
def process_fee_allocation(reciept_id):
    try:
        # Get the amount
        receipt = Receipt.objects.filter(id = reciept_id).first()
        if not receipt:
            return {"success": False, "message": "Transaction not found."}
        
        amount_paid = receipt.amount
        amount_arrears = amount_paid

        # Default manager - Reciept's Student and Reciept's Term
        manager = FeeManager(receipt.student.regno, receipt.term.pk)

        # Check Pending Invoices 
        pending_invoices = Invoice.objects.filter(student=receipt.student, state="Pending").order_by("created_at")
        if pending_invoices:
            # Pay Pending Invoices
            for invoice in pending_invoices:
                invoice_due = invoice.get_balance_due()
                # If the amount is able to settle the invoice the proceed
                if amount_arrears <= 0:
                    break

                allocation = min(invoice_due, amount_arrears)
 
                # Link receipt to invoice
                ReceiptAllocation.objects.create(
                    receipt = receipt,
                    invoice = invoice,
                    amount = allocation
                )
                
                # Process the pending for the invoice
                manager = FeeManager(invoice.student.regno, invoice.term.pk)

                paid = manager.get_paid_records()
                structure = manager.get_invoice_items(invoice)
                priorities = manager.get_priorities()

                particular_balance = manager.get_particular_balance(structure, paid)
                priority_map = manager.filter_priorities(particular_balance, priorities)

                # Combine unpaid + priority for allocation
                distribution = {
                    account: (particular_balance[account], priority_map.get(account, 0))
                    for account in particular_balance
                }

                allocated_money = manager.allocate_payment(amount_arrears, distribution)

                manager.apply_payment(receipt, allocated_money)
 
                invoice.paid_amount += allocation
                invoice.save()

                if invoice.paid_amount == invoice.amount:
                    invoice.state = "Cleared"
                    invoice.is_cleared = True

                invoice.updated_at = datetime.now()
                invoice.save()

                amount_arrears -= allocation
        
        # Update the Fee Status
        manager.update_status(receipt.trans_id, amount_paid)

    except Exception as e:
        print("Error in async fee allocation:", str(e))

def get_historical_payment_rates():
    # Step 1: Get total invoice amount per course
    invoice_totals = (
        Invoice.objects
        .values(course_id=F('student__course'))
        .annotate(total_invoiced=Sum('amount'))
    )

    # Step 2: Get total allocated receipt amount per course
    receipt_totals = (
        Receipt.objects
        .values(course_id=F('student__course'))
        .annotate(total_received=Sum('amount'))
    )

    # Step 3: Convert to dictionary for fast lookup
    invoice_dict = {item['course_id']: item['total_invoiced'] or 0 for item in invoice_totals}
    receipt_dict = {item['course_id']: item['total_received'] or 0 for item in receipt_totals}

    # Step 4: Compute rates
    rates = {}
    for course_id in invoice_dict:
        invoiced = invoice_dict.get(course_id, 0)
        received = receipt_dict.get(course_id, 0)
        rate = received / invoiced if invoiced > 0 else 0.9  # default to 90%
        rates[course_id] = round(rate, 2)

    return rates

def get_course_fee(course):
    # Step 1: Get average amount per votehead (Account) for the course
    averages = (
        FeeParticular.objects
        .filter(course=course)
        .values('account')
        .annotate(avg_amount=Avg('amount'))
    )

    # Step 2: Sum up the averages
    total_fee = sum(item['avg_amount'] for item in averages)

    return round(total_fee, 2)