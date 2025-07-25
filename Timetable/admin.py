from django.contrib import admin #type:ignore
from .models import *
from django.urls import reverse #type:ignore
from django.utils.http import urlencode #type:ignore
from django.utils.html import format_html #type:ignore

@admin.register(Days)
class DaysAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name__startswith", )
    list_filter = ("name", )

@admin.register(TableSetup)
class TableSetupAdmin(admin.ModelAdmin):
    list_display = ("name", 'start', 'duration', 'end', 'code',)
    search_fields = ("name__startswith", )
    list_filter = ("name", )

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ("term", 'Class', 'classroom', 'day', 'lesson',)
    search_fields = ("Class__startswith", )
    list_filter = ("Class", )