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

from Core.models import (
        Course, GENDER_CHOICES, Branch, UserProfile,
        AcademicYear, Sponsor, Intake,
        Module, Term, Class, ALLOCATION_STATE_CHOICES
)

STATE_CHOICES = [
    ("Active","Active"),
    ("Suspended","Suspended"),
    ("Graduated","Graduated"),
    ("Expelled","Expelled"),
    ("Cleared","Cleared"),
    ("Differ","Differ"),
    ("Inactive","Inactive")
]

APPLICATION_CATEGORY=[
    ("NEW STUDENT", "New Student"),
    ("CONTINUING", "Continuing"),
]

APPLICATION_CHOICES = [
    ("Pending", "Pending"),
    ("Approved", "Approved"),
    ("Declined", "Declined"),
    ("Joined", "Joined")
]

class Student(models.Model):
    # user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    regno = models.CharField(verbose_name="Registration Number", max_length=50, blank=True, null=True) #registration number
    fname = models.CharField(verbose_name='First Name', max_length=30) #first name
    mname = models.CharField(verbose_name='Middle Name', max_length=30, blank = True) #middle name
    sname = models.CharField(verbose_name='Sir Name', max_length=30) #sir name
    gender = models.CharField(choices=GENDER_CHOICES, max_length=20)
    dob = models.DateTimeField(verbose_name='Date of Birth') #date of birth
    nat_id = models.IntegerField(verbose_name='National ID', blank=True) #national id
    phone = models.IntegerField() #phone number
    email = models.EmailField() #email address
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="students")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    dor = models.DateTimeField(verbose_name='Date Registered', default=utils.timezone.now, blank=True, null=True) #date of registration
    year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE)
    sponsor = models.ForeignKey(Sponsor, on_delete=models.CASCADE, default = 1)
    passport = ImageField(upload_to='students/', blank=True, null=True)
    state = models.CharField(choices=STATE_CHOICES, max_length=30, default="Active", blank=True, null=True)

    def __str__(self):
        return str(self.regno)
    
    def get_full_name(self):
        return f"{self.fname} {self.mname} {self.sname}"

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"

# ==========================================================================================#
# ========================      STUDENT APPLICATION MODULE         =========================#

class Application(models.Model):
    category = models.CharField(choices=APPLICATION_CATEGORY, verbose_name="Application Type",blank=True, null=True, max_length=15, default="NEW STUDENT")
    regno = models.CharField(verbose_name='Registration Number', max_length=40, blank = True, null=True)
    fname = models.CharField(verbose_name='First Name', max_length=30) #first name
    mname = models.CharField(verbose_name='Middle Name', max_length=30, blank = True) #middle name
    sname = models.CharField(verbose_name='Sir Name', max_length=30) #sir name
    gender = models.CharField(choices=GENDER_CHOICES, max_length=20)
    dob = models.DateTimeField(verbose_name='Date of Birth') #date of birth
    nat_id = models.IntegerField(verbose_name='National ID', blank=True, null=True) #national id
    phone = models.IntegerField() #phone number
    email = models.EmailField(unique=True) #email address
    religion = models.CharField(verbose_name='Religion', max_length=50)
    phy_addr = models.CharField(verbose_name='Physical Address', max_length=50)
    home_addr = models.CharField(verbose_name='Home Address', max_length=50)
    guardian_fname = models.CharField(verbose_name='Guardian First Name', max_length=50,blank=True, null = True)
    guardian_lname = models.CharField(verbose_name='Guardian Last Name', max_length=50,blank=True, null = True)
    guardian_email = models.EmailField(blank=True, null = True) #email
    guardian_phone = models.IntegerField(blank=True, null = True) #phone number
    guardian_relationship = models.CharField(verbose_name='Guardian Relationship', max_length=50,blank=True, null = True)
    examtype = models.CharField(verbose_name='Previous Exams Type', max_length=50)
    examyear = models.IntegerField(blank=True, null = True)
    prev_schoolname = models.CharField(verbose_name='Previous School Name', max_length=150)
    examgrade = models.CharField(verbose_name='Previous Grade', max_length=50)
    previousexams = ImageField(upload_to='uploads/')
    passport = ImageField(upload_to='students/')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    sponsor = models.ForeignKey(Sponsor, on_delete=models.CASCADE)
    year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE)
    doa = models.DateTimeField(verbose_name='Date of Application', blank=True, null=True, default=utils.timezone.now) #date of application
    state = models.CharField(choices=APPLICATION_CHOICES, max_length=40, blank=True, null=True, default="Pending")

    def __str__(self):
        return self.fname +"'s Application"
    
    def get_full_name(self):
        return f"{self.fname} {self.mname} {self.sname}"

    class Meta:
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'

class RegistrationNumber(models.Model):
    regno = models.CharField(verbose_name="Random Code", max_length=100) #registration numbers
    intake = models.ForeignKey(Intake, on_delete=models.CASCADE)
    year = models.ForeignKey(AcademicYear, verbose_name='Academic Year', on_delete=models.CASCADE)
    doe = models.DateTimeField(verbose_name='Date of Enquiry', default=utils.timezone.now, blank = True, null=True) #date of enquiry
    valid_date = models.DateTimeField(verbose_name='Date of Expiry', default=utils.timezone.now, blank = True, null=True) #date of expiry
    temporary = models.BooleanField(verbose_name='Temporary Number', default=True)

    def __str__(self):
        return str(self.regno)

    class Meta:
        verbose_name = 'Registration Number'
        verbose_name_plural = 'Registration Numbers'

# ==========================================================================================#
# ========================      STUDENT ALLOCATION MODULE          =========================#

class Allocate_Student(models.Model):
    studentno = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='students')
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    Class = models.ForeignKey(Class, on_delete=models.CASCADE, null=True, blank=True)
    level = models.IntegerField()
    state = models.CharField(choices=ALLOCATION_STATE_CHOICES, max_length=30, default= "Pending")
    doa = models.DateTimeField(default=utils.timezone.now, blank = True, null=True)

    def __str__(self):
        return str(self.studentno) +'#'+ str(self.module)

    class Meta:
        verbose_name = 'Student Allocation'
        verbose_name_plural = 'Students Allocation'
        unique_together = ('studentno', 'term')
