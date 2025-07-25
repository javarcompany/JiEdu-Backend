from rest_framework import serializers #type: ignore
from django.contrib.auth.models import Group #type: ignore
from .models import *
from datetime import date

class StudentSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.abbr', read_only=True)
    year_name = serializers.CharField(source='year.name', read_only=True)
    intake_name = serializers.CharField(source='intake.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    sponsor_name = serializers.CharField(source='sponsor.name', read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'regno', 'fname', 'mname', 'sname', 'gender', 'dob', 'nat_id',
            'phone', 'email', 'course', 'course_name', 'branch', 'branch_name',
            'dor', 'year', 'year_name', 'intake', 'intake_name', 'sponsor', 'sponsor_name',
            'passport', 'state',
        ]

    def validate_dob(self, value):
        if value >= date.today():
            raise serializers.ValidationError("Date of birth must be in the past.")
        return value

    def validate_phone(self, value):
        value = str(value)
        if not value.isdigit() or len(value) < 10:
            raise serializers.ValidationError("Enter a valid phone number.")
        return value
    
    def get_dob(self, obj):
        return obj.dor.strftime("%Y-%m-%d")

class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            'category', 'fname', 'mname', 'sname', 'gender', 'dob', 'nat_id',
            'phone', 'email', 'religion', 'phy_addr', 'home_addr', 
            'guardian_fname', 'guardian_lname', 'guardian_email', 'guardian_phone', 
            'guardian_relationship', 'examtype', 'examyear', 'prev_schoolname', 
            'examgrade', 'previousexams', 'passport', 'course', 'branch', 'sponsor', 
            'year', 'intake'
        ]
    
    def create(self, validated_data):
        return super().create(validated_data)

class ApplicationDetailSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.abbr', read_only=True)
    year_name = serializers.CharField(source='year.name', read_only=True)
    intake_name = serializers.CharField(source='intake.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    sponsor_name = serializers.CharField(source='sponsor.name', read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'category', 'fname', 'mname', 'sname', 'gender', 'dob', 'nat_id',
            'phone', 'email', 'religion', 'phy_addr', 'home_addr', 'regno',
            'guardian_fname', 'guardian_lname', 'guardian_email', 'guardian_phone', 
            'guardian_relationship', 'examtype', 'examyear', 'prev_schoolname', 'sponsor_name',
            'examgrade', 'previousexams', 'passport', 'course', 'branch', 'sponsor', 'branch_name',
            'year', 'intake', 'course_name', 'year_name', 'intake_name', 'state']

class StudentAllocationSerializer(serializers.ModelSerializer):
    fname = serializers.CharField(source='studentno.fname', read_only=True)
    mname = serializers.CharField(source='studentno.mname', read_only=True)
    sname = serializers.CharField(source='studentno.sname', read_only=True)
    regno = serializers.CharField(source='studentno.regno', read_only=True)
    year_name = serializers.CharField(source='term.year.name', read_only=True)
    term_name = serializers.CharField(source='term.name', read_only=True)
    class_name = serializers.CharField(source='Class.name', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)
    passport = serializers.SerializerMethodField()
    branch =  serializers.CharField(source='studentno.branch.id', read_only=True)
    branch_name =  serializers.CharField(source='studentno.branch.name', read_only=True)
    course = serializers.CharField(source='studentno.course.id', read_only=True)
    course_name = serializers.CharField(source='studentno.course', read_only=True)
    student_state = serializers.CharField(source='studentno.state', read_only=True)

    class Meta:
        model = Allocate_Student
        fields = ['id', 'studentno', 'module', 'term', 'Class', 'doa', 'module_name',
            'year_name', 'term_name', 'class_name', 'fname', 'mname', 'sname', 'level',
            'regno', 'passport', 'state', 'branch', 'branch_name', 'course', 'course_name',
            'student_state'
        ]

    def get_passport(self, obj):
        request = self.context.get('request')
        if obj.studentno and obj.studentno.passport:
            passport_url = obj.studentno.passport.url
            return request.build_absolute_uri(passport_url) if request else passport_url
        return None
