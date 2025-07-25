from rest_framework import serializers #type: ignore
from .models import *
from django.db.models import Sum #type: ignore
from decimal import Decimal

class CameraDeviceSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    class Meta:
        model = CameraDevice
        fields = '__all__'