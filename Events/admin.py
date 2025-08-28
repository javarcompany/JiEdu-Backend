from django.contrib import admin #type:ignore
from .models import *
from django.urls import reverse #type:ignore
from django.utils.http import urlencode #type:ignore
from django.utils.html import format_html #type:ignore

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start_datetime", "end_datetime", "location", "created_by")

@admin.register(EventParticipant)
class EventParticipantAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "status", "joined_at")

@admin.register(EventReminder)
class EventReminderAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "reminder_time", "method", "sent")
