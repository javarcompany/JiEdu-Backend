from django.contrib import admin #type:ignore
from .models import *
from django.urls import reverse #type:ignore
from django.utils.http import urlencode #type:ignore
from django.utils.html import format_html #type:ignore

@admin.register(AttendanceModes)
class AttendanceModesAdmin(admin.ModelAdmin):
    list_display = ('name', )

@admin.register(StudentRegister)
class StudentRegisterAdmin(admin.ModelAdmin):
    list_display = ("student", "dor",)

@admin.register(StaffRegister)
class StaffRegisterAdmin(admin.ModelAdmin):
    list_display = ('lecturer', )