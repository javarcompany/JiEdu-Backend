from django.utils import timezone #type: ignore
from django.contrib.auth.models import Group #type: ignore
from django.core.mail import send_mail  #type: ignore
from django.http import JsonResponse   #type: ignore
import string
import random
from uuid import uuid4
from django.conf import settings #type: ignore
from datetime import timedelta

from .models import *
from Core.models import User

# STAFF
# Assign Workload
def assign_workload(unit_id, lecturer_id, class_id):
    try:
        # Retrive information
        unit = Unit.objects.get(id=unit_id)
        print("Unit: ", unit)

        staff = Staff.objects.get(id = lecturer_id)
        print("Lecturer: ", staff)

        current_class = Class.objects.get(id = class_id)
        print("Class: ", current_class)

        currentTerm = current_class.intake
        print("Term: ", currentTerm)

        # Check Staff's Load
        Workload = StaffWorkload.objects.filter(term = currentTerm, regno = staff, unit=unit, Class = current_class)
        if Workload:
           return{'error': f"{staff} has already been assigned {unit} for {current_class}"}
        else:
            Workload = StaffWorkload.objects.filter(term = currentTerm, unit=unit, Class = current_class).first()
            if Workload:
                return {'error': f"{unit} has already been assigned for {current_class} to {Workload.regno}"}
            else:
                StaffWorkload.objects.update_or_create(term=currentTerm, regno=staff, unit=unit, Class = current_class)
                return {"message": "Staff workload saved successfully..."}

    except Unit.DoesNotExist:
        return {'error': 'Unit NOT found!'}
    
    except Staff.DoesNotExist:
        return {'error': 'Lecturer NOT found!'}

    except Class.DoesNotExist:
        return {'error': 'Class NOT found!'}
    
    except StaffWorkload.MultipleObjectsReturned:
        return {'error': 'Error saving the workload!'}

# Assign Class Tutor
def assign_tutor(class_id, lecturer_id):
    try:
        # Retrive information
        class_ = Class.objects.get(id=class_id)
        print("Class: ", class_)

        staff = Staff.objects.get(id = lecturer_id)
        print("Lecturer: ", staff)

        #  Get user
        user = User.objects.get(username = staff.regno)
        if not user:
            return {'error': f"Trainer Not registered as user.."}

        # Get Class Tutor Group
        class_tutor_group = Group.objects.filter(name__regex=r"(?i).*class.*tutor.*").first()
        if not class_tutor_group:
            return {'error': f'Class Tutor Group NOT found!'}
        
        Tutor = ClassTutor.objects.filter(Class = class_)
        if Tutor:
            Tutor = ClassTutor.objects.get(Class = class_)
            return{'error': f"{class_.name} has been assigned to {Tutor.regno}"}
        else:
            Tutor = ClassTutor.objects.filter(regno = staff)
            if Tutor:
                Tutor = ClassTutor.objects.get(regno = staff)
                return{'error': f"{staff} has already been assigned to {Tutor.Class.name}"}
            else:
                Tutor = ClassTutor.objects.filter(regno = staff, Class = class_)
                if Tutor:
                    return{'error': "Record Already exists..!"}
                else:
                    Tutor = ClassTutor(regno=staff, Class = class_, state = "Allocated")
                    Tutor.save()

                    # Change the tutors' designition to Class Tutor
                    user.groups.clear()  # Removes all existing groups
                    user.groups.add(class_tutor_group)  # Adds only "Class Tutor"

                    return{'message': f"{staff} assigned as the {class_.name} tutor successfully...."}
        
    except Class.DoesNotExist:
        return {'error': 'Class NOT found!'}
    except Staff.DoesNotExist:
        return {'error': 'Lecturer NOT found!'}
    except User.DoesNotExist:
        return {'error': f"Trainer Not registered as user.."}
