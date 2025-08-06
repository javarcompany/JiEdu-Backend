# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models #type: ignore
from django import utils #type: ignore

from django.db.models.fields.files import ImageField  #type: ignore

from django.contrib.auth import get_user_model  #type:ignore
from django.contrib.auth.models import Group  #type:ignore
from django.core.exceptions import ValidationError #type:ignore

User = get_user_model()

DEPARTMENTCHOICES = [
    ("Administration", "ADMINISTRATION"),
    ("Academic", "ACADEMIC")
]

EXAM_CHOICES = [
    ("KCPE", "KCPE"),
    ("KCSE", "KCSE"),
    ("Certificate", "Certificate"),
    ("Diploma", "Diploma"),
    ("Degree", "Degree"),
    ("Masters", "Masters"),
]

INTAKE_CHOICES = [
    ("JANUARY", "January"),
    ("FEBRUARY", "February"),
    ("MARCH", "March"),
    ("APRIL", "April"),
    ("MAY", "May"),
    ("JUNE", "June"),
    ("JULY", "July"),
    ("AUGUST", "August"),
    ("SEPTEMBER", "September"),
    ("OCTOBER", "October"),
    ("NOVEMBER", "November"),
    ("DECEMBER", "December")
]

GENDER_CHOICES = [
    ("Male", "Male"),
    ("Female", "Female")
]

STATE_CHOICES_STAFF = [
    ("Active","Active"),
    ("Suspended","Suspended"),
    ("Transfered","Transfered"),
    ("Leave","Leave"),
    ("Retired","Retired")
]

CLASS_CHOICES = [
    ('Active','Active'),
    ('Cleared','Cleared')
]

CLASSROOM_CHOICES = [
    ('Active','Active'),
    ('Abandoned','Abandoned'),
    ('Inactive', 'Inactive')
]

SPONSOR_CHOICES = [
    ("Active", "ACTIVE"),
    ("Inactive", "INACTIVE"),
]

RELATIONSHIP_CHOICES = [
    ("Father", "Father"),
    ("Mother", "Mother"),
    ("Brother", "Brother"),
    ("Sister", "Sister"),
    ("Cousin", "Cousin"),
    ("Uncle", "Uncle"),
    ("Aunt", "Aunt"),
    ("Grandfather", "Grandfather"),
    ("Grandmother", "Grandmother")
]

ALLOCATION_STATE_CHOICES = [
    ("Allocated","Allocated"),
    ("Pending","Pending"),
]

class Branch(models.Model):
    name = models.CharField(verbose_name = "Branch Name", default= "Main Campus", null=True, blank=True, max_length=115)
    code = models.CharField(verbose_name="Branch Code", unique=True, max_length=25)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    paddr = models.CharField(verbose_name='Physical Address', max_length=255)
    dor = models.DateTimeField(verbose_name='Date Registered', default = utils.timezone.now, blank=True, null=True) #date of registration
    tel_a = models.IntegerField(verbose_name='Telephone 1') #telephone address A
    tel_b = models.IntegerField(verbose_name = 'Telephone 2', blank=True, null = True) #telephone address B
    email = models.EmailField()

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural = "Branches"
        unique_together = ('name', 'email')

# ==========================================================================================#
# ========================               USERS MODULE              =========================#
class GroupProfile(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="profile")
    icon = models.CharField(max_length=100, blank=True, null=True)  # e.g., 'fa-user-cog'
    members = models.ManyToManyField(User, related_name="group_profiles", blank=True)

    def __str__(self):
        return f"{self.group.name} Profile"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    picture = models.ImageField("User's passport image", upload_to="users/")
    phone = models.CharField(max_length=20, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username

# ==========================================================================================#
# ========================                CORE MODULE              =========================#
class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True)
    dor = models.DateTimeField(verbose_name = 'Date Registered', default=utils.timezone.now, blank=True, null= True)

    def __str__(self):
        return self.name 

    class Meta:
        verbose_name = 'Academic Year'
        verbose_name_plural = "Academic Years"

class Module(models.Model):
    name = models.CharField(max_length=255)
    abbr = models.CharField(verbose_name="Abbreviation", max_length=25)
    dor = models.DateTimeField(verbose_name="Date Registered", default=utils.timezone.now, blank = True, null=True) #date of registration
    
    def __str__(self):
        return self.abbr

    class Meta:
        verbose_name_plural = "Module"

class Intake(models.Model):
    name = models.CharField(max_length=25, blank=True, null=True)
    openingMonth = models.CharField(choices= INTAKE_CHOICES, verbose_name = 'Opening Month', max_length=255)
    closingMonth = models.CharField(choices= INTAKE_CHOICES, verbose_name = 'Closing Month', max_length=25)
    dor = models.DateTimeField(verbose_name='Date of Registration', default=utils.timezone.now, blank = True, null=True) #date of registration

    def __str__(self):
        self.name = str(self.openingMonth)[0:3]+'/'+str(self.closingMonth)[0:3]
        return str(self.openingMonth) +'/'+ str(self.closingMonth)

    class Meta:
        verbose_name = "Intake"
        verbose_name_plural = "Intakes"
 
class Institution(models.Model):
    logo = ImageField(upload_to='logo/', blank=True, null=True)
    name = models.CharField(max_length=255)
    motto = models.TextField()
    mission = models.TextField()
    vision = models.TextField()
    paddr = models.CharField(verbose_name='Physical Address', max_length=255) #physical address
    tel_a = models.IntegerField(verbose_name='Telephone 1') #telephone address A
    tel_b = models.IntegerField(verbose_name = 'Telephone 2', blank=True, null = True) #telephone address B
    facebook = models.URLField(verbose_name="Facebook", blank=True, null=True)
    telegram = models.URLField(verbose_name="Telegram", blank=True, null=True)
    instagram = models.URLField(verbose_name="Instagram", blank=True, null=True)
    youtube = models.URLField(verbose_name="Youtube", blank=True, null=True)
    twitter = models.URLField(verbose_name="Twitter", blank=True, null=True)
    tiktok = models.URLField(verbose_name="TikTok", blank=True, null=True)
    email = models.EmailField()
    current_year = models.ForeignKey(AcademicYear, verbose_name='Current Year', on_delete=models.CASCADE)
    current_intake = models.ForeignKey(Intake, verbose_name='Current Term', on_delete=models.CASCADE)
    newsystem = models.BooleanField(default=True, blank=True, null=True)
    dof = models.DateTimeField(verbose_name= 'Date Founded', blank=True, null=True) #date of foundation
    promotionMode = models.BooleanField(default=False, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.pk and Institution.objects.exists():
            raise ValidationError("Only one Institution instance is allowed.")
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def getShortName(self):
        name = (str(self.name)).split(" ")
        abb = ''
        for x in range(len(name)):
            if x == 0:
                pass
            else:
                abb += name[x][0]
        return name[0]+ ' '+ abb

    class Meta:
        verbose_name = 'Institution'
        verbose_name_plural = "Institution"

class Term(models.Model):
    name = models.ForeignKey(Intake, on_delete=models.CASCADE)
    openingDate = models.DateTimeField(default=utils.timezone.now, blank=True, null=True)
    closingDate = models.DateTimeField(default = utils.timezone.now, blank=True, null=True)
    year =models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    dor = models.DateTimeField(verbose_name='Date Registered',default = utils.timezone.now, blank=True, null=True) #date of registration

    def __str__(self):
        return str(self.name) + '-' + str(self.year)

    class Meta:
        verbose_name_plural = "Intake Series"
        unique_together = ('name', 'year')

class Department(models.Model):
    category = models.CharField(max_length=40, choices=DEPARTMENTCHOICES, default="Academic")
    name = models.CharField(max_length=255)
    abbr = models.CharField(verbose_name='Abbreviation', max_length=20, unique=True) #abbreviation of the name
    dor = models.DateTimeField(verbose_name='Date Registered', blank=True, null=True, default=utils.timezone.now) #date of registration

    def __str__(self):
        return self.abbr

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = "Departments"

class Course(models.Model):
    code = models.IntegerField(unique = True)
    name = models.CharField(max_length=255)
    abbr = models.CharField(verbose_name='Abbreviation',max_length=20)
    dor = models.DateTimeField(verbose_name='Date Registered', blank=True, null=True, default=utils.timezone.now) #date of registration
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    module_duration = models.IntegerField(verbose_name='Module Duration', default=1)
    
    def __str__(self):
        return self.abbr

    class Meta:
        unique_together = ("name", "department" )
        verbose_name_plural = "Courses"
    
class CourseDuration(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    duration = models.IntegerField(verbose_name='Duration(Terms)')
    dor = models.DateTimeField(default=utils.timezone.now, blank=True, null=True)

    def __str__(self):
        return str(self.course) +'#'+ str(self.module) +'#'+ str(self.duration)

    class Meta:
        verbose_name = 'Course Duration'
        verbose_name_plural = 'Courses Durations'
        unique_together = ('course', 'module')

class Unit(models.Model):
    uncode = models.CharField(max_length=30, verbose_name='Unit Code', unique=True, blank=False)
    name = models.CharField(max_length=255)
    abbr = models.CharField(verbose_name='Abbreviation', max_length=20)
    dor = models.DateTimeField(verbose_name='Date Registered', default=utils.timezone.now, blank=True, null=True) #date of registration
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    weekly_hours = models.IntegerField(verbose_name="Weekly Hours", blank=True, null=True)

    def __str__(self):
        return str(self.uncode) +'  ('+ str(self.abbr) +')'
    
    def get_code(self):
        return self.uncode

    class Meta:
        verbose_name_plural = "Units"
        unique_together = ("uncode", "abbr", )

class Class(models.Model):
    name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    intake = models.ForeignKey(Term, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    level = models.IntegerField(default=1, blank=True, null=True)
    state = models.CharField(choices=CLASS_CHOICES, max_length=30, default='Active', blank=True, null=True)
    dor = models.DateTimeField(verbose_name='Date Registered', default=utils.timezone.now, blank=True, null=True) #date of registration

    def __str__(self):
        return self.name +'_'+ str(self.intake)
    
    class Meta:
        verbose_name_plural = "Class"
        unique_together = ("name", "intake")

class Classroom(models.Model):
    name = models.CharField(max_length=255, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    state = models.CharField(
        choices=CLASSROOM_CHOICES,
        max_length=30,
        default='Inactive',
        blank=True,
        null=True
    )
    dor = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Classrooms"

class Designation(models.Model):
    name = models.CharField(max_length=255)
    abbr = models.CharField(verbose_name='Abbreviation', max_length=25)
    dor = models.DateTimeField(verbose_name='Date Registered', default=utils.timezone.now, blank=True, null=True) #date of registration

    def __str__(self):
        return self.abbr
    
    class Meta:
        verbose_name_plural = "Designations"

class Sponsor(models.Model):
    name = models.CharField(verbose_name='Name', unique=True, max_length=30, default="Self", blank=True, null=True) #name
    phone = models.IntegerField(blank=True, null=True) #phone number
    email = models.EmailField(blank=True, null=True) #email address
    dor = models.DateTimeField(verbose_name='Date Registered', default=utils.timezone.now, blank=True, null=True) #date of registration
    state = models.CharField(choices=SPONSOR_CHOICES, max_length=30, default = "Active", blank=True, null=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = "Sponsor"
        verbose_name_plural = "Sponsors"
        ordering = ("name", "state")
