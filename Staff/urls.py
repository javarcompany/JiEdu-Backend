from django.urls import path, include  #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import *

router = DefaultRouter()
router.register(r'staffs', StaffViewSet, basename='staff')
router.register(r'staff-workloads', StaffWorkloadViewSet, basename = 'staff-workload')
router.register(r'class-tutors', ClassTutorViewSet, basename = 'class-tutor')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/search-staff-primary/', get_staff_primary_data, name='search-staff-primary'),

    path('api/search-staff-workloads/', get_staff_units, name='search-staff-units'),

    path('api/staff-workloads/individual/<int:id>', staff_workload, name = "staff-workload"),
    path('api/staff_count/<str:filter>/', staff_count, name='staff-count'),

    path('api/assign-workloads/<int:unit_id>/<int:lecturer_id>/<int:class_id>/', assign_workload_view, name="assign-workload"),
    path('api/workload/assign-batch/', assign_workloads_batch, name='assign-batch'),
    path('api/tutors/assign/<int:class_id>/<int:lecturer_id>/', assign_tutor_view, name='assign-batch'),
    path('api/staff-workload-count-comparision/', get_current_and_previous_pending_workload, name="staff-workload-count-comparision"),
    path('api/staff-tutor-count-comparision/', get_current_and_previous_pending_tutor, name="staff-tutor-count-comparision"),

    path('api/unassigned-classes/', unassigned_classes, name="unassigned-classes"),
    path('api/search-class-lecturers/', search_class_lecturers, name="search-class-lecturers"),
    path('api/change-class-tutor/', change_class_tutor, name = "change-class-tutor"),

    path('api/search-workload-lecturers/', search_workload_lecturers, name="search-workload-lecturers"),
    path('api/change-unit-workload/', change_unit_workload, name = "change-unit-workload"),
    path('api/check-new-lecturer-workload/', check_new_lecturer_workload, name="check-new-lecturer-workload"),

    path('api/lecturer-classes/', get_staff_classes, name="lecturer-classes"),

]