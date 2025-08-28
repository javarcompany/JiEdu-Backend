from rest_framework import viewsets, permissions, status #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, action, permission_classes#type: ignore
from rest_framework.pagination import PageNumberPagination #type: ignore
from django.utils import timezone #type: ignore
from datetime import datetime, timedelta
from itertools import chain

from Timetable.models import Timetable
from Core.models import Institution
from Core.application import is_student_user, is_rep_user, is_staff_user, is_tutor_user

from Students.models import Student, Allocate_Student

from .models import *
from .application import *
from .serializers import *
from .filters import *

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'count': self.page.paginator.count,
        })
    
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('id')
    serializer_class = EventSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def rsvp(self, request, pk=None):
        """
        RSVP to an event (Going, Not Going, Maybe)
        """
        event = self.get_object()
        status = request.data.get("status", "invited")

        participant, created = EventParticipant.objects.update_or_create(
            event=event, user=request.user,
            defaults={"status": status}
        )
        return Response(EventParticipantSerializer(participant).data)

class EventParticipantViewSet(viewsets.ModelViewSet):
    queryset = EventParticipant.objects.all().select_related("event", "user")
    serializer_class = EventParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    
    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)
    
class EventReminderViewSet(viewsets.ModelViewSet):
    queryset = EventReminder.objects.all().select_related("event", "user")
    serializer_class = EventReminderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    
    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_user_upcoming_events(request):
    """
    Returns upcoming events & lessons for the logged-in user:
    - Events: first 6, starting today or in the future (ignore past).
    - Lessons: first 4 upcoming timetable slots from today onwards.
    """
    now = timezone.now()
    today = timezone.localdate()

    user_regno = request.query_params.get("user_regno")
    user_groups = request.user.groups.values_list("name", flat=True)

    # --- Identify user type ---
    try:
        if any(g.lower().startswith("student") or "rep" in g.lower() for g in user_groups):
            student = Student.objects.get(regno=user_regno)
            user = Allocate_Student.objects.get(studentno=student)
            is_rep = any("rep" in g.lower() for g in user_groups)
            user_type = "rep" if is_rep else "student"
        else:
            user = Staff.objects.get(regno=user_regno)
            user_type = "staff"
    except Student.DoesNotExist:
        print("Student not found.")
        return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
    except Allocate_Student.DoesNotExist:
        print("Student allocation not found.")
        return Response({"detail": "Student allocation not found."}, status=status.HTTP_404_NOT_FOUND)
    except Staff.DoesNotExist:
        print("Staff not found.")
        return Response({"detail": "Staff not found."}, status=status.HTTP_404_NOT_FOUND)
    
    # --- Collect Events ---
    events = Event.objects.none()

    # 1b. Get the Limit for return
    limit_lessons = request.query_params.get("limit_lessons")

    if user_type in ["student", "rep"]:
        events |= Event.objects.filter(student=user.studentno)
        events |= Event.objects.filter(visibility="students")
        events |= Event.objects.filter(Class=user.Class)
        events |= Event.objects.filter(course=user.Class.course)
        events |= Event.objects.filter(branch=user.Class.branch)
        events |= Event.objects.filter(department=user.Class.course.department)
        if user_type == "rep":
            events |= Event.objects.filter(visibility="classreps")
    else:  # staff
        events |= Event.objects.filter(visibility="staff")
        events |= Event.objects.filter(staff=user)
        events |= Event.objects.filter(department=user.department)
        events |= Event.objects.filter(branch=user.branch)

    # Always include branch + public events
    events |= Event.objects.filter(visibility="public")

    # --- Deduplicate + Order ---
    events = (
        events.filter(start_datetime__date__gte=today)
        .filter(end_datetime__gte=now)
        .distinct()
        .order_by("start_datetime")
    )[:6]

    event_list = [
        {
            "title": e.title,
            "description": e.description,
            "start_datetime": e.start_datetime,
            "end_datetime": e.end_datetime,
            "event_type": e.event_type,
            "location": str(e.location),
        }
        for e in events
    ]

    # --- Lessons ---
    institution = Institution.objects.first()
    current_term = Term.objects.filter(name=institution.current_intake, year=institution.current_year).first()
    lessons_list = []

    for offset in range(0, 7):  # check up to 7 days ahead
        target_date = today + timedelta(days=offset)
        weekday_name = WEEKDAY_MAP[target_date.weekday()]  # e.g. "Tuesday"
        if user_type in ["student", "rep"]:
            lessons = Timetable.objects.filter(term=current_term, Class=user.Class, day__name=weekday_name)

            for t in lessons:
                lesson_start = timezone.make_aware(datetime.combine(target_date, t.lesson.start))
                lesson_end = timezone.make_aware(datetime.combine(target_date, t.lesson.end))

                # skip past lessons for today
                if offset == 0 and lesson_end <= now:
                    continue

                lessons_list.append({
                    "title": f"{t.lesson.name or 'Free'}",
                    "description": f"{t.unit.unit.abbr} by {t.unit.regno.get_full_name() if t.unit and t.unit.regno else 'TBA'}",
                    "start_datetime": lesson_start,
                    "end_datetime": lesson_end,
                    "event_type": "Lesson",
                    "location": str(t.classroom.name),
                })
        else:
            lessons = Timetable.objects.filter(term=current_term, unit__regno__regno=user_regno, day__name=weekday_name)

            for t in lessons:
                lesson_start = timezone.make_aware(datetime.combine(target_date, t.lesson.start))
                lesson_end = timezone.make_aware(datetime.combine(target_date, t.lesson.end))

                # skip past lessons for today
                if offset == 0 and lesson_end <= now:
                    continue

                lessons_list.append({
                    "title": f"{t.lesson.name or 'Free'}",
                    "description": f"{t.unit.unit.abbr} at {t.Class.name if t.Class else 'TBA'}",
                    "start_datetime": lesson_start,
                    "end_datetime": lesson_end,
                    "event_type": "Lesson",
                    "location": str(t.classroom.name),
                })
    # sort and take first 4
    lessons_list = sorted(lessons_list, key=lambda x: x["start_datetime"])[:4]

    # --- Merge events + lessons ---
    combined = sorted(
        chain(event_list, lessons_list), key=lambda x: x["start_datetime"]
    )

    return Response(combined)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_user_events(request):
    """
    Returns all events for the logged-in user (student, class rep, or staff).
    """
    user_regno = request.query_params.get("user_regno")
    user_groups = request.user.groups.values_list("name", flat=True)

    # --- Identify user type ---
    try:
        if any(g.lower().startswith("student") or "rep" in g.lower() for g in user_groups):
            student = Student.objects.get(regno=user_regno)
            user = Allocate_Student.objects.get(studentno=student)
        else:
            user = Staff.objects.get(regno=user_regno)
    except Student.DoesNotExist:
        return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
    except Allocate_Student.DoesNotExist:
        return Response({"detail": "Student allocation not found."}, status=status.HTTP_404_NOT_FOUND)
    except Staff.DoesNotExist:
        return Response({"detail": "Staff not found."}, status=status.HTTP_404_NOT_FOUND)

    # --- Collect Events ---
    events = Event.objects.none()

    if is_student_user(request.user) or is_rep_user(request.user):
        events |= Event.objects.filter(student=user.studentno)
        events |= Event.objects.filter(visibility="students")
        events |= Event.objects.filter(Class=user.Class)
        events |= Event.objects.filter(course=user.Class.course)
        events |= Event.objects.filter(branch=user.Class.branch)
        events |= Event.objects.filter(department=user.Class.course.department)
        if is_rep_user(request.user):
            events |= Event.objects.filter(visibility="classreps")

    elif is_staff_user(request.user) or is_tutor_user(request.user):  # staff
        events |= Event.objects.filter(visibility="staff")
        events |= Event.objects.filter(staff=user)
        events |= Event.objects.filter(department=user.department)
        events |= Event.objects.filter(branch=user.branch)
        if is_tutor_user(request.user):
            events |= Event.objects.filter(visibility="classtutors")

    # Always include branch + public events
    events |= Event.objects.filter(visibility="public")

    # --- Deduplicate + Order ---
    events = events.distinct().order_by("start_datetime")

    # --- Serialize ---
    event_list = [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "start_datetime": e.start_datetime,
            "end_datetime": e.end_datetime,
            "level": e.level,
            "location": str(e.location),
            "is_all_day": e.is_all_day,
        }
        for e in events
    ]

    return Response(event_list)

