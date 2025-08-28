from rest_framework import serializers #type: ignore

from Core.application import is_rep_user, is_staff_user, is_student_user, is_tutor_user

from .models import *
from .application import *

class EventSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.username', read_only=True)
    term = serializers.CharField(source='term.name', read_only=True)
    department = serializers.CharField(source='department.name', read_only=True)
    course = serializers.CharField(source='course.name', read_only=True)
    class_name = serializers.CharField(source='Class.name', read_only=True)
    student = serializers.CharField(source='student.user.username', read_only=True)
    staff = serializers.CharField(source='staff.user.username', read_only=True)
    branch_name = serializers.CharField(source = 'branch.name', read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'title', 
                'description', 'start_datetime', 
                'end_datetime', 'is_all_day', 
                'location', 'created_by', 'term', 
                'department', 'course', 'class_name', 
                'student', 'staff', 'branch_name', 'branch', 'level'
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["created_by"] = user

        student_regno = self.context["request"].data.get("student_regno")
        staff_regno = self.context["request"].data.get("staff_regno")

        student_obj = Student.objects.filter(regno=student_regno).first() if student_regno else None
        staff_obj = Staff.objects.filter(regno=staff_regno).first() if staff_regno else None

        if is_student_user(user):  
            validated_data["visibility"] = "private"
            validated_data["student"] = student_obj
        
        if is_rep_user(user):  
            validated_data["visibility"] = "private"
            validated_data["student"] = student_obj

        if is_staff_user(user):  
            validated_data["visibility"] = "private"
            validated_data["staff"] = staff_obj

        if is_tutor_user(user):  
            validated_data["visibility"] = "private"
            validated_data["staff"] = staff_obj

        return super().create(validated_data)
    
class EventParticipantSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = EventParticipant
        fields = ["id", "event", "user", "user_name", "status", "joined_at"]
        read_only_fields = ["joined_at"]


class EventReminderSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = EventReminder
        fields = ["id", "event", "user", "user_name", "reminder_time", "method", "sent"]