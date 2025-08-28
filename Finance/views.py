from rest_framework.views import APIView #type: ignore
from rest_framework import viewsets, status, permissions #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, permission_classes #type: ignore
from rest_framework.permissions import IsAuthenticated, AllowAny #type: ignore
from django.views.decorators.csrf import csrf_exempt #type: ignore
from django.http import JsonResponse #type: ignore
from rest_framework.pagination import PageNumberPagination #type: ignore
import json
from decimal import Decimal
from django.db.models import OuterRef, Subquery, F, DecimalField, Sum, Value as V#type: ignore
from django.db.models.functions import Coalesce, ExtractYear, TruncMonth #type: ignore
from django.views.decorators.http import require_POST #type: ignore
from collections import defaultdict, OrderedDict
from datetime import date
import calendar

from threading import Thread
from django.utils.dateparse import parse_datetime # type: ignore

from Core.models import Class, Department, CourseDuration, Course
from Students.models import Student, Allocate_Student
from Students.views import predict_applications

from .models import *
from .filters import *
from .serailizers import *
from .application import *

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'count': self.page.paginator.count,
        })
 
@csrf_exempt
@require_POST
def request_payment(request):
    try:
        body = json.loads(request.body)
        student_id = body.get("student_id")
        wallet_id = body.get("wallet_id")
        amount = int(body.get("amount", 0))

        if not student_id or not wallet_id or amount <= 0:
            return JsonResponse({"message": "Missing or invalid data."}, status=400)

        # Fetch Student
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return JsonResponse({"message": "Student not found."}, status=404)

        # Determine phone number
        if student.sponsor.name.upper() == "SELF":
            phone = student.phone
            payer_name = student.get_full_name()
        else:
            phone = student.sponsor.phone  # Ensure this field exists
            payer_name = student.sponsor.name

        if not phone:
            return JsonResponse({"message": "Phone number not available."}, status=400)

        # Fetch wallet to determine payment method
        try:
            wallet = Wallet.objects.get(id=wallet_id)
        except Wallet.DoesNotExist:
            return JsonResponse({"message": "Wallet not found."}, status=404)

        if wallet.payment_method.name.upper() == "BANK":
            return JsonResponse({"message": "Bank payments not supported yet."}, status=400)

        # Initiate M-Pesa STK Push
        mpesa_response = initiate_stk_push(
            phone_number = phone,
            amount = amount,
            paybill = wallet.paybill,
            account_reference = f"{student.regno} SchoolFee",
            transaction_desc=f"Fee Payment by {student.fname} {student.sname}"
        )

        if "errorCode" in mpesa_response:
            return JsonResponse({
                "success": False,
                "message": mpesa_response.get("errorMessage", "M-Pesa Error"),
                "errorCode": mpesa_response.get("errorCode"),
            }, status=400)

        if mpesa_response.get("ResponseCode") == "0":
            PaymentAttempt.objects.create(
                student = student,
                wallet = wallet,
                amount = amount,
                ref_id = mpesa_response.get("CheckoutRequestID"),
                payer_name = payer_name,
                account_number = phone,
                status = "Pending",
                merchant_request_id=mpesa_response.get("MerchantRequestID"),
                checkout_request_id=mpesa_response.get("CheckoutRequestID"),
                response_payload=json.dumps(mpesa_response)
            )

            return JsonResponse({
                "success": True,
                "message": mpesa_response.get("CustomerMessage"),
                "checkout_id": mpesa_response.get("CheckoutRequestID"),
                "merchant_id": mpesa_response.get("MerchantRequestID")
            })

        # Unexpected fallback
        return JsonResponse({
            "success": False,
            "message": "Unexpected response from M-Pesa",
            "raw": mpesa_response
        }, status=500)

    except ValueError:
        return JsonResponse({"message": "Invalid amount or payload."}, status=400)
    except Exception as e:
        print("Unexpected error:", str(e))
        return JsonResponse({"message": "Something went wrong."}, status=500)

@csrf_exempt
@require_POST
def mpesa_c2b_confirmation(request):
    if request.method != 'POST':
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid request method"})

    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid JSON"})

    try:
        trans_id = data.get('TransID')
        trans_time = data.get('TransTime')
        trans_amount = float(data.get('TransAmount', 0))
        msisdn = data.get('MSISDN')  # Phone number
        account_number = data.get('BillRefNumber')  # Admission number

        # Match student
        student = Student.objects.filter(regno=account_number).first()

        if not student:
            # Optionally: log to UnmatchedPayment
            # UnmatchedPayment.objects.create(...)
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted but unmatched"})

        # Cleanly format name
        first = data.get("FirstName", "")
        middle = data.get("MiddleName", "")
        last = data.get("LastName", "")
        payer_name = " ".join(filter(None, [first, middle, last]))

        wallet = Wallet.objects.filter(name__contains = "MPesa").first()

        if PaymentAttempt.objects.filter(ref_id=trans_id).exists():
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Duplicate transaction"})

        attempt = PaymentAttempt.objects.create(
            wallet = wallet,
            status="Success",
            account_number=msisdn,
            payer_name=payer_name,
            ref_id=trans_id,
            merchant_request_id=trans_id,
            checkout_request_id=trans_id,
            student=student,
            amount=trans_amount,
            response_payload=json.dumps(data)
        )

        rcpt = create_receipt(attempt.id)
        Thread(target=process_fee_allocation, args=(rcpt.id,)).start()

        return JsonResponse({
            "ResultCode": 0,
            "ResultDesc": "Accepted",
            "transaction_id": trans_id,
        })

    except Exception as e:
        # Add logging here for production
        return JsonResponse({"ResultCode": 1, "ResultDesc": f"Error: {str(e)}"})

@csrf_exempt
@require_POST
def check_stk_status(request):
    try:
        body = json.loads(request.body)
        checkout_request_id = body.get("checkout_request_id")

        if not checkout_request_id:
            return JsonResponse({"success": False, "message": "Missing CheckoutRequestID."}, status=400)

        attempt = PaymentAttempt.objects.filter(checkout_request_id=checkout_request_id).first()
        if not attempt:
            return JsonResponse({"success": False, "message": "Transaction not found."}, status=404)

        try:
            response = query_stk_status(checkout_request_id)
        except Exception as err:
            return JsonResponse({"success": False, "message": f"Safaricom query error: {str(err)}"}, status=502)

        result_code = str(response.get("ResultCode", "9999"))
        result_desc = response.get("ResultDesc", "Unknown")

        attempt.response_payload += f"\n\n{result_desc}"

        if result_code == "0":
            attempt.status = "Success"
            attempt.ref_id = response.get("TransID", attempt.ref_id)
            attempt.save()

            rcpt = create_receipt(attempt.id)
            Thread(target=process_fee_allocation, args=(rcpt.id,)).start()

            return JsonResponse({
                "success": True,
                "status": "SUCCESS",
                "transaction_id": attempt.ref_id,
                "payer": attempt.student.get_full_name(),
                "amount": attempt.amount
            })

        elif result_code in ["1", "1032", "1037", "2001"]:
            attempt.status = "Failed"
            attempt.save()

            message_map = {
                "1": "Insufficient funds.",
                "1032": "User cancelled the payment.",
                "1037": "User unreachable.",
                "2001": "Wrong M-Pesa PIN entered."
            }

            return JsonResponse({
                "success": True,
                "status": "FAILED",
                "message": message_map.get(result_code, "Transaction failed.")
            })

        else:
            # Still pending
            attempt.save()
            return JsonResponse({
                "success": True,
                "status": "PENDING",
                "message": result_desc
            })

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

@csrf_exempt
def bank_payment_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            trans_id = data.get('trans_id')
            account_number = data.get('account_number')
            bank_name = data.get('bank_name')
            amount = data.get('amount')
            student_reg = data.get('reference_number')  # Your custom field (e.g., reg number)
            trans_time = parse_datetime(data.get('trans_time')) or timezone.now()

            # Check if student exists
            try:
                student = Student.objects.get(registration_number=student_reg)
            except Student.DoesNotExist:
                student = None

            # Save the transaction
            bank_txn, created = Transaction.objects.get_or_create(
                trans_id=trans_id,
                defaults={
                    'bank_name': bank_name,
                    'account_number': account_number,
                    'amount': amount,
                    'trans_time': trans_time,
                    'reference_number': student_reg,
                    'status': 'CONFIRMED'
                }
            )

            # Optionally auto-create a Receipt
            if student and created:
                payment_method, _ = PaymentMethod.objects.get_or_create(name=bank_name, code=bank_name.upper())
                mode, _ = Wallet.objects.get_or_create(payment_method = payment_method)

                Receipt.objects.create(
                    student=student,
                    term=Term.objects.latest("start_date"),
                    amount_paid=amount,
                    balance=0,
                    pay_mode=mode,
                    cashier="System",
                )

            return JsonResponse({
                'message': 'Transaction processed',
                'transaction_id': bank_txn.id
            }, status=201 if created else 200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'detail': 'Method not allowed'}, status=405)

class AccessTokenViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = AccessToken.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = AccessTokenSerializer

class PaymentMethodViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = PaymentMethod.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = PaymentMethodSerializer

class WalletViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        query_param = request.query_params.get("all")

        if query_param == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure

        elif query_param == 'active':
            queryset = self.filter_queryset(self.get_queryset().filter(blocked=False))
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)

class PriorityLevelViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = PriorityLevel.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = PriorityLevelSerializer

class AccountViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = Account.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = AccountSerializer

class FeeParticularViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = FeeParticular.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = FeeParticularSerializer

class FeeStatusViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = FeeStatus.objects.all().order_by('-id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = FeeStatusSerializer

class ReceiptViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = Receipt.objects.all().order_by('-id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = ReceiptSerializer

class TransactionViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = Transaction.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = TransactionSerializer

class PaymentAttemptViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = PaymentAttempt.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = PaymentAttemptSerializer

class PaymentPlanViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    queryset = PaymentPlan.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
    serializer_class = PaymentPlanSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kpi_dashboard(request):
    # Total collected (all transactions)
    total_collected = Receipt.objects.aggregate(total=models.Sum('amount'))['total'] or Decimal("0.00")

    students = Student.objects.all()
    latest_statuses = []
    for student in students:
        latest_status = FeeStatus.objects.filter(student=student).order_by('-created_at').first()   
        if latest_status:
            latest_statuses.append(latest_status) 

    # Filter and sum arrears for NOT-CLEARED only
    pending_dues = Decimal("0.00")
    for status in latest_statuses:
        if status.status == "Not-Cleared":
            pending_dues += status.arrears

    # Total students
    total_students = Student.objects.count()

    # This term’s transactions (you may want to pass current term via request instead)
    try:
        institution = Institution.objects.first()
        current_term = Term.objects.get(
            name=institution.current_intake,
            year=institution.current_year
        )
        this_term_txns = Receipt.objects.filter(
            term=current_term  # adjust to match your active term logic
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal("0.00")

    except Institution.DoesNotExist:
        print("Institution not configured.")
        return None
    
    return Response({
        "total_collected": total_collected,
        "pending_dues": abs(pending_dues),  # abs in case it's negative
        "total_students": str(total_students),
        "term_txns": this_term_txns,
    })

def create_invoice_for_new_student(mode):
    if mode == "all":
        excluded_states = ["Cleared", "Suspended", "Expelled", "Graduated", "Differ"]
        eligible_students = Student.objects.exclude(state__in=excluded_states)
        for student in eligible_students:
            target_term = Term.objects.get(name=Institution.objects.first().current_intake, year=Institution.objects.first().current_year)
            create_newterm_invoice(student.regno, term_id=target_term.id)

    else:
        # Handle specific mode logic here
        pass
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_statement(request):
    try:
        student_regno = request.query_params.get('student_regno')
        student = Student.objects.get(regno=student_regno) if student_regno else Student.objects.first()

        term_id = request.query_params.get('term_id')
        institution = Institution.objects.first()
        term = (
            Term.objects.get(name=institution.current_intake, year=institution.current_year)
            if not term_id else Term.objects.get(id=term_id)
        )

        # Gather invoices and receipts
        invoices = Invoice.objects.filter(student = student, term = term).order_by('created_at')
        receipts = Receipt.objects.filter(student = student, term = term).order_by('created_at')
        status = FeeStatus.objects.filter(student = student, term = term).order_by('created_at')

        statement = []

        # === Add Invoices ===
        for invoice in invoices:
            statement.append({
                "transaction_id": invoice.inv_no,
                "date": invoice.created_at,  # will be formatted later
                "record": {
                    "detail": "New Term Invoice",
                    "paid_in": f"{invoice.paid_amount} bal b/f",
                    "paid_out": f"{invoice.amount}",
                    "balance": f"{status.filter(purpose = invoice.inv_no).first().arrears}",
                }
            })

        # === Add Receipts with grouped voteheads ===
        for receipt in receipts:
            running_balance = status.filter(purpose = receipt.trans_id).first().arrears  - receipt.amount
            txns = Transaction.objects.filter(receipt=receipt).order_by("-id")
            txn_details = {}
            sorted_txn_details = {}
            if txns:
                pre_running_balance = status.filter(purpose = receipt.trans_id).first().arrears
                if pre_running_balance>0:
                    sorted_txn_details["Overpayment"] = {
                        "paid_out": f"{pre_running_balance}",
                        "balance": f"{pre_running_balance}"
                    }
                for txn in txns:
                    running_balance += txn.amount
                    txn_details[txn.account.account.votehead] = {
                        "paid_out": f"{txn.amount}",
                        "balance": f"{running_balance}",
                    }

                # Sort txn_details in reverse
                key_list = list(txn_details.keys())
                key_list.reverse()
                for keys in key_list:
                    sorted_txn_details[keys] = txn_details[keys]

            else:
                sorted_txn_details["Overpayment"] = {
                    "paid_out": "",
                    "balance": f"{running_balance}"
                }

            # Add paid_in inside the record
            sorted_txn_details["paid_in"] = f"{receipt.amount}"

            statement.append({
                "transaction_id": receipt.trans_id,
                "date": receipt.created_at,  # will be formatted later
                "record": sorted_txn_details
            })

        # === Sort by datetime then format date ===
        sorted_statement = sorted(statement, key=lambda x: x['date'], reverse=True)
        for item in sorted_statement:
            item["date"] = item["date"].strftime("%d/%m/%Y %H:%M")

        return JsonResponse({
            "student": student.get_full_name(),
            "statement": sorted_statement
        }, status=200)

    except Student.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_logs(request):
    try:
        student_regno = request.query_params.get('student_regno')
        student = Student.objects.get(regno=student_regno) if student_regno else Student.objects.first()

        term_id = request.query_params.get('term_id')
        institution = Institution.objects.first()
        term = (
            Term.objects.get(name=institution.current_intake, year=institution.current_year)
            if not term_id else Term.objects.get(id=term_id)
        )

        # Gather attempts
        attempts = PaymentAttempt.objects.filter(student = student).order_by('created_at')

        logs = []

        # === Add Logs ===
        for attempt in attempts:
            logs.append({
                "id": attempt.id,
                "date": attempt.created_at,  # will be formatted later
                "wallet": attempt.wallet.name,
                "ref_id": attempt.ref_id,
                "payer": attempt.payer_name,
                "amount": attempt.amount,
                "account_number": attempt.account_number,
                "status": attempt.status,
            })

        # === Sort by datetime then format date ===
        sorted_logs = sorted(logs, key=lambda x: x['date'], reverse=True)
        for item in sorted_logs:
            item["date"] = item["date"].strftime("%d/%m/%Y %H:%M")

        return JsonResponse({
            "student": student.get_full_name(),
            "logs": sorted_logs
        }, status=200)

    except Student.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_receipts(request):
    try:
        student_regno = request.query_params.get('student_regno')
        student = Student.objects.get(regno=student_regno) if student_regno else Student.objects.first()

        term_id = request.query_params.get('term_id')
        institution = Institution.objects.first()
        term = (
            Term.objects.get(name=institution.current_intake, year=institution.current_year)
            if not term_id else Term.objects.get(id=term_id)
        )

        receipts = Receipt.objects.filter(student=student, term=term).order_by('-created_at')
        data = []

        for receipt in receipts:
            txns = Transaction.objects.filter(receipt=receipt)
            data.append({
                "id": receipt.id,
                "trans_id": receipt.trans_id,
                "created_at": receipt.created_at.strftime("%d/%m/%Y"),
                "amount": f"{receipt.amount:,.0f}",
                "transactions": [
                    {
                        "account": txn.account.account.votehead,
                        "amount": f"{txn.amount}",
                        "running_balance": f"{txn.running_balance:,.0f}"
                    } for txn in txns
                ]
            })

        return JsonResponse({"receipts": data}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fee_structure(request):
    try:
        student_regno = request.query_params.get('student_regno')
        student = Student.objects.get(regno=student_regno) if student_regno else Student.objects.first()

        term_id = request.query_params.get('term_id')
        institution = Institution.objects.first()
        term = (
            Term.objects.get(name=institution.current_intake, year=institution.current_year)
            if not term_id else Term.objects.get(id=term_id)
        )

        invoice = Invoice.objects.filter(student=student, term=term).first()
        structure = []

        if invoice:
            for item in invoice.narration.all():
                structure.append({
                    "account": item.account.votehead,
                    "amount": item.amount
                })

        return JsonResponse({"structure": structure}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reciept_summary(request):
    try:
        # Get student
        student_regno = request.query_params.get('student_regno')
        student = Student.objects.get(regno=student_regno) if student_regno else Student.objects.first()

        # Get term
        institution = Institution.objects.first()
        term_id = request.query_params.get('term_id')
        term = (
            Term.objects.get(id=term_id)
            if term_id else Term.objects.get(name=institution.current_intake, year=institution.current_year)
        )

        # Get receipts
        receipts = Receipt.objects.filter(student=student, term=term).order_by('created_at')
        receipt_dates = [r.id for r in receipts]
        receipt_values = [float(r.amount) for r in receipts]
        total_receipt = sum(r.amount for r in receipts)

        # Get current fee status
        status_obj = FeeStatus.objects.filter(student=student, term=term).last()
        status = {
            "status": status_obj.status if status_obj else "",
            "arrears": float(status_obj.arrears) if status_obj and status_obj.arrears is not None else ""
        }

        # Get total invoice
        invoices = Invoice.objects.filter(student=student, term=term)
        total_invoice = sum(i.amount for i in invoices)

        # Compute progress
        payment_progress = float(total_receipt / total_invoice * 100) if total_invoice > 0 else 0.00

        # Get term-wise summary
        current_year = institution.current_year if not term_id else Term.objects.get(id=term_id).year
        year_terms = Term.objects.filter(year=current_year)

        term_series = []
        for t in year_terms:
            receipt_total = Receipt.objects.filter(student=student, term=t).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            invoice_total = Invoice.objects.filter(student=student, term=t).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            term_series.append({
                "term": t.name.name,
                "invoice": float(invoice_total),
                "reciept": float(receipt_total),
            })

        return JsonResponse({
            "term_series": term_series,
            "paymentProgress": round(payment_progress, 2),
            "status": status,
            "recieptDates": receipt_dates,
            "recieptValues": receipt_values
        }, status=200)

    except Exception as e:
        print("Error in reciept_summary:", e)
        return JsonResponse({"error": str(e)}, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_receipts(request):
    try:
        wallet_id = request.query_params.get('wallet_id')
        if not wallet_id:
            return JsonResponse({"error": "wallet_id is required"}, status=400)

        wallet = Wallet.objects.get(id = wallet_id)
        transactions = Receipt.objects.filter(wallet=wallet).order_by('-created_at')
        serialized = ReceiptSerializer(transactions, many=True)

        print(serialized)

        return JsonResponse(serialized.data, safe=False)

    except Wallet.DoesNotExist:
        return JsonResponse({"error": "Wallet not found or not yours"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def class_fee_report(request):
    try:
        class_id = request.param_query.get("class_id")
        term_id = request.param_query.get("term_id")
        classroom = Allocate_Student.objects.get(Class__id = class_id, term__id = term_id)
        students = classroom.students.all() 

        report = []

        for student in students:
            invoices = Invoice.objects.filter(student=student)

            total_invoiced = sum(inv.total_amount for inv in invoices)
            total_paid = sum(inv.total_paid for inv in invoices)  # or use related payments

            balance = total_invoiced - total_paid
            if balance <= 0:
                status = "Paid"
            elif total_paid == 0:
                status = "Not Paid"
            else:
                status = "Partially Paid"

            report.append({
                "regno": student.regno,
                "name": student.fullname,
                "total_invoiced": total_invoiced,
                "total_paid": total_paid,
                "balance": balance,
                "status": status
            })

        return Response({
            "class": classroom.name,
            "students": report
        })
    except Allocate_Student.DoesNotExist:
        return Response({"error": "Class not found"}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_course_invoices(request):
    course_id = request.query_params.get("course_id")
    term_id = request.query_params.get("term_id")

    try:
        # Fallback to current term
        if term_id:
            term = Term.objects.filter(id=term_id).first()
        else:
            inst = Institution.objects.first()
            term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()

        if not term:
            return Response({"error": "No term found"}, status=status.HTTP_400_BAD_REQUEST)

        # Fallback to first course
        if course_id:
            course = Course.objects.filter(id=course_id).first()
        else:
            course = Course.objects.first()

        if not course:
            return Response({"error": "No course found"}, status=status.HTTP_400_BAD_REQUEST)

        # Group Fee Particulars by Module
        module_fees = {}
        modules = Module.objects.all().order_by("id")

        for module in modules:
            fee_particulars = FeeParticular.objects.filter(course=course, term=term, module=module, target="Course")

            if not fee_particulars.exists():
                continue

            fee_data = []
            total = 0
            for fee in fee_particulars:
                fee_data.append({
                    "votehead": fee.account.votehead,
                    "amount": float(fee.amount)
                })
                total += float(fee.amount)

            module_fees[module.name] = {
                "particulars": fee_data,
                "total": total
            }

        return Response(module_fees, status=status.HTTP_200_OK)

    except Exception as e:
        print("Fee View Error:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def class_income_statement(request):
    course_id = request.query_params.get('course_id')
    term_id = request.query_params.get('term_id')
 
    try:
        # Get term
        if term_id:
            term = Term.objects.filter(id=term_id).first()
        else:
            inst = Institution.objects.first()
            term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()

        if not term:
            return Response({"error": "Term not found"}, status=status.HTTP_400_BAD_REQUEST)

        # Get course
        if course_id:
            course = Course.objects.filter(id=course_id).first()
        else:
            course = Course.objects.first()

        if not course:
            return Response({"error": "Course not found"}, status=status.HTTP_400_BAD_REQUEST)

        # 🔍 Filter classes by course and term + sort by name
        # Adjust this if your Class model uses term-like fields differently
        course_classes = Class.objects.filter(
            course = course,
            intake = term,   # 🔁 Change this line if you use a different term-related field
        ).order_by("branch", "name")

        # Group students by class
        allocations = Allocate_Student.objects.filter(Class__in=course_classes).select_related("studentno", "Class")
        student_map = defaultdict(list)

        for alloc in allocations:
            student_map[str(alloc.Class.id)].append(alloc.studentno)

        response_data = []

        for cls in course_classes:
            class_id = str(cls.id)
            students = student_map.get(class_id, [])

            total_invoiced = Decimal("0.00")
            total_paid = Decimal("0.00")

            for student in students:
                invoices = Invoice.objects.filter(student=student, term=term)
                receipts = Receipt.objects.filter(student=student, term=term)
                
                total_invoiced += sum(inv.amount for inv in invoices)
                total_paid += sum(rcp.amount for rcp in receipts)
                # Add Overpayments to total_paid
                total_paid += sum(inv.paid_amount for inv in invoices if inv.paid_amount is not None)

            balance = total_invoiced - total_paid

            if balance == 0 and total_invoiced == 0:
                status_label = "No Data"
            elif balance == 0:
                status_label = "Cleared"
            elif balance > 0:
                status_label = "Owing"
            else:
                status_label = "Overpaid"

            response_data.append({
                "class_id": class_id,
                "class_name": cls.name,
                "branch": cls.branch.name,
                "total_invoiced": float(total_invoiced),
                "total_paid": float(total_paid),
                "total_balance": float(balance),
                "status": status_label
            })

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        print("Error in income statement view:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def class_student_breakdown(request):
    class_id = request.query_params.get('class_id')
    term_id = request.query_params.get('term_id')

    try:
        # Get class
        classroom = Class.objects.filter(id=class_id).first()
        if not classroom:
            return Response({"error": "Class not found"}, status=status.HTTP_404_NOT_FOUND)

        # Fallback to current term if not provided
        if term_id:
            term = Term.objects.filter(id=term_id).first()
        else:
            inst = Institution.objects.first()
            term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()

        if not term:
            return Response({"error": "Term not found"}, status=status.HTTP_400_BAD_REQUEST)

        # Get students in class
        allocations = Allocate_Student.objects.filter(Class=classroom).select_related("studentno")

        student_data = []

        for alloc in allocations:
            student = alloc.studentno
            invoices = Invoice.objects.filter(student=student, term=term)
            receipts = Receipt.objects.filter(student=student, term=term)

            invoice_total = sum(inv.amount for inv in invoices)
            paid_total = sum(rc.amount for rc in receipts)
            # Add Overpayments to paid_total
            paid_total += sum(inv.paid_amount for inv in invoices if inv.paid_amount is not None)
            balance = invoice_total - paid_total

            if balance == 0:
                status_label = "Cleared"
            elif balance > 0:
                status_label = "Owing"
            else:
                status_label = "Overpaid"

            student_data.append({
                "profile_picture": student.passport.url if student.passport else None,
                "student_name": student.get_full_name(),
                "regno": student.regno,
                "invoice_amount": float(invoice_total),
                "amount_paid": float(paid_total),
                "balance": float(balance),
                "status": status_label
            })

        return Response(student_data, status=status.HTTP_200_OK)

    except Exception as e:
        print("Error in class_student_breakdown view:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_fee_summary(request):
    try:
        student_regno = request.query_params.get("student_regno")
        student = Student.objects.get(regno = student_regno)

        inst = Institution.objects.first()
        current_term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()

        # Try to get previous term by ordering
        previous_terms = Term.objects.exclude(id=current_term.id).order_by('-year', '-id')

        if not current_term:
            return Response({"error": "Current term not found"}, status=400)

        # Current term data
        invoices = Invoice.objects.filter(student = student)
        receipts = Receipt.objects.filter(student = student)

        total_invoiced = invoices.aggregate(total=Coalesce(Sum('amount'), V(0), output_field=DecimalField()))['total']
        total_paid = receipts.aggregate(total=Coalesce(Sum('amount'), V(0), output_field=DecimalField()))['total']
        total_balance = total_invoiced - total_paid

        # Previous term comparison data
        prev_invoiced, prev_paid, prev_balance = 0, 0, 0
        if previous_terms:
            prev_invoiced = Invoice.objects.filter(student = student, term__in=previous_terms).aggregate(
                total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
            )['total']
            prev_paid = Receipt.objects.filter(student = student, term__in=previous_terms).aggregate(
                total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
            )['total']
            prev_balance = prev_invoiced - prev_paid

        return Response({
            "summary": {
                "totalInvoiced": float(total_invoiced),
                "totalPaid": float(total_paid),
                "totalBalance": float(total_balance),
                "prevInvoiced": float(prev_invoiced),
                "prevPaid": float(prev_paid),
                "prevBalance": float(prev_balance)
            }
        })

    except Exception as e:
        print("Error in institution fee summary:", e)
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def institution_fee_summary(request):
    try:
        inst = Institution.objects.first()
        current_term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()

        # Try to get previous term by ordering
        previous_term = Term.objects.exclude(id=current_term.id).order_by('-year', '-id').first() if current_term else None

        if not current_term:
            return Response({"error": "Current term not found"}, status=400)

        # Current term data
        invoices = Invoice.objects.filter(term=current_term)
        receipts = Receipt.objects.filter(term=current_term)

        total_invoiced = invoices.aggregate(total=Coalesce(Sum('amount'), V(0), output_field=DecimalField()))['total']
        total_paid = receipts.aggregate(total=Coalesce(Sum('amount'), V(0), output_field=DecimalField()))['total']
        total_balance = total_invoiced - total_paid

        # Previous term comparison data
        prev_invoiced, prev_paid, prev_balance = 0, 0, 0
        if previous_term:
            prev_invoiced = Invoice.objects.filter(term=previous_term).aggregate(
                total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
            )['total']
            prev_paid = Receipt.objects.filter(term=previous_term).aggregate(
                total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
            )['total']
            prev_balance = prev_invoiced - prev_paid

        cleared, owing, overpaid = 0, 0, 0
        student_balances = defaultdict(Decimal)

        for student in Student.objects.all():
            stu_invoiced = invoices.filter(student=student).aggregate(
                total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
            )['total']
            stu_paid = receipts.filter(student=student).aggregate(
                total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
            )['total']
            balance = stu_invoiced - stu_paid

            if balance == 0:
                cleared += 1
            elif balance > 0:
                owing += 1
            else:
                overpaid += 1

        # Top classes
        class_balances = []
        for cls in Class.objects.all():
            student_ids = Allocate_Student.objects.filter(Class=cls).values_list("studentno", flat=True)
            cls_invoiced = invoices.filter(student_id__in=student_ids).aggregate(
                total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
            )['total']
            cls_paid = receipts.filter(student_id__in=student_ids).aggregate(
                total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
            )['total']
            balance = cls_invoiced - cls_paid

            class_balances.append({
                "name": cls.name,
                "balance": float(balance)
            })

        top_classes = sorted([c for c in class_balances if c["balance"] > 0], key=lambda x: -x["balance"])[:5]
        cleared_classes = [c for c in class_balances if c["balance"] == 0][:5]
        overpaid_classes = sorted([c for c in class_balances if c["balance"] < 0], key=lambda x: x["balance"])[:5]

        # By department
        dept_data = []
        for dept in Department.objects.all():
            dept_courses = Course.objects.filter(department=dept)
            dept_invoiced, dept_paid = 0, 0
            course_list = []

            for course in dept_courses:
                class_ids = Class.objects.filter(course=course).values_list("id", flat=True)
                student_ids = Allocate_Student.objects.filter(Class_id__in=class_ids).values_list("studentno", flat=True)

                course_invoiced = invoices.filter(student_id__in=student_ids).aggregate(
                    total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
                )['total']
                course_paid = receipts.filter(student_id__in=student_ids).aggregate(
                    total=Coalesce(Sum('amount'), V(0), output_field=DecimalField())
                )['total']
                balance = course_invoiced - course_paid

                if balance == 0:
                    status = "Cleared"
                elif balance > 0:
                    status = "Not Cleared"
                else:
                    status = "Overpaid"

                course_list.append({
                    "name": course.name,
                    "abbr": course.abbr if hasattr(course, 'abbr') else course.name,
                    "invoiced": float(course_invoiced),
                    "paid": float(course_paid),
                    "balance": float(balance),
                    "status": status
                })

                dept_invoiced += course_invoiced
                dept_paid += course_paid

            dept_balance = dept_invoiced - dept_paid
            if dept_balance == 0:
                dept_status = "Cleared"
            elif dept_balance > 0:
                dept_status = "Not Cleared"
            else:
                dept_status = "Overpaid"

            dept_data.append({
                "name": dept.name,
                "abbr": dept.abbr,
                "invoiced": float(dept_invoiced),
                "paid": float(dept_paid),
                "balance": float(dept_balance),
                "status": dept_status,
                "courses": course_list
            })

        return Response({
            "summary": {
                "totalInvoiced": float(total_invoiced),
                "totalPaid": float(total_paid),
                "totalBalance": float(total_balance),
                "prevInvoiced": float(prev_invoiced),
                "prevPaid": float(prev_paid),
                "prevBalance": float(prev_balance),
                "cleared": cleared,
                "owing": owing,
                "overpaid": overpaid,
            },
            "topClasses": top_classes,
            "clearedClasses": cleared_classes,
            "overpaidClasses": overpaid_classes,
            "byDepartment": dept_data
        })

    except Exception as e:
        print("Error in institution_fee_summary:", e)
        return Response({"error": str(e)}, status=500)

class InstitutionFeeTrendAPIView(APIView):
    def get(self, request):
        current_year = date.today().year
        start_year = current_year - 4  # Past 5 years

        # Annotate and aggregate invoice totals by year
        invoice_data = (
            Invoice.objects.filter(created_at__year__gte=start_year)
            .annotate(year=ExtractYear("created_at"))
            .values("year")
            .annotate(total=Sum("amount"))
            .order_by("year")
        )

        # Annotate and aggregate receipt totals by year
        receipt_data = (
            Receipt.objects.filter(dop__year__gte = start_year)
            .annotate(year=ExtractYear("dop"))
            .values("year")
            .annotate(total=Sum("amount"))
            .order_by("year")
        )

        # Convert to dict: {year: amount}
        invoice_map = {str(i["year"]): float(i["total"]) for i in invoice_data}
        receipt_map = {str(r["year"]): float(r["total"]) for r in receipt_data}

        # Combine into trend list
        trend = []
        for year in range(start_year, current_year + 1):
            y = str(year)
            trend.append({
                "year": y,
                "invoiced": round(invoice_map.get(y, 0)),
                "received": round(receipt_map.get(y, 0)),
            })

        return Response(trend)

class InstitutionMonthlyFeeSummary(APIView):
    def get(self, request):
        current_year = date.today().year

        # Get invoiced per month
        invoices = (
            Invoice.objects.filter(created_at__year = current_year)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total_invoiced=Sum("amount"))
            .order_by("month")
        )

        # Get paid per month
        payments = (
            Receipt.objects.filter(created_at__year = current_year)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total_paid=Sum("amount"))
            .order_by("month")
        )

        # Build month map
        month_map = OrderedDict()
        for i in range(1, 13):
            month_name = calendar.month_abbr[i]
            month_map[month_name] = {"invoiced": 0, "paid": 0}

        for inv in invoices:
            month = calendar.month_abbr[inv["month"].month]
            month_map[month]["invoiced"] = inv["total_invoiced"]

        for pay in payments:
            month = calendar.month_abbr[pay["month"].month]
            month_map[month]["paid"] = pay["total_paid"]

        # Prepare response
        data = [
            {
                "month": month,
                "invoiced": float(values["invoiced"]),
                "paid": float(values["paid"]),
            }
            for month, values in month_map.items()
        ]

        return Response(data)

@api_view(['POST'])
@permission_classes([AllowAny])
def equity_payment_callback(request):
    """
    This receives payment notifications from Equity Bank
    """
    data = request.data
    try:
        amount = float(data.get("amount"))
        reference = data.get("reference")  # e.g., ADM00123
        sender = data.get("sender_name")
        transaction_id = data.get("transaction_id")
        msisdn = data.get("sender_account")

        student = Student.objects.filter(regno=reference).first()
        if not student:
            return Response({"error": "Student not found"}, status=400)

        wallet = Wallet.objects.filter(name__contains = "Equity").first()

        if PaymentAttempt.objects.filter(ref_id=transaction_id).exists():
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Duplicate transaction"})

        attempt = PaymentAttempt.objects.create(
            wallet = wallet,
            status="Success",
            account_number=msisdn,
            payer_name=sender,
            ref_id=transaction_id,
            merchant_request_id=transaction_id,
            checkout_request_id=transaction_id,
            student=student,
            amount=amount,
            response_payload=json.dumps(data)
        )

        rcpt = create_receipt(attempt.id)
        Thread(target=process_fee_allocation, args=(rcpt.id,)).start()

        return Response({"status": "success"}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predict_fee_payments(request):
    current_year = datetime.now().year
    next_year = current_year + 1

    # Retrive Enrollment Prediction
    app_request = request._request  # low-level Django request
    app_prediction_response = predict_applications(app_request)  # Call existing function
    app_data = json.loads(app_prediction_response.content)  # Get JSON response

    course_dict = app_data.get("by_course", {})

    # Extract predicted students per course
    predicted_enrollment = {}
    for course_id in course_dict:
        predicted_enrollment[course_id] = course_dict[course_id]
    
    total_students = 0
    total_invoice = 0
    total_receipt = 0
    department_data = {}

    # Get historical average payment rate per course
    course_payment_rates = get_historical_payment_rates()
    
    for course_id, student_count in predicted_enrollment.items():
        try:
            course = Course.objects.get(id = course_id)
            department = course.department
        except Course.DoesNotExist:
            continue

        fee_per_student = get_course_fee(course)
        invoice_total = fee_per_student * student_count
        payment_rate = course_payment_rates.get(course_id, 0.9)  # Fallback: 90%
        receipt_total = invoice_total * Decimal(str(payment_rate))
        balance = invoice_total - receipt_total

        total_students += student_count
        total_invoice += invoice_total
        total_receipt += receipt_total

        dept_id = department.id
        if dept_id not in department_data:
            department_data[dept_id] = {
                "id": dept_id,
                "name": department.name,
                "abbr": department.abbr,
                "students": 0,
                "invoice": 0,
                "receipt": 0,
                "balance": 0,
                "courses": []
            }

        department_data[dept_id]["students"] += student_count
        department_data[dept_id]["invoice"] += invoice_total
        department_data[dept_id]["receipt"] += receipt_total
        department_data[dept_id]["balance"] += balance

        department_data[dept_id]["courses"].append({
            "id": course.id,
            "abbr": course.abbr,
            "name": course.name,
            "students": student_count,
            "invoice": invoice_total,
            "receipt": receipt_total,
            "balance": balance
        })

    # Final response
    response = {
        "total_students": total_students,
        "total_invoice": int(total_invoice),
        "total_receipt": int(total_receipt),
        "total_balance": int(total_invoice - total_receipt),
        "departments": list(department_data.values())
    }

    return Response(response)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def check_fee_structure(request):
    course_id = request.query_params.get('course_id')

    try:
        # Fallback to current term
        inst = Institution.objects.first()
        term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()

        if not term:
            return Response({"error": True,
                             "errMessage": "No term found"
                        }, status=status.HTTP_400_BAD_REQUEST)

        if course_id:
            course = CourseDuration.objects.filter(id=course_id).first()
        else:
            return Response({"error": "No course found"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get Fee Particulars by Module
        fee_particulars = FeeParticular.objects.filter(course=course.course, term=term, module=course.module, target="Course")
        
        if not fee_particulars.exists():
            return Response({"feeCheckError": True}, status=status.HTTP_200_OK)

        return Response({"feeCheckSuccess":True}, status=status.HTTP_200_OK)

    except Exception as e:
        print("Fee Structure Error:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def check_invoice_match_feestructure(request):
    student_ids = request.data.get("student_ids", [])
    voteheads = request.data.get("voteheads", {})

    try:
        if not student_ids:
            return Response({"error": "No students provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        inst = Institution.objects.first()
        term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()

        if not term:
            return Response({"error": "No term found"}, status=status.HTTP_400_BAD_REQUEST)
        
        results = []

        for student_id in student_ids:
            try:
                student_alloc = Allocate_Student.objects.get(id=student_id)

                course_id = getattr(getattr(student_alloc.studentno, "course", None), "id", None)
                module_id = getattr(getattr(student_alloc, "module", None), "id", None)

                if not course_id or not module_id:
                    results.append({
                        "student_id": student_id,
                        "student_name": str(student_alloc),
                        "match": False,
                        "reason": "Missing course/module"
                    })
                    continue

                # ✅ Check fee structure
                fee_structure_qs = FeeParticular.objects.filter(
                    course_id=course_id,
                    module_id=module_id,
                    term=term
                )
                print(f"[STUDENT]: ", student_alloc.studentno.get_full_name())
                print(f"[FEE STRUCTURE]: ", fee_structure_qs)

                if not fee_structure_qs.exists():
                    results.append({
                        "student_id": student_id,
                        "student_name": str(student_alloc),
                        "match": False,
                        "reason": "No matching fee structure"
                    })
                    continue

                # ✅ Check if voteheads are in fee structure
                fee_structure_ids = set(fee_structure_qs.values_list('id', flat=True))
                invoice_qs = Invoice.objects.filter(
                    student=student_alloc.studentno,
                    term=term
                ).distinct()
                print(f"[INVOICES]: ", invoice_qs)

                invoice_match = False
                for invoice in invoice_qs:
                    invoice_fee_ids = set(invoice.narration.values_list('id', flat=True))
                    if invoice_fee_ids == fee_structure_ids:
                        invoice_match = True
                        break
                print(f"[INVOICE MATCH]: ", invoice_match)

                results.append({
                    "student_id": student_id,
                    "student_name": str(student_alloc.studentno.get_full_name()),
                    "match": invoice_match,
                    "reason": "Match found" if invoice_match else "No matching invoice"
                })
                print("\n")
 
            except Allocate_Student.DoesNotExist:
                results.append({
                    "student_id": student_id,
                    "match": False,
                    "reason": "Student not found"
                })

        print(results)
        return Response({"results": results}, status=status.HTTP_200_OK)

    except Exception as e:
        print("Fee Structure Error:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_invoice_student(request):
    student_ids = request.data.get("student_ids", [])
    voteheads = request.data.get("voteheads", {})

    try:
        response = create_invoice(student_ids, voteheads, "Student")

        return Response({
            "success": True,
            "message": f"Invoices created for {len(student_ids)} student(s).",
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            "error": False,
            "message": f"{e}"
        })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_invoice_class(request):
    class_ids = request.data.get("class_ids", [])
    voteheads = request.data.get("voteheads", {})
    try:
        error = False
        success = True
        errMessage = []
        successMessage = []

        inst = Institution.objects.first()
        term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()
        classes = Class.objects.filter(id__in=class_ids)
        if not classes.exists():
            success = False
            return Response({"error": True,
                             "errMessage": ["No valid classes found."]}, status=status.HTTP_404_NOT_FOUND)

        for klass in classes:
            students = (
                Allocate_Student.objects
                .filter(Class = klass, term = term)
                .values("id")
            )
            if students:
                response = create_invoice(students, voteheads, "Class")
                successMessage.append(f"{students.count()} invoice(s) have been created for {klass.name}")
            else:
                error = True
                errMessage.append(f"{klass.name} doesn't have students")
        
        return Response({
            "success": success,
            "error": error,
            "errMessage": errMessage,
            "successMessage": successMessage,
            "message": f"Invoices created for {classes.count()} class(es).",
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "error": True,
            "errMessage": f"{e}"
        })
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_invoice_course_overide(request):
    try:
        course_id = request.data.get("course_id", None)
        voteheads = request.data.get("voteheads", {})

        error = False
        success = True
        errMessage = []
        successMessage = []

        inst = Institution.objects.first()
        term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()
        course_duration = CourseDuration.objects.filter(id=course_id).first()

        passed_registry = list()
        non_record = False
        for registry in voteheads:
            votehead = Account.objects.filter(id = registry["votehead"]).first()
            if not votehead:
                errMessage.append(f"Votehead of ID {votehead} is not found!")
            feenaration = FeeParticular.objects.filter(course = course_duration.course, module = course_duration.module, term = term, account = votehead ).first()
            if feenaration:
                # Overide
                feenaration.amount = Decimal(registry["amount"])
                feenaration.save()
            else:
                non_record = True
                passed_registry.append(registry)

        if non_record:
            # Create New One
            response = create_feestructure(course_duration.course.id, passed_registry)
            # Apply to all students
            students = Allocate_Student.objects.filter(term = term, module = course_duration.module, Class__course = course_duration.course)
            print(f"[STUDENTS]: {students}")
            for student in students:
                print(f"Student: {student}")
                print(f"Fee Narration: {response['feenarration']}")
                inv_response = create_new_invoice(student.studentno.regno, term.id, response["feenarration"])
                print(f"Invoice: {inv_response}")

        # Counter check whether all the students have fee structure
        students_in_course = Allocate_Student.objects.filter(
            term=term,
            module=course_duration.module,
            Class__course=course_duration.course
        )

        for student in students_in_course:
            has_invoice = Invoice.objects.filter(
                student=student.studentno,  # assuming studentno FK to Student model
                term=term
            ).exists()

            if not has_invoice:
                # Create an invoice with the fee structure
                invoice = create_newterm_invoice(student.studentno.regno, term.id)
    
        return Response({
            "success": success,
            "error": error,
            "errMessage": errMessage,
            "successMessage": successMessage,
            "message": f"{course_duration.course.abbr} Module {course_duration.module.name} Fee Structure overiden successfully!",
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "error": True,
            "errMessage": f"{e}"
        })
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_invoice_course_append(request):
    try:
        course_id = request.data.get("course_id", None)
        voteheads = request.data.get("voteheads", {})
        
        error = False
        success = True
        errMessage = []
        successMessage = []

        inst = Institution.objects.first()
        term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()
        course_duration = CourseDuration.objects.filter(id=course_id).first()
        if not course_duration:
            return Response({
                "error": True,
                "errMessage": f"Course Duration with id {course_id} not found"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        passed_registry = list()
        non_record = False
        for registry in voteheads:
            votehead = Account.objects.filter(id = registry["votehead"]).first()
            if not votehead:
                errMessage.append(f"Votehead of ID {votehead} is not found!")
                continue
            feenaration = FeeParticular.objects.filter(course = course_duration.course, module = course_duration.module, term = term, account = votehead ).first()
            if feenaration:
                # Append
                feenaration.amount += Decimal(str(registry["amount"]))
                feenaration.save()
            else:
                non_record = True
                passed_registry.append(registry)

        if non_record:
            # Create New One
            response = create_feestructure(course_duration.course.id, passed_registry)
            # Apply to all students
            students = Allocate_Student.objects.filter(term = term, module = course_duration.module, Class__course = course_duration.course)
            for student in students:
                inv_response = create_new_invoice(student.studentno.regno, term.id, response["feenarration"])

        
        # Counter check whether all the students have fee structure
        students_in_course = Allocate_Student.objects.filter(
            term=term,
            module=course_duration.module,
            Class__course=course_duration.course
        )

        for student in students_in_course:
            has_invoice = Invoice.objects.filter(
                student=student.studentno,  # assuming studentno FK to Student model
                term=term
            ).exists()

            if not has_invoice:
                # Create an invoice with the fee structure
                invoice = create_newterm_invoice(student.studentno.regno, term.id)

            # Create a New Invoice with the new addition
            result = create_invoice(student.id, voteheads, "Course")

        return Response({
            "success": success,
            "error": error,
            "errMessage": errMessage,
            "successMessage": successMessage,
            "message": f"{course_duration.course.abbr} Module {course_duration.module.name} Fee Structure appended successfully!",
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "error": True,
            "errMessage": f"{e}"
        })
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_invoice_course_new(request):
    try:
        course_id = request.data.get("course_id", None)
        voteheads = request.data.get("voteheads", {})

        error = False
        success = True
        errMessage = []
        successMessage = []

        inst = Institution.objects.first()
        term = Term.objects.filter(name=inst.current_intake, year=inst.current_year).first()
        course_duration = CourseDuration.objects.filter(id=course_id).first()

        # Apply Particular to Student New Invoice
        students = (
            Allocate_Student.objects
            .filter(Class__course = course_duration.course, term = term)
            .values("id")
        )
        if students:
            response = create_invoice(students, voteheads, "Course")
            successMessage.append(f"{students.count()} invoice(s) have been created for {course_duration.course} Module {course_duration.module.name}")
        else:
            response = create_feestructure(course_id, voteheads)
            success = response["success"]
            successMessage = response["successMessage"]
            error = True
            errMessage.append(f"{course_duration.course.abbr} doesn't have students")
        
        return Response({
            "success": success,
            "error": error,
            "errMessage": errMessage,
            "successMessage": successMessage,
            "message": f"{course_duration.course.abbr} Module {course_duration.module.name} Fee Structure created successfully!",
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "error": True,
            "errMessage": f"{e}"
        })
    