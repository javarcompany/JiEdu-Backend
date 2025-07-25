# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models #type: ignore
from django import utils #type: ignore

from datetime import datetime, timedelta
from django.utils import timezone #type: ignore

from Core.models import ( 
    Term, Class, Classroom, 
)
from Staff.models import StaffWorkload

# ==========================================================================================#
# ========================           TIMETABLE MODULE              =========================#
REPORT_TYPES = [
    ("DEPARTMENT", "Department"),
    ("CLASS", "Class"),
    ("LECTURER", "Lecturer")
]

LESSON_CATEGORY = [
    ("Lesson", "Lesson"),
    ("Break", "Break")
]

DAYS_OPTIONS = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
    ("Sunday", "Sunday")
]

class Days(models.Model):
    name = models.CharField(verbose_name="Week Day", unique=True, max_length=255)
    dor = models.DateTimeField(verbose_name='Date Registered', blank=True, null = True, default=utils.timezone.now)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Timetable Day'
        verbose_name_plural = 'Timetable Days'

class TableSetup(models.Model):
    name = models.CharField(verbose_name='Lesson Name', unique=True, max_length=255)
    start = models.TimeField(verbose_name = 'Start Time', unique=True, max_length = 25)
    duration = models.DurationField(verbose_name='Duration')
    end = models.TimeField(verbose_name='End Time', blank=True, null=True)
    code = models.CharField(verbose_name='Mode', max_length=25, choices=LESSON_CATEGORY, default="Lesson", blank=True, null=True)
    dor = models.DateTimeField(verbose_name='Date Registered', blank=True, null = True, default=utils.timezone.now)
                                                                                                                    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Timetable Setup'
        verbose_name_plural = 'Timetable Setups'

class Timetable(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    Class = models.ForeignKey(Class, on_delete=models.CASCADE)
    day = models.ForeignKey(Days, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    lesson = models.ForeignKey(TableSetup, on_delete=models.CASCADE)
    unit = models.ForeignKey(StaffWorkload, on_delete = models.CASCADE, blank=True, null=True)
    dor = models.DateTimeField(verbose_name='Date Registered', blank=True, null = True, default=utils.timezone.now)

    def __str__(self):
        return str(self.day) +' '+ str(self.lesson) + ' '+ str(self.unit)
 
    class Meta:
        verbose_name = 'Timetable'
        verbose_name_plural = 'Timetables'
        unique_together = ('term', 'day', 'lesson', 'Class')

class DummyTable(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    Class = models.ForeignKey(Class, on_delete=models.CASCADE)
    classroom = models.CharField(max_length=200)
    day = models.ForeignKey(Days, on_delete=models.CASCADE)
    lesson = models.ForeignKey(TableSetup, on_delete=models.CASCADE)
    unit = models.CharField(max_length=200)
    lecturer = models.CharField(max_length=200)
    dor = models.DateTimeField(verbose_name='Date Registered', blank=True, null = True, default=utils.timezone.now)

    def __str__(self):
        return self.day +' '+ str(self.lesson) + ' '+ str(self.unit)

    class Meta:
        verbose_name = 'Dummy Timetable'
        verbose_name_plural = 'Dummy Timetables'

