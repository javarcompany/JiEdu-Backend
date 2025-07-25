from django.contrib import admin #type:ignore
from .models import *

@admin.register(KnownFace)
class KnownFaceAdmin(admin.ModelAdmin):
    list_display = ('regno', )

@admin.register(CameraDevice)
class CameraDevicesAdmin(admin.ModelAdmin):
    list_display = ('name', "ip_address", "role", )