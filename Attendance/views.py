from rest_framework import filters, viewsets, status, permissions #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, permission_classes, action #type: ignore
from django.views.decorators.csrf import csrf_exempt #type: ignore
from rest_framework.pagination import PageNumberPagination #type: ignore
from django.db.models import Sum, Count, Q, F, Func #type: ignore
from datetime import datetime
from collections import defaultdict

from .models import *
from .serializers import *
from .filters import *
from .application import *

from Students.models import Allocate_Student
from Timetable.models import TableSetup, Days
from Core.models import Institution, Term, Unit
from Students.serializers import StudentAllocationSerializer

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

class StudentRegisterViewSet(viewsets.ModelViewSet):
    queryset = StudentRegister.objects.all().order_by("-id")
    serializer_class = StudentRegisterSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [ExtendedMultiKeywordSearchFilter]

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

@api_view(["GET"])
def student_attendance_percentages(request):
    students = Student.objects.all()

    results = []

    for entry in students:
        registers = StudentRegister.objects.filter(student=entry).select_related('lesson')
        
        total_lessons = registers.count()
        if total_lessons == 0:
            continue

        total_value = 0

        for reg in registers:
            lesson = reg.lesson.lesson
            if not lesson.start or not lesson.duration or not reg.tor:
                continue

            # Convert lesson duration to seconds
            duration_seconds = lesson.duration.total_seconds()

            # Calculate delay in seconds
            scheduled_datetime = datetime.combine(reg.dor, lesson.start)
            actual_arrival = datetime.combine(reg.dor, reg.tor)

            delay_seconds = max((actual_arrival - scheduled_datetime).total_seconds(), 0)

            # Compute attendance value
            value = 0 if delay_seconds >= duration_seconds else 100 - (delay_seconds * 100 / duration_seconds)
            
            total_value += value

        avg_attendance = round(total_value / total_lessons, 2)


        results.append({
            "id": entry.id,
            "student_passport": entry.passport.url if entry.passport else None,
            "student_regno": entry.regno,
            "student_fname": entry.fname,
            "student_mname": entry.mname or '',
            "student_sname": entry.sname,
            "percentage": avg_attendance,
        })

    return Response(results)

class AttendanceModeViewSet(viewsets.ModelViewSet):
    queryset = AttendanceModes.objects.all().order_by("id")
    serializer_class = AttendanceModesrSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [ExtendedMultiKeywordSearchFilter]

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)
    
@api_view(['GET'])
def check_current_lesson(request):
    class_id = request.GET.get("class_id")
    # a) Class
    classObject = Class.objects.get(id = class_id)

    # b) Day
    today = Days.objects.filter(name = str(datetime.today().strftime('%A'))).first()

    if not today:
        return Response({"error": "Today there are NO Lessons..."}, status=400)
    
    # c) Lesson
    current_time = datetime.now().time()
    all_lessons = TableSetup.objects.filter(code="Lesson")
    matched_lesson = None
    if all_lessons:
        for lesson in all_lessons:
            print("Start Time: ", lesson.start, " End Time: ", lesson.end, "  Current Time:", current_time)
            if lesson.start <= current_time <= lesson.end:
                matched_lesson = lesson
                break

    if not matched_lesson:     
        return Response({"error": "Ooops, There is no lesson this time of the day...."})
    
    # Get current system term
    currentTerm = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)

    lesson = Timetable.objects.filter(
        term = currentTerm,
        Class = classObject,
        day = today,
        lesson = matched_lesson,
    ).first()

    if lesson:
        return Response({"has_lesson": True, "lesson_id": lesson.id})
    
    return Response({"has_lesson": False, "error": f"{classObject.name} has no lesson at this time of the day.."})

@api_view(["GET"])
def search_student_attendance(request):
    class_id = request.query_params.get('class_id')
    # Initial Load
    if class_id == "":
        students = Allocate_Student.objects.all()
        return Response(StudentAllocationSerializer(students, many=True).data)
    
    # Search Attendance
    # 1. Get objects
    # a) Class
    classObject = Class.objects.get(id = class_id)

    # b) Day
    today = Days.objects.filter(name = str(datetime.today().strftime('%A'))).first()
    todate = datetime.today().date()
    if not today:
        return Response({"error": "Today there are NO Lessons..."}, status=400)
    
    # c) Lesson
    current_time = datetime.now().time()
    currentLesson = TableSetup.objects.filter(code="Lesson")
    if currentLesson:
        for lesson in currentLesson:
            if lesson.start <= current_time <= lesson.end:
                currentLesson = lesson
                break
            
    if not currentLesson:     
        return Response({"error": "Ooops, There is no lesson this time of the day...."})
    
    # Get current system term
    currentTerm = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)
    
    existing_attendance = StudentRegister.objects.filter(
        lesson__term = currentTerm,
        lesson__Class=classObject,
        lesson__lesson=currentLesson,
        lesson__day = today,
        dor=todate
    )

    if existing_attendance:
        return Response(StudentRegisterSerializer(existing_attendance, many=True).data)
    else:
        allocated_students = Allocate_Student.objects.filter(Class=classObject)
        return Response(StudentAllocationSerializer(allocated_students, many=True).data)

@api_view(["POST"])
def mark_attendance(request):
    data = request.data
    attendance_data = data.get("attendance", {})
    mode_id = data.get("mode_id")
    lesson_id = data.get("lesson_id")

    # Basic validation
    if not mode_id or not lesson_id:
        return Response({"error": "Missing mode, or lesson."}, status=status.HTTP_400_BAD_REQUEST)
 
    try:
        mode_obj = AttendanceModes.objects.get(id = mode_id)
        lesson_obj = Timetable.objects.get(id = lesson_id)
    except (AttendanceModes.DoesNotExist, Timetable.DoesNotExist) as e:
        return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    # Track errors and successes
    errors = []
    saved = 0

    for regno, state in attendance_data.items():
        
        if state == "Allocated":
            state = "Absent"
        try:
            student = Student.objects.get(regno=regno)

            # Create or update attendance
            attn, created = StudentRegister.objects.update_or_create(
                student = student,
                lesson = lesson_obj,
                dor = datetime.today().date(),
                defaults={
                    "state": state,
                    "tor": datetime.now().time()
                }
            )
            saved += 1
        except Student.DoesNotExist:
            errors.append(f"Student {regno} not found in class.")
        except Exception as e:
            errors.append(str(e))

    if errors:
        return Response({"error": errors}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "success": f"Attendance marked for {saved} student(s).",
    }, status=status.HTTP_200_OK)

@api_view(["GET"])
def get_student_analysis(request):
    student_id = request.query_params.get('student_id')
    
    # Validate and retrieve student
    try:
        if not student_id:
            currentStudent = Student.objects.first()  # fallback
        else:
            currentStudent = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)

    try:
        studentsClass = Allocate_Student.objects.get(studentno=currentStudent)
    except Allocate_Student.DoesNotExist:
        return Response({"error": "Student class allocation not found"}, status=404)

    # Get start and end dates
    startDay = studentsClass.Class.intake.openingDate.date()
    endDay = datetime.today().date()

    # Calculate all weekdays between startDay and endDay
    total_days = (endDay - startDay).days + 1
    all_weekdays = [
        (startDay + timedelta(days=i))
        for i in range(total_days)
        if (startDay + timedelta(days=i)).weekday() < 5  # Weekdays only (0-4 = Mon-Fri)
    ]

    # Get attendance records in date range
    present = StudentRegister.objects.filter(
        student=currentStudent,
        state="Present",
        dor__range=(startDay, endDay)
    ).count()

    absent = StudentRegister.objects.filter(
        student=currentStudent,
        state="Absent",
        dor__range=(startDay, endDay)
    ).count()

    late = StudentRegister.objects.filter(
        student=currentStudent,
        state="Late",
        dor__range=(startDay, endDay)
    ).count()

    total_marked = present + absent + late
    total_expected = len(all_weekdays)
    unmarked = total_expected - total_marked if total_expected > total_marked else 0

    # Calculate percentages
    def percentage(count):
        return round((count / total_expected) * 100, 2) if total_expected > 0 else 0

    data = {
        "student": currentStudent.get_full_name(),
        "from": startDay,
        "to": endDay,
        "expected_days": total_expected,
        "marked_days": total_marked,
        "present": present,
        "present_percentage": percentage(present),
        "absent": absent,
        "absent_percentage": percentage(absent),
        "late": late,
        "late_percentage": percentage(late),
        "unmarked": unmarked,
        "unmarked_percentage": percentage(unmarked),
    }

    return Response(data)

@api_view(["GET"])
def get_student_unit_analysis(request):
    student_id = request.query_params.get('student_id')
    
    # Validate and retrieve student
    try:
        if not student_id:
            currentStudent = Student.objects.first()  # fallback
        else:
            currentStudent = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)

    try:
        studentClass = Allocate_Student.objects.get(studentno=currentStudent)
    except Allocate_Student.DoesNotExist:
        return Response({"error": "Student class allocation not found"}, status=404)

    student_class = studentClass.Class
    timetables = Timetable.objects.filter(Class=student_class)
    if not timetables:
        return Response({"error": "Student's class is missing timetable"}, status=404)

    # Get unique units
    units = Unit.objects.filter(id__in=timetables.values_list("unit__unit", flat=True).distinct())

    # Prepare response data
    result = []
    if units:
        for unit in units:
            # Get all attendance records for this student for this unit
            unit_attendance = StudentRegister.objects.filter(student=currentStudent, lesson__unit__unit=unit)

            total = unit_attendance.count()
            if total == 0:
                present_pct = late_pct = absent_pct = 0
            else:
                present_pct = round(unit_attendance.filter(state="Present").count() / total * 100, 2)
                late_pct = round(unit_attendance.filter(state="Late").count() / total * 100, 2)
                absent_pct = round(unit_attendance.filter(state="Absent").count() / total * 100, 2)

            result.append({
                "id": unit.id,
                "abbr": unit.abbr,
                "uncode": unit.uncode,
                "present": f"{present_pct}%",
                "late": f"{late_pct}%",
                "absent": f"{absent_pct}%"
            })
    else:
        units = Unit.objects.filter(course = student_class.course, module = student_class.module)
        for unit in units:
            result.append({
                "id": unit.id,
                "abbr": unit.abbr,
                "uncode": unit.uncode,
                "present": "0%",
                "late": "0%",
                "absent": "0%"
            })
    
    return Response(result)

@api_view(["GET"])
def get_student_lesson_analysis(request):
    student_id = request.query_params.get('student_id')

    try:
        currentStudent = Student.objects.get(id=student_id) if student_id else Student.objects.first()
    except Student.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)

    try:
        studentClass = Allocate_Student.objects.get(studentno=currentStudent).Class
    except Allocate_Student.DoesNotExist:
        return Response({"error": "Student class allocation not found"}, status=404)

    institution = Institution.objects.first()
    try:
        current_term = Term.objects.get(name=institution.current_intake, year=institution.current_year)
    except Term.DoesNotExist:
        return Response({"error": "There is no current term set..."}, status=400)

    startDay = current_term.openingDate.date()
    endDay = datetime.today().date()

    this_term_timetable = Timetable.objects.filter(term=current_term, Class=studentClass)
    if not this_term_timetable.exists():
        return Response({"error": "There is no timetable for this student."}, status=404)

    timetable_by_day = {}
    for t in this_term_timetable:
        weekday = t.day.name.lower()
        timetable_by_day.setdefault(weekday, []).append(t)

    lessons = []
    reg_values = []

    for i in range((endDay - startDay).days + 1):
        current_date = startDay + timedelta(days=i)
        weekday = get_weekday(current_date.weekday()).lower()
        daily_timetables = timetable_by_day.get(weekday, [])

        if not daily_timetables:
            continue  # No lessons this day

        register = 0
        lesson_count = 0

        for lesson in daily_timetables:
            lesson_count += 1
            attendance = StudentRegister.objects.filter(
                student=currentStudent,
                lesson=lesson,
                dor=current_date
            ).first()

            if attendance:
                if attendance.state == "Present":
                    register += 100
                elif attendance.state == "Late":
                    register += 50
                # Absent = 0, implicit
            # Else: treat as unmarked (register += 0)

        avg_register = register / lesson_count if lesson_count > 0 else 0
        lessons.append(current_date.strftime("%m-%d"))
        reg_values.append(round(avg_register,1))

    return Response({
        "lessons": lessons,
        "reg_values": reg_values
    })

@api_view(["GET"])
def student_weekly_attendance_trend(request):
    student_id = request.query_params.get('student_id')

    # Validate and retrieve student
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)

    try:
        student_class = Allocate_Student.objects.get(studentno=student).Class
    except Allocate_Student.DoesNotExist:
        return Response({"error": "Class allocation not found"}, status=404)

    # Get current term
    institution = Institution.objects.first()
    try:
        term = Term.objects.get(name=institution.current_intake, year=institution.current_year)
    except Term.DoesNotExist:
        return Response({"error": "Current term not set"}, status=404)

    start_date = term.openingDate.date()
    end_date = datetime.today().date()

    # Fetch timetable for the class and term
    timetable = Timetable.objects.filter(Class=student_class, term=term)
    if not timetable.exists():
        return Response({"error": "No timetable for this class in the current term"}, status=404)

    total_days = (end_date - start_date).days + 1
    daily_timetable_by_weekday = defaultdict(list)
    for lesson in timetable:
        daily_timetable_by_weekday[lesson.day.name.lower()].append(lesson)

    # Weekly counters
    week_data = defaultdict(lambda: {"present": 0, "late": 0, "absent": 0})
    
    for i in range(total_days):
        current_date = start_date + timedelta(days=i)
        weekday_name = get_weekday(current_date.weekday()).lower()
        week_number = ((current_date - start_date).days // 7) + 1

        lessons_today = daily_timetable_by_weekday.get(weekday_name, [])
        for lesson in lessons_today:
            attendance = StudentRegister.objects.filter(student=student, lesson=lesson, dor=current_date).first()
            if attendance:
                state = attendance.state.lower()
                if state in week_data[week_number]:
                    week_data[week_number][state] += 1
                else:
                    week_data[week_number]["absent"] += 1  # fallback
            else:
                week_data[week_number]["absent"] += 1  # not marked = absent

    # Format for chart
    week_labels = [f"Week {i}" for i in sorted(week_data.keys())]
    present_counts = [week_data[i]["present"] for i in sorted(week_data.keys())]
    late_counts = [week_data[i]["late"] for i in sorted(week_data.keys())]
    absent_counts = [week_data[i]["absent"] for i in sorted(week_data.keys())]

    return Response({
        "weeks": week_labels,
        "present": present_counts,
        "late": late_counts,
        "absent": absent_counts,
    })

@api_view(["GET"])
def get_student_module_summary_report(request):
    student_id = request.query_params.get("student_id")

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)

    try:
        student_class_alloc = Allocate_Student.objects.get(studentno=student)
        student_class = student_class_alloc.Class
        current_module = student_class.module.id  # e.g., 1 for Module One
    except Allocate_Student.DoesNotExist:
        return Response({"error": "Student class not found"}, status=404)

    try:
        inst = Institution.objects.first()
        current_term = Term.objects.get(name=inst.current_intake, year=inst.current_year)
    except Term.DoesNotExist:
        return Response({"error": "Current term not set"}, status=404)

    # Fetch attendance records for student's class in current or past modules
    attendance_qs = StudentRegister.objects.filter(
        student=student,
        lesson__term=current_term,
    ).select_related("lesson__unit", "lesson__Class__module")

    # Group by module
    module_summary = defaultdict(lambda: {"present": 0, "absent": 0, "late": 0})

    for record in attendance_qs:
        module = record.lesson.Class.module
        if module.id <= current_module:
            key = f"{module.name}"  # e.g., "Module One"
            if record.state == "Present":
                module_summary[key]["present"] += 1
            elif record.state == "Late":
                module_summary[key]["late"] += 1
            elif record.state == "Absent":
                module_summary[key]["absent"] += 1

    # Convert to list
    results = []
    for module_name, stats in module_summary.items():
        results.append({
            "module": f"Module {module_name}",
            "present": stats["present"],
            "late": stats["late"],
            "absent": stats["absent"]
        })

    print(results)

    return Response(results)

@api_view(["GET"])
def get_student_weekday_attendance_report(request):
    student_id = request.query_params.get("student_id")

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)

    try:
        studentClass = Allocate_Student.objects.get(studentno=student).Class
    except Allocate_Student.DoesNotExist:
        return Response({"error": "Student class allocation not found"}, status=404)

    try:
        inst = Institution.objects.first()
        current_term = Term.objects.get(name=inst.current_intake, year=inst.current_year)
    except Term.DoesNotExist:
        return Response({"error": "Current term not set"}, status=404)
    
    # Get active school days dynamically
    active_days = Days.objects.all().values_list("name", flat=True)
    weekday_data = {day[0:3]: {"present": 0, "late": 0, "absent": 0, "unmarked":0} for day in active_days}

    startDay = current_term.openingDate.date()
    endDay = datetime.today().date()

    this_term_timetable = Timetable.objects.filter(term=current_term, Class=studentClass)
    if not this_term_timetable.exists():
        return Response({"error": "There is no timetable for this student."}, status=404)

    timetable_by_day = {}
    for t in this_term_timetable:
        weekday = t.day.name[0:3]
        timetable_by_day.setdefault(weekday, []).append(t)

    for i in range((endDay - startDay).days + 1):
        current_date = startDay + timedelta(days=i)
        weekday = get_weekday(current_date.weekday())[0:3]
        daily_timetables = timetable_by_day.get(weekday, [])

        if not daily_timetables:
            continue  # No lessons this day

        for lesson in daily_timetables:
            attendance = StudentRegister.objects.filter(
                student=student,
                lesson=lesson,
                dor=current_date
            ).first()

            if attendance:
                if attendance.state == "Present":
                    weekday_data[weekday]["present"] += 1
                elif attendance.state == "Late":
                    weekday_data[weekday]["late"] += 1
                elif attendance.state == "Absent":
                    weekday_data[weekday]["absent"] += 1
            else:
                weekday_data[weekday]["unmarked"] += 1

    return Response(weekday_data)
 
@api_view(["GET"])
def get_class_attendance_summary(request):
    class_id = request.query_params.get("class_id")

    if not class_id:
        return Response({"error": "Missing class_id parameter"}, status=400)

    try:
        klass = Class.objects.get(id=class_id)
    except Class.DoesNotExist:
        return Response({"error": "Class not found"}, status=404)

    try:
        inst = Institution.objects.first()
        current_term = Term.objects.get(name=inst.current_intake, year=inst.current_year)
    except Term.DoesNotExist:
        return Response({"error": "Current term not set"}, status=404)

    students = Allocate_Student.objects.filter(Class=klass)
    report = []

    for student in students:
        total = StudentRegister.objects.filter(
            student=student.studentno, 
            lesson__term=current_term
        ).count()

        present = StudentRegister.objects.filter(
            student=student.studentno,
            lesson__term=current_term,
            state="Present"
        ).count()

        late = StudentRegister.objects.filter(
            student=student.studentno,
            lesson__term=current_term,
            state="Late"
        ).count()

        absent = StudentRegister.objects.filter(
            student=student.studentno,
            lesson__term=current_term,
            state="Absent"
        ).count()

        report.append({
            "id": student.studentno.id,
            "name": f"{student.studentno.fname} {student.studentno.mname} {student.studentno.sname}",
            "regno": student.studentno.regno,
            "passport": student.studentno.passport.url,
            "present": present,
            "late": late,
            "absent": absent,
            "present_rate": round((present / total) * 100, 1) if total > 0 else 0.0,
            "late_rate": round((late / total) * 100, 1) if total > 0 else 0.0,
            "absent_rate": round((absent / total) * 100, 1) if total > 0 else 0.0,
        })

    return Response(report)

@api_view(["GET"])
def get_top3_attendance_report(request):
    class_id = request.query_params.get("class_id")

    if not class_id:
        return Response({"error": "class_id is required"}, status=400)

    try:
        institution = Institution.objects.first()
        current_term = Term.objects.get(name=institution.current_intake, year=institution.current_year)
    except Term.DoesNotExist:
        return Response({"error": "Current term not set"}, status=404)

    # Get students allocated to this class
    allocated_students = Allocate_Student.objects.filter(Class_id=class_id).select_related("studentno")
    student_ids = [alloc.studentno.id for alloc in allocated_students]

    attendance_qs = StudentRegister.objects.filter(
        student_id__in=student_ids,
        lesson__term=current_term
    ).select_related("student")

    # Group counts by student and state
    attendance_counter = defaultdict(lambda: {"name": "", "present": 0, "late": 0, "absent": 0})

    for entry in attendance_qs:
        student = entry.student
        if not attendance_counter[student.id]["name"]:
            attendance_counter[student.id]["name"] = f"{student.fname} {student.mname} {student.sname}"
        if entry.state == "Present":
            attendance_counter[student.id]["present"] += 1
        elif entry.state == "Late":
            attendance_counter[student.id]["late"] += 1
        elif entry.state == "Absent":
            attendance_counter[student.id]["absent"] += 1

    # Sort for each state and get top 3
    sorted_by_present = sorted(attendance_counter.values(), key=lambda x: x["present"], reverse=True)[:3]
    sorted_by_late = sorted(attendance_counter.values(), key=lambda x: x["late"], reverse=True)[:3]
    sorted_by_absent = sorted(attendance_counter.values(), key=lambda x: x["absent"], reverse=True)[:3]

    return Response({
        "top_present": sorted_by_present,
        "top_late": sorted_by_late,
        "top_absent": sorted_by_absent,
    })

@api_view(["GET"])
def class_weekday_attendance_summary(request):
    class_id = request.query_params.get("class_id")

    try:
        class_obj = Class.objects.get(id=class_id)
    except (Institution.DoesNotExist, Term.DoesNotExist, Class.DoesNotExist):
        return Response({"error": "Invalid class or term settings"}, status=404)

    # Fetch all days configured in your system
    operational_days = Days.objects.all().order_by("id")  # assume there's an `order` field to sort days correctly

    # Get attendance records for the current term and class
    attendance_records = StudentRegister.objects.filter(
        lesson__Class=class_obj,
    ).select_related("lesson", "lesson__day")

    summary = defaultdict(lambda: {"Present": 0, "Late": 0, "Absent": 0})

    for record in attendance_records:
        day_name = record.lesson.day.name
        summary[day_name][record.state] += 1

    # Respect the actual order and existence of operational days
    response_data = {
        day.name[0:3]: summary[day.name]
        for day in operational_days
    }
    
    return Response(response_data)

@api_view(["GET"])
def class_unit_attendance_summary(request):
    class_id = request.query_params.get("class_id")
    if not class_id:
        return Response({"error": "Missing class_id"}, status=400)

    try:
        class_obj = Class.objects.get(id=class_id)
    except Class.DoesNotExist:
        return Response({"error": "Invalid class ID"}, status=404)

    # Get all timetables for this class
    timetables = Timetable.objects.filter(Class=class_obj)
    if not timetables.exists():
        return Response({"error": "This class has no timetable"}, status=404)
    
    # Units that have scheduled lessons
    unit_ids = timetables.values_list("unit__unit", flat=True).distinct()
    units = Unit.objects.filter(id__in=unit_ids)

    result = []
    for unit in units:
        unit_attendance = StudentRegister.objects.filter(
            lesson__Class=class_obj,
            lesson__unit__unit=unit
        )

        total = unit_attendance.count()
        present_pct = late_pct = absent_pct = 0

        if total > 0:
            present_pct = round(unit_attendance.filter(state="Present").count() / total * 100, 2)
            late_pct = round(unit_attendance.filter(state="Late").count() / total * 100, 2)
            absent_pct = round(unit_attendance.filter(state="Absent").count() / total * 100, 2)

        result.append({
            "id": unit.id,
            "abbr": unit.abbr,
            "uncode": unit.uncode,
            "present": f"{present_pct}%",
            "late": f"{late_pct}%",
            "absent": f"{absent_pct}%"
        })

    return Response(result)

@api_view(["GET"])
def course_attendance_summary(request):
    course_id = request.query_params.get("course_id")

    if not course_id:
        return Response({"error": "Missing course_id parameter"}, status=400)

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=404)

    try:
        inst = Institution.objects.first()
        current_term = Term.objects.get(name=inst.current_intake, year=inst.current_year)
    except Term.DoesNotExist:
        return Response({"error": "Current term not set"}, status=404)

    report = []

    classes = Class.objects.filter(course = course).order_by("name")

    for klass in classes:
        total = StudentRegister.objects.filter(
            lesson__term=current_term,
            lesson__Class = klass
        ).count()

        present = StudentRegister.objects.filter(
            lesson__term=current_term,
            lesson__Class = klass,
            state="Present"
        ).count()

        late = StudentRegister.objects.filter(
            lesson__Class = klass,
            lesson__term=current_term,
            state="Late"
        ).count()

        absent = StudentRegister.objects.filter(
            lesson__Class = klass,
            lesson__term=current_term,
            state="Absent"
        ).count()

        report.append({
            "id": klass.id,
            "name": f"{klass.name} [{klass.intake}]",
            "present": present,
            "term": klass.intake.id,
            "late": late,
            "absent": absent,
            "present_rate": round((present / total) * 100, 1) if total > 0 else 0.0,
            "late_rate": round((late / total) * 100, 1) if total > 0 else 0.0,
            "absent_rate": round((absent / total) * 100, 1) if total > 0 else 0.0,
        })

    return Response(report)

@api_view(["GET"])
def course_unit_attendance_summary(request):
    course_id = request.query_params.get("course_id")
    if not course_id:
        return Response({"error": "course_id is required"}, status=400)

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=404)

    # Get all class IDs in this course
    class_ids = course.class_set.values_list("id", flat=True)

    # Get all timetable IDs linked to these classes
    timetable_ids = Timetable.objects.filter(Class__id__in=class_ids).values_list("id", flat=True)

    # Aggregate attendance data per unit
    attendance = (
        StudentRegister.objects
        .filter(lesson__id__in=timetable_ids)
        .values(unit_id=F("lesson__unit__unit__id"), abbr=F("lesson__unit__unit__abbr"), uncode=F("lesson__unit__unit__uncode"))
        .annotate(
            total=Count("id"),
            present=Count("id", filter=Q(state="Present")),
            late=Count("id", filter=Q(state="Late")),
            absent=Count("id", filter=Q(state="Absent")),
        )
        .annotate(
            present_pct=Func(100.0 * F("present") / F("total"), function="ROUND", template="ROUND(%(expressions)s, 2)"),
            late_pct=Func(100.0 * F("late") / F("total"), function="ROUND", template="ROUND(%(expressions)s, 2)"),
            absent_pct=Func(100.0 * F("absent") / F("total"), function="ROUND", template="ROUND(%(expressions)s, 2)"),
        )
        .order_by("abbr")
    )

    return Response(attendance)

@api_view(["GET"])
def course_weekday_attendance_summary(request):
    course_id = request.query_params.get("course_id")

    if not course_id:
        return Response({"error": "course_id is required"}, status=400)

    try:
        course_obj = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Invalid course ID"}, status=404)

    # Get all class IDs for this course
    class_ids = Class.objects.filter(course=course_obj).values_list("id", flat=True)

    # All configured weekdays, in order
    operational_days = Days.objects.all().order_by("id")  # assumes Day model has a name (e.g. Monday)

    # Attendance records across all classes in the course
    attendance_records = StudentRegister.objects.filter(
        lesson__Class_id__in=class_ids
    ).select_related("lesson", "lesson__day")

    # Group by day name
    summary = defaultdict(lambda: {"Present": 0, "Late": 0, "Absent": 0})

    for record in attendance_records:
        day_name = record.lesson.day.name
        summary[day_name][record.state] += 1

    # Build response with fixed weekday keys (Mon, Tue, etc.)
    response_data = {
        day.name[0:3]: summary[day.name]
        for day in operational_days
    }

    return Response(response_data)

@api_view(["GET"])
def course_class_average_weekday_attendance(request):
    course_id = request.query_params.get("course_id")

    if not course_id:
        return Response({"error": "course_id is required"}, status=400)

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=404)

    class_objs = Class.objects.filter(course=course)
    operational_days = Days.objects.all().order_by("id")

    attendance_records = StudentRegister.objects.filter(
        lesson__Class__in=class_objs
    ).select_related("lesson", "lesson__Class", "lesson__day")

    # {(day, class_name): {Present, Late, Absent, count}}
    summary = defaultdict(lambda: {"Present": 0, "Late": 0, "Absent": 0, "count": 0})

    for record in attendance_records:
        class_name = record.lesson.Class.name
        day_name = record.lesson.day.name[0:3]
        summary[(day_name, class_name)][record.state] += 1
        summary[(day_name, class_name)]["count"] += 1

    # Build full matrix of all combinations (even if zero)
    result = []
    for cls in class_objs:
        for day in operational_days:
            key = (day.name[0:3], cls.name)
            stats = summary.get(key, {"Present": 0, "Late": 0, "Absent": 0, "count": 0})
            count = stats["count"] or 1
            result.append({
                "day": key[0],
                "class_name": key[1],
                "Present": round(stats["Present"] / count * 100, 2),
                "Late": round(stats["Late"] / count * 100, 2),
                "Absent": round(stats["Absent"] / count * 100, 2),
            })

    return Response(result)

@api_view(["GET"])
def course_unit_attendance_breakdown(request):
    course_id = request.query_params.get("course_id")

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Invalid course ID"}, status=404)

    units = Unit.objects.filter(course=course).distinct()
    classes = Class.objects.filter(course=course).distinct()

    result = []
    for unit in units:
        class_data = []

        for cls in classes:
            registers = StudentRegister.objects.filter(
                lesson__unit__unit=unit,
                lesson__Class=cls
            )
            total = registers.count()
            summary = defaultdict(int)

            for record in registers:
                summary[record.state] += 1

            def get_percent(count):
                return round((count / total) * 100, 2) if total else 0.0

            if total > 0:
                class_data.append({
                    "class_name": cls.name,
                    "Present": get_percent(summary["Present"]),
                    "Late": get_percent(summary["Late"]),
                    "Absent": get_percent(summary["Absent"]),
                })

        if class_data:
            result.append({
                "unit_abbr": unit.abbr,
                "classes": class_data
            })

    return Response(result)

@api_view(["GET"])
def course_attendance_overview(request):
    course_id = request.query_params.get("course_id")

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response({"error": "Invalid course ID"}, status=404)

    classes = Class.objects.filter(course=course)
    class_ids = classes.values_list("id", flat=True)

    students = Allocate_Student.objects.filter(Class__in=class_ids).distinct()

    lessons = StudentRegister.objects.filter(lesson__Class__in=class_ids)
    total_lessons = lessons.values("lesson_id").distinct().count()

    total_attendance = lessons.count()
    present_count = lessons.filter(state="Present").count()
    late_count = lessons.filter(state="Late").count()
    absent_count = lessons.filter(state="Absent").count()

    def get_avg(count):
        return round((count / total_attendance) * 100, 2) if total_attendance else 0.0

    data = {
        "No_of_Classes": classes.count(),
        "No_of_Students": students.count(),
        "Total_Lessons": total_lessons,
        "Avg_Present": get_avg(present_count),
        "Avg_Late": get_avg(late_count),
        "Avg_Absent": get_avg(absent_count),
    }

    return Response(data)

