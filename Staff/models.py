# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models #type: ignore
from django import utils #type: ignore
import numpy as np #type:ignore

from django.db.models.fields.files import ImageField  #type: ignore

import uuid
from django.contrib.contenttypes.models import ContentType #type:ignore
from django.contrib.contenttypes.fields import GenericForeignKey #type:ignore

from django.contrib.auth import get_user_model  #type:ignore
from django.contrib.auth.models import Group  #type:ignore

from Core.models import(
    UserProfile, GENDER_CHOICES, Branch, Department,
    Designation, STATE_CHOICES_STAFF, Term, Unit, Class,
    ALLOCATION_STATE_CHOICES
)

class Staff(models.Model):
    user = models.OneToOneField(UserProfile, blank=True, null=True, on_delete=models.CASCADE)
    regno = models.CharField(verbose_name="Registration Number", max_length=30, blank=True, null=True)
    fname = models.CharField(verbose_name='First Name', max_length=30) #first name
    mname = models.CharField(verbose_name='Middle Name', max_length=30, blank = True, null=True) #middle name
    sname = models.CharField(verbose_name='Sir Name', max_length=30) #sir name
    gender = models.CharField(choices=GENDER_CHOICES, max_length=20)
    nat_id = models.IntegerField(verbose_name='National ID') #national id
    phone = models.IntegerField() #phone number
    email = models.EmailField() #email address
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE, blank=True, null = True)
    weekly_hours = models.IntegerField(verbose_name="Weekly Hours", blank=True, null=True, default=0)
    used_hours = models.IntegerField(verbose_name="Used Hours", blank=True, null=True, default=0)
    load_state = models.CharField(verbose_name="Load State", max_length=30, choices=[("Booked", "Booked"), ("Above Optimum", "Above Optimum"), ("Average", "Average"), ("Available", "Available")], default="Available", blank=True, null=True)
    dob = models.DateTimeField(verbose_name='Date of Birth', default=utils.timezone.now, blank=True, null=True) #date of birth
    dor = models.DateTimeField(verbose_name='Date Registered', default=utils.timezone.now, blank=True, null=True) #date of registration
    passport = ImageField(upload_to='staff/', blank=True, null=True)
    state = models.CharField(choices=STATE_CHOICES_STAFF, max_length=30, default="Active")

    def __str__(self):
        return str(self.fname) +' '+ str(self.sname)

    def get_full_name(self):
        return f"{self.fname} {self.mname} {self.sname}"

    def get_name_reg(self):
        return f"{self.fname} {self.sname} - {self.regno}"

    class Meta:
        verbose_name = "Staff"
        verbose_name_plural = "Staffs"
        ordering = ("fname", "sname")


# ==========================================================================================#
# ========================        STAFF WORKLOAD MODULE            =========================#
class StaffWorkload(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    regno = models.ForeignKey(Staff, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    Class = models.ForeignKey(Class, on_delete=models.CASCADE)
    doa = models.DateTimeField(verbose_name='Date of Assignment', default=utils.timezone.now, blank = True, null=True)

    def __str__(self):
        return str(self.unit)+ ' ' +str(self.regno) + ' ' + str(self.Class.name)
    
    def getLoad(self):
        return str(self.unit)+ ' ' +str(self.regno) + ' ' + str(self.Class.name)
    
    class Meta:
        verbose_name = "Staff Workload"
        verbose_name_plural = "Staffs Workloads"
        unique_together = ("term", "regno", "unit", "Class")

class ClassTutor(models.Model):
    regno = models.ForeignKey(Staff, on_delete=models.CASCADE)
    Class = models.ForeignKey(Class, on_delete=models.CASCADE)
    doa = models.DateTimeField(verbose_name='Date of Assignment', default=utils.timezone.now, blank = True, null=True)
    state = models.CharField(max_length=30, choices=ALLOCATION_STATE_CHOICES, default="Pending")

    def __str__(self):
        return str(self.regno) +' '+ str(self.Class)

    class Meta:
        verbose_name = "Class Tutor"
        verbose_name_plural = "Class Tutors"
        unique_together = ("regno", "Class")
