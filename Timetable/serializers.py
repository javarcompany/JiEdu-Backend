from rest_framework import serializers #type: ignore
from .models import *
from datetime import date

class DaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Days
        fields = '__all__'

class TableSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableSetup
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Convert start and end times to AM/PM format
        if instance.start:
            data['start'] = instance.start.strftime('%I:%M %p')  # e.g. 08:00 AM
        if instance.end:
            data['end'] = instance.end.strftime('%I:%M %p')      # e.g. 10:00 AM

        # Format duration in hours/minutes
        if instance.duration:
            total_seconds = instance.duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)

            if hours and minutes:
                data['duration'] = f"{hours}h {minutes}m"
            elif hours:
                data['duration'] = f"{hours}h"
            else:
                data['duration'] = f"{minutes}m"

        return data

class TimetableSerializer(serializers.ModelSerializer):
    year = serializers.CharField(source = 'term.year.name')
    intake = serializers.CharField(source = 'term.name.name')
    course = serializers.CharField(source = 'Class.course')
    branch = serializers.CharField(source = 'Class.branch')
    module = serializers.CharField(source = 'Class.module')
    class_name = serializers.CharField(source = 'Class.name')
    day_name = serializers.CharField(source = 'day.name')
    classroom_name = serializers.CharField(source = 'classroom.name')
    lesson_name = serializers.CharField(source = 'lesson.name')
    lecturer_fname = serializers.CharField(source = 'unit.regno.fname')
    lecturer_mname = serializers.CharField(source = 'unit.regno.mname')
    lecturer_sname = serializers.CharField(source = 'unit.regno.sname')
    lecturer_regno = serializers.CharField(source = 'unit.regno.regno')
    unit_name = serializers.CharField(source = 'unit.unit.abbr')
    unit_uncode = serializers.CharField(source = 'unit.unit.uncode')

    class Meta:
        model = Timetable
        fields = ['id', 'term', 'Class', 'day', 'classroom', 'lesson', 'unit', 'dor',
                  'year', 'intake', 'course', 'branch', 'module', 'class_name', 'day_name',
                  'classroom_name', 'lesson_name', 'lecturer_fname', 'lecturer_mname', 'lecturer_sname', 'lecturer_regno',
                  'unit_name', 'unit_uncode'
                ]

