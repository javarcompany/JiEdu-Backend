from django.urls import path, include  #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import *

router = DefaultRouter()
router.register(r'days', DayViewSet, basename='days')
router.register(r'lessons', TableSetupViewSet, basename='lessons')
router.register(r'tables', TableViewSet, basename='tables')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/timetable-count/', timetable_count, name="timetable-count"),
    path("api/timetable/current-lessons/", current_lessons, name = "current-lessons"),
    path('api/days-options/', day_choices, name="day-options"),
    path('api/code-options/', code_choices, name="code-options"),
    path('api/available-slots/', available_lesson_slots, name = 'available-slots'),
    path('api/check_trainer_conflict/', check_trainer_conflict, name = 'check-trainer-conflict'),
    path('api/check_classroom_conflict/', check_classroom_conflict, name = 'check-classroom-conflict'),
    path('api/allocate-timetable/<int:class_id>/<int:day_id>/', allocate_timetable, name = 'allocate-timetable'),

    path('api/timetable/staff/', staff_timetable, name='staff-timetable'),
    path('api/timetable/student/<int:id>', student_timetable, name='student-timetable'),
    path("api/institution-timetable/", institution_timetable),
    path('api/timetable/class/', class_timetable, name='class-timetable'),
    path('api/timetable/department/', department_timetable, name='department-timetable'),

    path('api/change-timetable/', change_timetable, name="change-timetable"),

]
