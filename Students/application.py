from .models import *
from django.utils import timezone #type: ignore
from django.contrib.auth.models import Group #type: ignore
from .models import Application, RegistrationNumber
from django.core.mail import send_mail  #type: ignore
from uuid import uuid4
from django.conf import settings #type: ignore
from datetime import timedelta, date
import string
import random

from Core.application import generate_password
from Core.models import UserProfile, User

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
        message = f"{application.fname} {application.mname}'s application have been approved. The student has been assigned temporary number: {temp_regno}"
        send_mail("COURSE APPLICATION", message, None, [settings.ADMIN_EMAIL,])
        message = f"Dear {application.fname} {application.mname}, \nYour application have been approved. \nKindly click on the link below to enroll for your course.\n {settings.DOMAIN_NAME}/application/enroll/{temp_regno[11:]}"
        send_mail("COURSE APPLICATION", message, None, [application.email, ])

        return {'message': f"Application Approved, Temporary Reg No.: {temp_regno}"}

    except Application.DoesNotExist:
        return {'error': 'Application NOT found!'}

def enroll_student(reg_no):
    try:
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

        # Create a new Student
        new_student = Student.objects.update_or_create(
            regno = new_perm_regno, fname = applicant.fname, mname = applicant.mname,
            sname = applicant.sname, gender = applicant.gender, dob = applicant.dob,
            nat_id = applicant.nat_id, phone = applicant.phone, email = applicant.email,
            course = applicant.course, branch = applicant.branch, year = applicant.year,
            intake = applicant.intake, sponsor = applicant.sponsor, passport = applicant.passport
        )

        # Allocate Student to a NULL student
        #  Get the appropriate Term (year + intake)
        app_term = Term.objects.get(year = applicant.year, name = applicant.intake)
        currentstudent = Student.objects.get(regno = new_perm_regno)
        student_class = Allocate_Student.objects.update_or_create(
            studentno = currentstudent, module = Module.objects.order_by('id').first(),
            term = app_term, level = 1
        )

        # Generate username and password
        username = str(applicant.fname)[:4] + str(applicant.sname)[0:2]
        password = generate_password()

        # Create user
        user = User.objects.create_user(
            username=username, password=password,
            first_name=applicant.fname, last_name=applicant.sname,
            email=applicant.email, is_active=True
        )
        # Create UserProfile if applicable
        UserProfile.objects.create(user=user, branch=applicant.branch, phone=applicant.phone, picture=applicant.passport)
        # Assign to Students group
        students_group = Group.objects.get(name="Students")
        user.groups.add(students_group)

        # new_student.user = user
        # new_student.save()

        # Update Application
        applicant.regno = new_perm_regno
        applicant.state = "Joined"
        applicant.save()

        # Send Email/ SMS
        message = f"{applicant.fname} {applicant.sname} have joined the school. The student has been assigned a permanent registration number: {new_perm_regno}"
        send_mail("COURSE APPLICATION", message, None, [settings.ADMIN_EMAIL,])
        message = f"Dear {applicant.fname} {applicant.mname}, \nYour have successfuly joined our school. \n\nYour Login Credential: \nUsername: {username}\nPassword: {password}"
        send_mail("COURSE APPLICATION", message, None, [applicant.email, ])

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
        message = f"{application.fname} {application.mname}'s application have been declined."
        send_mail("COURSE APPLICATION", message, None, [settings.ADMIN_EMAIL,])
        message = f"Dear {application.fname} {application.mname}, \nWe regret to inform you that your application have been declined."
        send_mail("COURSE APPLICATION", message, None, [application.email, ])

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

