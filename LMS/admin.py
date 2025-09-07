from django.contrib import admin #type:ignore
from .models import *

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("number","unit","title","duration")
    search_fields = ("title__startswith", )
    list_filter = ("number", )

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('number', 'chapter', 'title', 'is_published')
    search_fields = ("title__startswith", )

@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    list_display = ('content_type', 'title', 'lesson')
    search_fields = ("title__startswith", )


