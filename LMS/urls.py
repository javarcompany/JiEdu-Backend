# lms/urls.py
from django.urls import path, include #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import LessonViewSet

router = DefaultRouter()
router.register("lessons", LessonViewSet, basename="lessons")

urlpatterns = [path("", include(router.urls))]
