from django.urls import path, include  #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import *

router = DefaultRouter()
router.register(r'attendance', StudentRegisterViewSet, basename='student-register')
router.register(r'attendance-modes', AttendanceModeViewSet, basename='atendance-modes')

urlpatterns = [
    path('api/', include(router.urls)),
    
    path('api/attendance-summary/', student_attendance_percentages, name="attendance-summary"),
    path('api/search-attendance/', search_student_attendance, name="search-student-attendance"),
    path('api/mark-attendance/', mark_attendance, name="mark-attendance"),
    path('api/student-analysis/', get_student_analysis, name="student-analysis"),
    path("api/student-unit-attendance/", get_student_unit_analysis, name = "student-unit-attendance"),
    path("api/student-lesson-analysis/", get_student_lesson_analysis, name = "student-lesson-attendance"),
    path("api/lecturer-lesson-analysis/", get_staff_lesson_analysis, name = "lecturer-lesson-attendance"),
    path("api/student-weekly-attendance/", student_weekly_attendance_trend, name = "student-weekly-trend"),
    path("api/student-module-attendance-summary/", get_student_module_summary_report, name = "student-module-attendance-summary"),
    path("api/student-daily-attendance-summary/", get_student_weekday_attendance_report, name="student-daily-attendance-summary"),
    path("api/class-attendance-summary/", get_class_attendance_summary, name="class-attendance-summary"),
    path("api/top-attendance-report/", get_top3_attendance_report, name="top-attendance-report"),
    path("api/class-weekday-attendance-report/", class_weekday_attendance_summary, name="class-weekday-attendance-report"),
    path("api/class-unit-attendance-report/", class_unit_attendance_summary, name="class-unit-attendance-report"),
    
    path("api/course-summary/", course_attendance_overview, name="course-summary"),
    path("api/course-attendance-summary/", course_attendance_summary, name="course-attendance-summary"),
    path("api/course-unit-attendance-report/", course_unit_attendance_summary, name="course-attendance-summary"),
    path("api/course-weekday-attendance-report/", course_weekday_attendance_summary, name="course-weekday-attendance-report"),
    path("api/course-class-average-weekday-attendance/", course_class_average_weekday_attendance, name="course-class-average-weekday-attendance"),
    path("api/course-unit-attendance-breakdown/", course_unit_attendance_breakdown, name="course-unit-attendance-breakdown"),

]