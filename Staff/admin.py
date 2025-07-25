from django.contrib import admin #type:ignore
from .models import *
from django.urls import reverse #type:ignore
from django.utils.http import urlencode #type:ignore
from django.utils.html import format_html #type:ignore

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("fname","mname","sname","gender","nat_id","phone","email","department","designation","dor","passport","state")
    search_fields = ("fname__startswith", )
    list_filter = ("gender", )

@admin.register(StaffWorkload)
class StaffWorkloadAdmin(admin.ModelAdmin):
    list_display = ('regno',)

@admin.register(ClassTutor)
class ClassTutorAdmin(admin.ModelAdmin):
    list_display = ('regno',)


