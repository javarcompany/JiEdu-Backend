from rest_framework import filters, viewsets, status, permissions #type: ignore
from django.contrib.auth.models import Permission, Group #type: ignore
from rest_framework.generics import ListCreateAPIView #type: ignore
from rest_framework.views import APIView #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, permission_classes #type: ignore
from django.views.decorators.csrf import csrf_exempt #type: ignore
from django.apps import apps #type: ignore
from django.views.decorators.http import require_GET, require_POST #type: ignore
from django.http import JsonResponse #type: ignore
from rest_framework.pagination import PageNumberPagination #type: ignore

from collections import defaultdict #type: ignore
from django.db.models import Prefetch #type: ignore

from .models import *
from .serializers import *
from .filters import *
from .application import *

from Staff.models import Staff
from Students.models import Allocate_Student
from Core.models import Course, Department, Institution

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

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def day_choices(request):
    return Response([{'value': choice[0], 'label': choice[1]} for choice in DAYS_OPTIONS])

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def code_choices(request):
    return Response([{'value': choice[0], 'label': choice[1]} for choice in LESSON_CATEGORY])

class DayViewSet(viewsets.ModelViewSet):
    queryset = Days.objects.all().order_by('id')
    serializer_class = DaySerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination
    
    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)
    
class TableSetupViewSet(viewsets.ModelViewSet):
    queryset = TableSetup.objects.all().order_by('id')
    serializer_class = TableSetupSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        start = self.request.data.get('start')
        duration = self.request.data.get('duration')
        print(f"Duration: {duration}")
        duration = parse_duration_string(duration)
        start = datetime.strptime(start, "%H:%M").time()

        if start and duration:
            start = datetime.combine(date.today(), start)
            end = (start + duration).time()
            serializer.save(end=end)
        else:
            serializer.save()

class TableViewSet(viewsets.ModelViewSet):
    queryset = Timetable.objects.all().order_by('id')
    serializer_class = TimetableSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def available_lesson_slots(request):
    class_id = request.query_params.get('class_id')
    day = request.query_params.get('day')

    if not class_id or not day:
        return Response({"error": "Missing parameters"}, status=400)

    # All possible slots
    all_slots = TableSetup.objects.filter(code = "Lesson").values_list("id", flat=True)

    # Get current system term
    current_term = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)

    # Fetch slots already used by this class on this day
    used_slots = Timetable.objects.filter(
        Class=class_id, day=day, term = current_term
    ).values_list('lesson', flat=True)

    # Filter only available ones
    available_ids = [slot for slot in all_slots if slot not in used_slots]

    # Fetch full TableSetup objects for the available slots
    available_slots = TableSetup.objects.filter(id__in=available_ids)
    
    # Serialize the results
    serializer = TableSetupSerializer(available_slots, many=True)

    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def timetable_count(request):
    workload_count = StaffWorkload.objects.count()
    timetable_count = Timetable.objects.count()
    average_load = round(workload_count/timetable_count * 100, 2)
    
    return Response({"average_load": average_load, "workload_count": workload_count, "timetable_count": timetable_count})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_trainer_conflict(request):
    workload_id = request.query_params.get('workload_id')
    lesson_id = request.query_params.get('lesson_id')
    day = request.query_params.get('day')
    class_id = request.query_params.get('class_id')  # Optional, to ignore self

    if not workload_id or not lesson_id or not day:
        return Response({"error": "Missing parameters"}, status=400)
 
    try:
        workload = StaffWorkload.objects.select_related('regno').get(id=workload_id)
    except StaffWorkload.DoesNotExist:
        return Response({"error": "Workload not found"}, status=404)

    trainer = workload.regno
    class_object = Class.objects.get(id = class_id)

    # 1. Check Trainer Lesson Conflict
    conflict = Timetable.objects.filter(
        term = class_object.intake,
        day__id = day,
        lesson__id = lesson_id,
        unit__regno = trainer
    )
    if class_id:
        conflict = conflict.exclude(Class__id = class_id)  # Allow re-editing own class
    if conflict.exists():
        return Response({"conflict": True, "message": "Trainer is already scheduled for another class at this time."})
    
    # 2. Check Staff Hours
    assigned_lessons = Timetable.objects.filter(term = class_object.intake, unit__regno = trainer)
    totalHours = 0
    if assigned_lessons:
        for entry in assigned_lessons:
            duration = entry.lesson.duration  # assuming lesson is FK and duration is TimeField or timedelta
            if duration:
                try:
                    total_seconds = duration.hour * 3600 + duration.minute * 60 + duration.second
                except AttributeError:
                    total_seconds = duration.total_seconds()
                totalHours += total_seconds / 3600
    if totalHours >= trainer.weekly_hours:
        return Response({"conflict": True, "message": "Trainer has reached maximum lesson hours."})

    # 3. Check Unit Weekly Limit
    unit = workload.unit

    unit_lessons = Timetable.objects.filter(
        term = class_object.intake, 
        unit__unit=unit,
        Class = class_object
    )
    
    totalHours = 0
    if unit_lessons:
        for entry in unit_lessons:
            duration = entry.lesson.duration  # assuming lesson is FK and duration is TimeField or timedelta
            if duration:
                try:
                    total_seconds = duration.hour * 3600 + duration.minute * 60 + duration.second
                except AttributeError:
                    total_seconds = duration.total_seconds()
                totalHours += total_seconds / 3600
    if totalHours >= unit.weekly_hours:
        return Response({"conflict": True, "message": "Unit has exhausted its weekly lessons."})

    return Response({"conflict": False})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_classroom_conflict(request):
    classroom_id = request.query_params.get('classroom_id')
    day = request.query_params.get('day')
    lesson_id = request.query_params.get('lesson_id')
    class_id = request.query_params.get('class_id')  # Optional for updates

    if not classroom_id or not day or not lesson_id:
        return Response({"error": "Missing parameters"}, status=400)

    class_object = Class.objects.get(id = class_id)

    conflict = Timetable.objects.filter(
        term = class_object.intake,
        day__id = day,
        lesson__id = lesson_id,
        classroom__id = classroom_id
    )

    if class_id:
        conflict = conflict.exclude(Class_id=class_id)

    if conflict.exists():
        return Response({"conflict": True, "message": "Classroom is already in use at this time."})
    
    return Response({"conflict": False})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def allocate_timetable(request, class_id, day_id):
    classroom_id = request.data.get('classroom')
    lesson_id = request.data.get('lesson')
    workload_id = request.data.get('workload')

    class_object = Class.objects.get(id = class_id)

    if not all([lesson_id, workload_id, classroom_id, class_id, day_id]):
        return Response({"detail": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)
    
    currentTerm = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)

    currentTable = Timetable.objects.update_or_create(
        term = currentTerm,
        Class = class_object,
        day_id = day_id,
        lesson_id = lesson_id,
        unit_id = workload_id,
        classroom_id = classroom_id,
    )

    # Update Staffs Load State
    staff = currentTable.unit.regno
    staff.used_hours += 2
    load_ratio = staff.used_hours / staff.weekly_hours
    if load_ratio == 1:
        load_state = "Booked"
    elif load_ratio >= 0.7:
        load_state = "Above Optimum"
    elif load_ratio >= 0.45:
        load_state = "Average"
    else:
        load_state = "Available"

    staff.load_state = load_state
    staff.save()

    return Response({"conflict": False})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_lessons(request):
    now = timezone.localtime()
    current_time = now.time()
    current_day = now.strftime('%A')

    # print("Day: ",current_day, "Time: ", current_time)

    lessons = Timetable.objects.filter(
        day__name__iexact=current_day,
        lesson__start__lte=current_time,
        lesson__end__gte=current_time,
        term__name = Institution.objects.first().current_intake,
        term__year = Institution.objects.first().current_year
    ).select_related('Class', 'unit__unit', 'unit__regno')

    data = []
    for entry in lessons:
        if entry.unit:
            data.append({
                "id": entry.id,
                "class_name": entry.Class.name,
                "unit": f"{entry.unit.unit.uncode}-{entry.unit.unit.abbr}",
                "lecturer": f"{entry.unit.regno.fname} {entry.unit.regno.sname}",
                "classroom": entry.classroom.name
            })

    return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def staff_timetable(request):
    staff_id = request.query_params.get("staff_id")
    term_id = request.query_params.get("term_id")
    if (not staff_id) or (staff_id == "0") or (staff_id == ""):
        staff_id = Staff.objects.first().id
    
    if (not term_id) or (term_id == "0") or (term_id == ""):
        term_id = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).id

    lessons = TableSetup.objects.filter(code="Lesson").order_by('start')  # Sorted by time
    days = Days.objects.order_by('id')
    timetable_entries = Timetable.objects.filter(unit__regno__id = staff_id, term__id = term_id).select_related('day', 'lesson', 'Class', 'unit', 'classroom')
    serializer = TimetableSerializer(timetable_entries, many=True)
    data = {
        "lessons": [{"id": l.id, "name": l.name, "start": l.start, "end": l.end} for l in lessons],
        "days": [{"id": d.id, "name": d.name}for d in days],
        "timetable": serializer.data
    }
    # print(data)
    return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def student_timetable(request, id):
    class_id = Allocate_Student.objects.get(studentno__id = id).Class.id
    # print("Class ID:  ", class_id)
    lessons = TableSetup.objects.filter(code="Lesson").order_by('start')  # Sorted by time
    days = Days.objects.order_by('id')
    timetable_entries = Timetable.objects.filter(Class__id = class_id, term = Class.objects.get(id = class_id).intake).select_related('day', 'lesson', 'unit', 'classroom')
    serializer = TimetableSerializer(timetable_entries, many=True)
    data = {
        "lessons": [{"id": l.id, "name": l.name, "start": l.start, "end": l.end} for l in lessons],
        "days": [{"id": d.id, "name": d.name}for d in days],
        "timetable": serializer.data
    }
    # print(data)
    return Response(data)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def institution_timetable(request):
    term_id = request.query_params.get("term_id")
    if (not term_id) or (term_id == "0") or (term_id == ""):
        term_id = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).id

    lessons = TableSetup.objects.filter(code="Lesson").order_by('start')  # Sorted by time
    days = Days.objects.order_by('id')
    classes = Class.objects.filter(state = "Active").order_by("name")
    timetable_entries = Timetable.objects.filter(term__id = term_id).select_related('day', 'lesson', 'unit', 'classroom', "Class")
    serializer = TimetableSerializer(timetable_entries, many=True)
    data = {
        "lessons": [{"id": l.id, "name": l.name, "start": l.start, "end": l.end} for l in lessons],
        "days": [{"id": d.id, "name": d.name}for d in days],
        "classes": [{"id": cls.id, "name": cls.name} for cls in classes],
        "timetable": serializer.data
    }
    
    return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def class_timetable(request):
    class_id = request.query_params.get("class_id")
    if (not class_id) or (class_id == "0"):
        class_id = Class.objects.first().id

    lessons = TableSetup.objects.filter(code="Lesson").order_by('start')  # Sorted by time
    days = Days.objects.order_by('id')
    timetable_entries = Timetable.objects.filter(Class__id = class_id, term = Class.objects.get(id = class_id).intake).select_related('day', 'lesson', 'unit', 'classroom')
    serializer = TimetableSerializer(timetable_entries, many=True)
    data = {
        "lessons": [{"id": l.id, "name": l.name, "start": l.start, "end": l.end} for l in lessons],
        "days": [{"id": d.id, "name": d.name}for d in days],
        "timetable": serializer.data
    }
    # print(data)
    return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def department_timetable(request):
    department_id = request.query_params.get("department_id")
    term_id = request.query_params.get("term_id")
    if (not department_id) or (department_id == "0") or (department_id == ""):
        department_id = Department.objects.first().id
    
    if (not term_id) or (term_id == "0") or (term_id == ""):
        term_id = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).id

    lessons = TableSetup.objects.filter(code="Lesson").order_by('start')  # Sorted by time
    days = Days.objects.order_by('id')
    classes = Class.objects.filter(course__department__id = department_id).order_by("name")
    timetable_entries = Timetable.objects.filter(Class__course__department__id = department_id, term__id = term_id).select_related('day', 'lesson', 'unit', 'classroom', "Class")
    serializer = TimetableSerializer(timetable_entries, many=True)
    data = {
        "lessons": [{"id": l.id, "name": l.name, "start": l.start, "end": l.end} for l in lessons],
        "days": [{"id": d.id, "name": d.name}for d in days],
        "classes": [{"id": cls.id, "name": cls.name} for cls in classes],
        "timetable": serializer.data
    }
    
    return Response(data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_timetable(request):
    classroom_id = request.query_params.get('classroom_id')
    table_id = request.query_params.get('table_id')
    day_id = request.query_params.get('day_id')
    time_id = request.query_params.get('time_id')

    if not all([table_id, time_id, classroom_id, day_id]):
        return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        timetable = Timetable.objects.get(id=table_id)

        # Check whether the lecturer is already assigned for that day/lesson or not
        conflict = Timetable.objects.filter(
                                day__id = day_id, lesson__id = time_id, 
                                unit__regno = timetable.unit.regno, 
                                term = timetable.term).exclude(id=timetable.id)
        if conflict.exists():
            return Response({"error": f"{timetable.unit.regno.get_name_reg()} is already assigned for another class on {Days.objects.get(id = day_id).name} {TableSetup.objects.get(id = time_id).name}"})
        
        timetable.day_id = day_id
        timetable.lesson_id = time_id
        timetable.classroom_id = classroom_id
        timetable.save()

    except Timetable.DoesNotExist:
        return Response({"error": "Timetable not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        "success": f"{timetable.Class.name} - {timetable.unit.unit} has been modified successfully."
    })

