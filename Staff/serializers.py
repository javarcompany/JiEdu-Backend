from rest_framework import serializers #type: ignore
from .models import *
from datetime import date

class StaffSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    fullname = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            'id', 'regno', 'fname', 'mname', 'sname', 'gender', 'dob',
            'nat_id', 'phone', 'email', 'department', 'department_name',
            'branch', 'branch_name', 'dor', 'designation', 'weekly_hours',
            'used_hours', 'load_state',
            'passport', 'state', 'designation_name', "fullname", 'user'
        ]

    def validate_dob(self, value):
        if value.date() >= date.today():
            raise serializers.ValidationError("Date of birth must be in the past.")
        return value

    def validate_phone(self, value):
        value = str(value)
        if not value.isdigit() or len(value) < 9:
            raise serializers.ValidationError("Enter a valid phone number.")
        return value

    def get_fullname(self, obj):
        return f"{obj.fname} {obj.mname} {obj.sname} - {obj.regno}".strip()

class StaffWorkloadSerializer(serializers.ModelSerializer):
    fname = serializers.CharField(source='regno.fname', read_only=True)
    mname = serializers.CharField(source='regno.mname', read_only=True)
    sname = serializers.CharField(source='regno.sname', read_only=True)
    staff_regno = serializers.CharField(source='regno.regno', read_only=True)
    passport = serializers.SerializerMethodField()
    term_year = serializers.CharField(source='term.year.name', read_only=True)
    term_name = serializers.CharField(source='term.name.name', read_only=True)
    class_name = serializers.CharField(source='Class.name', read_only=True)    
    unit_name = serializers.CharField(source = 'unit.name', read_only = True)
    unitcode = serializers.CharField(source = 'unit.uncode', read_only = True)

    class Meta:
        model = StaffWorkload
        fields = ['id', 'term', 'regno', 'unit', 'Class', 'doa', 'term_name',
            'term_year', 'fname', 'mname', 'sname', 'staff_regno','passport', 
            'class_name', 'unit_name', 'unitcode'
        ]

    def get_passport(self, obj):
        request = self.context.get('request')
        if obj.regno and obj.regno.passport:
            passport_url = obj.regno.passport.url
            return request.build_absolute_uri(passport_url) if request else passport_url
        return None

class ClassTutorSerializer(serializers.ModelSerializer):
    fname = serializers.CharField(source='regno.fname', read_only=True)
    mname = serializers.CharField(source='regno.mname', read_only=True)
    sname = serializers.CharField(source='regno.sname', read_only=True)
    staff_regno = serializers.CharField(source='regno.regno', read_only=True)
    passport = serializers.SerializerMethodField()
    class_name = serializers.CharField(source='Class.name', read_only=True)    
   
    class Meta:
        model = ClassTutor
        fields = ['id', 'regno', 'Class', 'fname', 'mname', 'sname', 'staff_regno','passport', 
            'class_name', 'state'
        ]

    def get_passport(self, obj):
        request = self.context.get('request')
        if obj.regno and obj.regno.passport:
            passport_url = obj.regno.passport.url
            return request.build_absolute_uri(passport_url) if request else passport_url
        return None

