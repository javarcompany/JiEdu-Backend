from rest_framework import serializers #type: ignore
from .models import *

class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseContent
        fields = ["id","kind","order","text","file","external_url","caption"]

class LessonListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id","title","summary","order","is_published"]

class LessonDetailSerializer(serializers.ModelSerializer):
    contents = ContentSerializer(many=True, read_only=True)
    class Meta:
        model = Lesson
        fields = ["id","title","summary","order","is_published","contents"]

class ChapterSerializer(serializers.ModelSerializer):
    lessons = LessonListSerializer(many=True, read_only=True)
    class Meta:
        model = Chapter
        fields = ["id","title","description","order","lessons"]
