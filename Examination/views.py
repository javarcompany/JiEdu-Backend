from django.shortcuts import render #type: ignore
from django.contrib.auth.decorators import user_passes_test #type: ignore
from django.http import JsonResponse #type: ignore

from .models import *

def is_exams_officer(user):
    return user.groups.filter(name="ExamsOfficer").exists()

@user_passes_test(is_exams_officer)
def approve_exam(request, exam_id):
    exam = ExamTimetable.objects.get(id=exam_id)
    exam.status = "approved"
    exam.approved_by = request.user.staff
    exam.save()
    return JsonResponse({"message": "Exam approved"})

