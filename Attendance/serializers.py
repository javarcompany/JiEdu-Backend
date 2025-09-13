from rest_framework import serializers #type: ignore
from .models import *

class StudentRegisterSerializer(serializers.ModelSerializer):
    fname = serializers.CharField(source='student.fname')
    mname = serializers.CharField(source='student.mname')
    sname = serializers.CharField(source='student.sname')
    regno = serializers.CharField(source='student.regno')
    passport = serializers.SerializerMethodField()
    unit_name = serializers.CharField(source='lesson.unit.unit.abbr')
    class_name = serializers.CharField(source='lesson.Class.name')
    year_name = serializers.CharField(source='lesson.term.year')
    intake_name = serializers.CharField(source='lesson.term.name')
    lesson = serializers.CharField(source='lesson.lesson.name')
    day = serializers.CharField(source='lesson.day.name')
    dor_date = serializers.SerializerMethodField()

    percentage = serializers.SerializerMethodField()

    class Meta:
        model = StudentRegister
        fields = [
            'id', 'passport', 'regno', 'fname', 'mname', 'sname',
            'unit_name', 'class_name', 'year_name', 'intake_name',
            'day', 'lesson', 'dor', 'dor_date', 'state', 'percentage'
        ]

    def get_percentage(self, obj):
        # Replace with your actual logic
        return "100%"
    
    def get_dor_date(self, obj):
        return obj.dor.strftime("%Y-%m-%d")
    
    def get_passport(self, obj):
        request = self.context.get('request')
        if obj.student and obj.student.passport:
            passport_url = obj.student.passport.url
            # return request.build_absolute_uri(passport_url) if request else passport_url
            return passport_url
        return None

class AttendanceModesrSerializer(serializers.ModelSerializer):

    class Meta:
        model = AttendanceModes
        fields = "__all__"
