# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models #type: ignore

from Core.models import (
    Course, Class, AcademicYear, Intake
)
from Timetable.models import Timetable
from Students.models import Student
from Staff.models import Staff

# ==========================================================================================#
# ========================              ATTENDANCE MODULE          =========================#
REGISTER_CHOICES = [
    ("Present", "Present"),
    ("Late", "Late"),
    ("Absent", "Absent"),
]

ATTENDANCE_TYPES = [
    ("Lesson", "Lesson"),
    ("Daily", "Daily"),
    ("Weekly", "Weekly"),
    ("Monthly", "Monthly"),
    ("Intake", "Intake"),
    ("Module", "Module")
]

class AttendanceModes(models.Model):
    name = models.CharField(max_length=255)
    dor = models.DateTimeField()
    
    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = 'Register Mode'
        verbose_name_plural = 'Register Modes'

class StudentRegister(models.Model):
    lesson = models.ForeignKey(Timetable, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    state = models.CharField(choices=REGISTER_CHOICES, max_length=255)
    dor = models.DateField()
    tor = models.TimeField()

    def __str__(self):
        return str(self.student) + " " + str(self.state)

    class Meta:
        verbose_name = 'Student Register'
        verbose_name_plural = 'Students Registers'

class StaffRegister(models.Model):
    lesson = models.ForeignKey(Timetable, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(Staff, on_delete=models.CASCADE)
    state = models.CharField(choices=REGISTER_CHOICES, max_length=255)
    dor = models.DateTimeField()
    tor = models.TimeField()

    def __str__(self):
        return str(self.lecturer) + " " + str(self.state)

    class Meta:
        verbose_name = 'Lecturer Register'
        verbose_name_plural = 'Lecturers Registers'
