from django.urls import path, include  #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import *

router = DefaultRouter()
router.register(r'users', UsersViewSet, basename='users')
router.register(r'academic-year', AcademicYearViewSet, basename='academicyear')
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'intakes', IntakeViewSet, basename='intakes')
router.register(r'terms', TermViewSet, basename='terms')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'institution', InstitutionViewSet, basename='institution')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'course-durations', CourseDurationViewSet, basename='course-duration')
router.register(r'units', UnitViewSet, basename='unit')
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'classrooms', ClassroomViewSet, basename='classroom')
router.register(r'sponsors', SponsorViewSet, basename='sponsor')

urlpatterns = [
    path('api/', include(router.urls)),

    path('api/auth/login/', CleanLoginView.as_view(), name='clean-login'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    
    path('api/unit_count/', unit_count, name='units-count'),
    path('api/users_count/', users_count, name='users-count'),
    path('api/branch_count/', branch_count, name='branch-count'),
    path('api/current_user/', current_user, name='current-user'),

    path('api/genders/', gender_choices, name="genders"),    
    path('api/relationship-choices/', relationship_choices, name="relationships"),
    path('api/exam-choices/', exam_choices, name="exam-choices"),
    path('api/groups/', GroupListCreateView.as_view(), name="list_group"),
    path('api/groups/delete/<int:group_id>/', DeleteGroupView.as_view(), name="delete_group"),
    path('api/groups/<str:group>/assign_permissions/', assign_permission_to_group, name='assign_permissions'),
    path("api/app-models/", AppModelListView.as_view(), name="app-models"),
    path('api/role-permissions/', get_role_permissions, name="role-permissions"),
    path('api/permissions/', list_permissions, name="list-permissions"),

    path('api/promote-system/', promote_system, name = "promote-system"),

    path("api/reset-password/<str:username>/", reset_own_password, name="reset-own-password"),
    path("api/check-token/", check_token, name="check-token"),
    path("api/download-template/", download_school_template, name="download_template"),
    
]