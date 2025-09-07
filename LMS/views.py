from rest_framework import viewsets, status, permissions #type: ignore
from rest_framework.decorators import api_view, permission_classes, action #type: ignore
from rest_framework.response import Response #type: ignore
from django.db.models import Prefetch #type: ignore


from Core.models import Unit
from .models import *
from .serializers import *

from Staff.models import StaffWorkload

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

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_unit_details(request):
    unit_id = request.query_params.get("unitId")
    if not unit_id:
        return Response({"error": "unitId is required"}, status=status.HTTP_400_BAD_REQUEST)

    unit = Unit.objects.filter(id=unit_id).first()
    if not unit:
        return Response({"error": "Unit not found"}, status=status.HTTP_404_NOT_FOUND)

    # Extract related details safely
    topics = (
        Chapter.objects.filter(unit=unit)
        .prefetch_related("lessons")  # optimize lessons
    )
    instructors = (
        StaffWorkload.objects.filter(unit__name__icontains = unit.name)
        .select_related("regno")  # optimize staff lookup
    )

    data = {
        "name": unit.name,
        "description": unit.description,
        "welcomeVideo": unit.welcome_video,
        "welcomeNote": unit.welcome_note,
        "objectives": unit.objectives.splitlines() if unit.objectives else [],
        "requirements": unit.requirements.splitlines() if unit.requirements else [],
        "lessons": [
            {"number": f"{lesson.chapter.number}.{lesson.number}", "title": lesson.title}
            for lesson in Lesson.objects.filter(chapter__in = topics)
        ],
        "topics": [
            {
                "number": topic.number,
                "title": topic.title,
                "lessons": [
                    {"number": lesson.number, "title": lesson.title}
                    for lesson in Lesson.objects.filter(chapter = topic)
                ],
            }
            for topic in topics
        ],
        "instructors": [
            {
                "id": inst.regno.id,
                "name": getattr(inst.regno, "get_full_name", lambda: inst.regno.get_full_name())(),
                "contact": getattr(inst.regno, "email", ""),
                "rating": getattr(inst.regno, "rating", None),
                "intro": getattr(inst.regno, "bio", ""),
                "photo": inst.regno.passport.url if getattr(inst.regno, "passport", None) else None,
            }
            for inst in instructors
        ],
    }

    return Response(data, status=status.HTTP_200_OK)
 
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def publish_unit(request):
    unit_id = request.query_params.get("unitid")
    print("Unit ID: ", unit_id)
    if not unit_id:
        return Response({"error": "unit id is required"}, status=status.HTTP_400_BAD_REQUEST)

    unit = Unit.objects.filter(id=unit_id).first()
    if not unit:
        return Response({"error": "Unit not found"}, status=status.HTTP_404_NOT_FOUND)

    text = ""
    if unit.is_published:
        unit.is_published = False
        text = "Published"
    else:
        unit.is_published = True
        text = "Unpublished"
    unit.save()

    return Response({"success":f"{unit.name} {text} Successfully!"}, status=status.HTTP_200_OK)
 