from django.urls import path, include #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore

from .views import *

router = DefaultRouter()
router.register("lessons", LessonViewSet, basename="lessons")

urlpatterns = [
    path("", include(router.urls)),
    path("api/lms/unit/", get_unit_details, name = "lms-units"),
    path("api/units/toggle-publish/", publish_unit, name = "toggle-units"),
]
