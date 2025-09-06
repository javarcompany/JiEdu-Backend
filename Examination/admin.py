from django.contrib import admin #type:ignore

from .models import *

@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "start_date", "end_date")

@admin.register(ExamTimetable)
class ExamTimetableAdmin(admin.ModelAdmin):
    list_display = ("exam_type", "exam_date", "venue", "session")

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("exam", "text", "question_type", "status")

@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = ("question", "text", "is_correct")

@admin.register(ExamRegistration)
class ExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ("student", "exam")

@admin.register(ExamSubmission)
class ExamSubmissionAdmin(admin.ModelAdmin):
    list_display = ("registration", "submitted_at", "is_submitted")

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("submission", "question", "response_text")

@admin.register(GradingScheme)
class GradingSchemeAdmin(admin.ModelAdmin):
    list_display = ("course", "min_mark", "max_mark", "grade", "remark")

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("exam", "student", "total_marks", "grade", "remark")
