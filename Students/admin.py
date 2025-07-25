from django.contrib import admin #type:ignore
from .models import *
from django.urls import reverse #type:ignore
from django.utils.http import urlencode #type:ignore
from django.utils.html import format_html #type:ignore

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("regno","fname","mname","sname","gender","nat_id","phone","email","course","dor","year","passport")
    list_filter = ("gender", )

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('fname', 'email', 'regno')

@admin.register(RegistrationNumber)
class RegistrationNumberAdmin(admin.ModelAdmin):
    list_display = ('regno',)

@admin.register(Allocate_Student)
class Allocate_StudentAdmin(admin.ModelAdmin):
    list_display = ('studentno',)
