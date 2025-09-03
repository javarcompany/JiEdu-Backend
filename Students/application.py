from django.utils import timezone #type: ignore
from django.contrib.auth.models import Group #type: ignore

from django.core.mail import send_mail  #type: ignore
from uuid import uuid4
from django.conf import settings #type: ignore
from datetime import timedelta, date
import string
import random

from Core.application import generate_password, generate_username
from Core.models import UserProfile, User, CourseDuration, Institution, Term

from Finance.application import create_newterm_invoice

from .models import *

def calculate_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def generate_temp_regno():
    used = True
    while used:
        new_regno = "TEMP/JIEDU/" + ''.join(random.choices(string.digits, k=6))
        if not RegistrationNumber.objects.filter(regno = new_regno):
            used = False
    return new_regno

def generate_perm_reg():    
    year = timezone.now().year
    prefix = f"JI{year}"

    # Count students registered this year
    count = Student.objects.filter(regno__startswith=prefix).count() + 1
    reg_number = f"{prefix}-{str(count).zfill(4)}"
    # return f"STU-{uuid4().hex[:8].upper()}"
    return reg_number

# Approve Applications
def approve_application(application_id):
    try:
        temp_regno = generate_temp_regno()

        application = Application.objects.get(id=application_id)
        print(f"[APPLICATION]: {temp_regno}")

        if application.state != 'Pending':
            return {'error': 'Already processed!'}

        application.regno = temp_regno
        application.state = 'Approved'
        application.save()

        # Store the temporary Reg no.
        expiry_date = utils.timezone.now()  + timedelta(days=60)
        newCode = RegistrationNumber(regno = temp_regno, 
                                     intake = application.intake, 
                                     year = application.year,
                                     valid_date = expiry_date
                        )
        newCode.save()

        # Send Email/ SMS Logic
        try:
            message = f"{application.fname} {application.mname}'s application have been approved. The student has been assigned temporary number: {temp_regno}"
            send_mail("COURSE APPLICATION", message, None, [settings.ADMIN_EMAIL,])
            message = f"Dear {application.fname} {application.mname}, \nYour application have been approved. \nKindly click on the link below to enroll for your course.\n {settings.DOMAIN_NAME}/application/enroll/{temp_regno[11:]}"
            send_mail("COURSE APPLICATION", message, None, [application.email, ])
        except Exception as e:
            print(f"[ERROR]: {e}")

        return {'message': f"Application Approved, Temporary Reg No.: {temp_regno}"}

    except Application.DoesNotExist:
        return {'error': 'Application NOT found!'}

def enroll_student(reg_no):
    try:
        if len(str(reg_no)) < 6:
            reg_no = str(reg_no).zfill(6)

        regno = "TEMP/JIEDU/" + str(reg_no)
        print(regno)

        # 1. Check if temp_regno exists and is still valid
        reg_entry = RegistrationNumber.objects.get(regno=regno)

        # Optional: check expiry logic (if you want a validity duration)
        if reg_entry.valid_date and reg_entry.valid_date < timezone.now():
            return {'error': 'Temporary registration expired!'}

        applicant = Application.objects.get(regno=regno)
        if applicant.state == 'Joined':
            return {'error': 'Already registered'}

        if applicant.state == 'Pending':
            return {'error': 'Application needs to approved first!'}

        # Create a permanent Reg No.
        new_perm_regno = generate_perm_reg()

        # Generate username and password
        username = generate_username(applicant.fname, applicant.mname, applicant.sname)
        password = generate_password()

        # Create user
        user = User.objects.create_user(
            username=username, password=password,
            first_name=applicant.fname, last_name=applicant.sname,
            email=applicant.email, is_active=True
        )
        # Create UserProfile if applicable
        user_profile = UserProfile.objects.create(user=user, branch=applicant.branch, phone=applicant.phone, picture=applicant.passport)
        # Assign to Students group
        students_group = Group.objects.get(name="Students")
        user.groups.add(students_group)

        # Create a new Student
        new_student = Student.objects.update_or_create(
            user = user_profile,
            regno = new_perm_regno, fname = applicant.fname, mname = applicant.mname,
            sname = applicant.sname, gender = applicant.gender, dob = applicant.dob,
            nat_id = applicant.nat_id, phone = applicant.phone, email = applicant.email,
            course = applicant.course, branch = applicant.branch, year = applicant.year,
            intake = applicant.intake, sponsor = applicant.sponsor, passport = applicant.passport
        )

        # Allocate Student to a NULL class
        #  Get the appropriate Term (year + intake)
        app_term = Term.objects.get(year = applicant.year, name = applicant.intake)
        currentstudent = Student.objects.get(regno = new_perm_regno)
        student_class = Allocate_Student.objects.update_or_create(
            studentno = currentstudent, module = Module.objects.order_by('id').first(),
            term = app_term, level = 1
        )

        # Update Application
        applicant.regno = new_perm_regno
        applicant.state = "Joined"
        applicant.save()

        # Create Fee Structure
        invoice = create_newterm_invoice(new_perm_regno, Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).id)

        try:
            # Send Email/ SMS
            message = f"{applicant.fname} {applicant.sname} have joined the school. The student has been assigned a permanent registration number: {new_perm_regno}"
            send_mail("COURSE APPLICATION", message, None, [settings.ADMIN_EMAIL,])
            message = f"Dear {applicant.fname} {applicant.mname}, \nYour have successfuly joined our school. \n\nYour Login Credential: \nUsername: {username}\nPassword: {password}"
            send_mail("COURSE APPLICATION", message, None, [applicant.email, ])
        except Exception as e:
            print(f"[ERROR]: {e}")
        return {'message': f"Student fully registered Username: {username} Password: {password}"}

    except Application.DoesNotExist:
        return {'error': 'Application not found!'}

def decline_application(application_id):
    try:
        application = Application.objects.get(id=application_id)

        if application.state != 'Pending':
            return {'error': 'Already processed!'}

        application.regno = ""
        application.state = 'Declined'
        application.save()
         
        # Send Email/ SMS Logic
        try:
            message = f"{application.fname} {application.mname}'s application have been declined."
            send_mail("COURSE APPLICATION", message, None, [settings.ADMIN_EMAIL,])
            message = f"Dear {application.fname} {application.mname}, \nWe regret to inform you that your application have been declined."
            send_mail("COURSE APPLICATION", message, None, [application.email, ])
        except Exception as e:
            print(f"[ERROR]: {e}")

        return {'message': f"Application Declined!"}

    except Application.DoesNotExist:
        return {'error': 'Application NOT found!'}
 
# Allocate Student
def allocate_student(stud_id, class_id):
    try:
        student = Student.objects.get(id=stud_id)
        print("Student: ", student)

        allocation_student = Allocate_Student.objects.get(studentno = student)
        print("Allocation Student: ", allocation_student)

        if allocation_student.state != 'Pending':
            return {'error': 'Already processed!'}

        # Get Class object
        class_object = Class.objects.get(id = class_id)
        print("Class Object: ", class_object)

        if student.year != class_object.intake.year:
            return {"error": f"{student.regno}'s intake does not match {class_object.name} intake"}
        
        if student.intake != class_object.intake.name:
            return {"error": f"{student.regno}'s intake does not match {class_object.name} intake"}

        allocation_student.Class = class_object
        allocation_student.state = "Allocated"
        allocation_student.save()

        return {'message': f"{student.regno} has been allocated successfully!"}

    except Student.DoesNotExist:
        return {'error': 'Student NOT found!'}
    
    except Allocate_Student.DoesNotExist:
        return {'error': 'Allocation NOT found!'}
    
    except Class.DoesNotExist:
        return {'error': 'Class NOT found!'}

# Promote student to next intake
def promote_student(request_user, stud_id):
    try:
        current_student = Student.objects.get(id = stud_id)
        current_student_allocation = Allocate_Student.objects.get(studentno = current_student)
        current_term = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)
        course_duration = CourseDuration.objects.filter(course = current_student.course, module = current_student_allocation.module).first()
        
        if current_student.state != "Active":
            if current_student.state == "Inactive":
                if current_student_allocation.level < course_duration.duration:
                    if current_student_allocation.term.id > current_term.id:
                        return {"message": f"{current_student.get_full_name()} intake is not yet there"}
                    elif current_student_allocation.term.id == current_term.id:
                        current_student_allocation += 0
                    else:
                        current_student_allocation.level += 1
                    current_student_allocation.term = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)
                    current_student.state = "Active"
                    
            elif current_student.state == "Cleared":
                student_course_level = int(current_student.course.module_duration)
                current_student_module = int(str(current_student_allocation.module.abbr)[1])
                
                if current_student_module < student_course_level:
                    current_student_module += 1
                    current_student_module = f"M{current_student_module}"
                    current_student_module = Module.objects.filter(abbr = current_student_module).first()
                    if current_student_module:
                        course_duration = CourseDuration.objects.filter(course = current_student.course, module = current_student_module).first()
                        if course_duration:
                            current_student_allocation.module = course_duration.module
                            current_student_allocation.level = 1
                            current_student_allocation.term = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)
                            current_student_allocation.Class = None
                            current_student_allocation.state = "Pending"
                            current_student.state = "Active"

            current_student.save()
            current_student_allocation.save()

            # Create Fee Invoice for the new term
            create_newterm_invoice(current_student.regno, term_id=Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).id)

            if request_user == "student":
                return {
                    "message": f"{current_student.fname}, you have been promoted successfully!",
                    "state": True,
                    "kind": "success"
                }
            else:
                return {
                    "message": f"{current_student.get_full_name()} Promoted Successfully!",
                    "state": True,
                    "kind": "success"
                }
        else:
            if request_user == "student":
                return {
                    "message": f"{current_student.fname}, you are already promoted",
                    "state": False,
                    "kind": "info"
                }
            else:
                return {
                    "message": f"{current_student.get_full_name()} is already promoted",
                    "state": False,
                    "kind": "info"
                }
        
    except Exception as e:
        print(f"[ERROR]: {e}")
        return {"error": str(e)}

# Deactivate student
def deactivate_student(mode):
    try:
        current_term = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)
        
        if mode == "all":
            for student in Student.objects.all():
                if student.state == "Active":
                    current_student_allocation = Allocate_Student.objects.get(studentno = student)

                    course_duration = CourseDuration.objects.filter(course = student.course, module = current_student_allocation.module).first()
                    if current_student_allocation.level == course_duration.duration:
                        # Check if student has cleared all modules
                        if current_student_allocation.module.abbr[1:] == student.course.module_duration:
                            student.state = "Graduated"
                        else:
                            student.state = "Cleared"
                    else:
                        student.state = "Inactive"
                    student.save()
            return "All students have been deactivated"
        else:
            student = Student.objects.filter(regno = mode).first()
            if student.state == "Active":
                current_student_allocation = Allocate_Student.objects.get(studentno = student)
                if current_student_allocation.term == current_term:
                    return f"{student.get_full_name()} is already active in the current term"
                else:
                    course_duration = CourseDuration.objects.filter(course = student.course, module = current_student_allocation.module).first()
                    if current_student_allocation.level == course_duration.duration:
                        # Check if student has cleared all modules
                        if current_student_allocation.module.abbr[1:] == student.course.module_duration:
                            student.state = "Graduated"
                        else:
                            student.state = "Cleared"
                    else:
                        student.state = "Inactive"
            student.save()
            return f"{student.get_full_name()} has been deactivated"
    except Exception as e:
        print(f"[ERROR]: {e}")
        return e
    