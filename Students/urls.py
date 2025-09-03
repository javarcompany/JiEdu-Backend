from django.urls import path, include  #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import *

router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='student')
router.register(r'applications', ApplicationViewSet, basename='application')

router.register(r'students-allocations', StudentAllocationViewSet, basename='student-allocation')

urlpatterns = [
    path('api/', include(router.urls)),

    path('api/students-class-details/', get_student_class_details, name='search-student-class-details'),
    path('api/search-student-primary/', get_student_primary_data, name='search-student-primary'),
    path('api/search-student-units/', get_student_units, name='search-student-units'),
    path('api/search-student-lesson-counts/', get_student_lesson_counts, name='search-student-lesson-counts'),

    path('api/student_count/<str:filter>/', student_count, name='student-count'),
    path('api/student-count-enrollment/', get_current_and_previous_enrollment, name="student-count-enrollment"),
    path('api/student-count-pending/', get_current_and_previous_pending_enrollment, name="student-count-pending-enrollment"),

    path('api/check-application-status/', check_application_status, name='check-application-status'),
    path('api/approve-application/<int:app_id>/', approve_new_application, name="approve-application"),
    path('application/enroll/<int:temp_no>/', enroll_new_application, name="enroll-application"),
    path('api/application/approve-batch-applications/', batch_approve_view, name='approve-batch'),
    path('api/decline-application/<int:app_id>/', decline_new_application, name="decline-application"),
    path('api/application/decline-batch-applications/', batch_decline_view, name='decline-batch'),
    
    path('api/allocate/allocate-batch/', batch_allocate_view, name='allocate-batch'),
    path('api/allocate-student/<int:stud_id>/<int:class_id>/', allocate_view, name="allocate-student"),
    path('api/student-allocation-count-pending/', get_current_and_previous_pending_allocation, name="student-count-pending-allocation"),

    path('api/search-student-state/', check_student_state, name='search-student-state'),
    path('api/promote/', promote_myself, name='promote'),
    path('api/promote/promote-batch/', batch_promote_view, name='promote-batch'),
    path('api/promote/institution-promotion-status/', institution_promotion_status, name="institution-promotion-status"),
    
    path('api/student/units/<int:id>/', student_units, name = 'student-units'),

    path('api/branch-student-stats/', branch_student_stats, name = "branch-student-stats"),

    path('api/search-student-class/', search_student_class, name="search-student-class"),
    path('api/change-student-allocations/', change_student_class, name = "change-student-allocations"),
    
    # Report
    path('api/department-gender-summary/', department_gender_summary, name = "department_gender_summary"),
    path('api/department-age-summary/', department_age_summary, name = "department_age_summary"),
    path('api/department-exams-summary/', department_exams_summary, name = "department_exams_summary"),
    path('api/institution-enrollment-summary/', institution_enrollment_summary, name = "enrollment-summary"),
    path('api/institution-enrollment-trend/', institution_enrollment_trend, name = "enrollment-trend"),
    path('api/student-enrollment-status-trend/', student_enrollment_status_trend, name = "enrollment-status-trend"),
    path('api/student-gender-trend/', student_gender_trend, name = "student-gender-trend"),
    path("api/predict-applications/", predict_applications, name = "predict-application"),

    path('api/course-gender-breakdown/', course_gender_breakdown, name ="course-gender-breakdown"),
    path('api/course-age-breakdown/', course_age_summary, name= "course-age-breakdown"),
    path('api/course-exams-breakdown/', course_exams_summary, name= "course-exams-breakdown"),

    path('api/fetch-classmates/', fetch_classmates, name="fetch-classmates"),
    path('api/fetch-student-previous-exams/', fetch_previous_exams, name="fetch-student-previous-exams"),
    path('api/student-primary-course-data/', fetch_student_primary_data, name="student-primary-course-data"),
    

]