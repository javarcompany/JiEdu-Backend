# lms/views.py
from rest_framework import viewsets, permissions #type: ignore
from rest_framework.decorators import action #type: ignore
from rest_framework.response import Response #type: ignore
from django.db.models import Prefetch #type: ignore

from Core.models import Unit
from .models import *
from .serializers import *

class IsEnrolledOrReadOnly(permissions.BasePermission):
    """Students can view only if unit is published and they’re enrolled."""
    def has_object_permission(self, request, view, obj: Unit):
        if request.method in permissions.SAFE_METHODS:
            if obj.is_published:
                return True if request.user.is_staff else obj.enrollments.filter(student=request.user).exists()
        return request.user.is_staff  # staff/admin can manage

class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Lesson.objects.filter(is_published=True).select_related("topic__unit").prefetch_related("contents")
    serializer_class = LessonDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
