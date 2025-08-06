from rest_framework import viewsets, status, permissions #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, permission_classes, action #type: ignore
from rest_framework.pagination import PageNumberPagination #type: ignore
from django.views.decorators.csrf import csrf_exempt #type: ignore
from django.http import JsonResponse #type: ignore
from django.db.models import Count, F, IntegerField, Value #type: ignore
from django.db.models.functions import ExtractYear, Now #type: ignore
from sklearn.linear_model import LinearRegression #type: ignore
import numpy as np #type: ignore
from datetime import datetime
from collections import defaultdict, OrderedDict
from django.utils.timezone import now  #type: ignore
import calendar

from Core.models import Department, Institution, Unit
from Core.serializers import UnitSerializer

from .models import *
from .serializers import *
from .filters import *
from .application import *

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_new_application(request, app_id):
    return Response(approve_application(app_id))

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def decline_new_application(request, app_id):
    return Response(decline_application(app_id))

@csrf_exempt
def enroll_new_application(request, temp_no):
    return JsonResponse(enroll_student(temp_no))

@api_view(['GET'])
def student_count(request, filter):
    if filter == "pending_allocation":
        count = Allocate_Student.objects.filter(state = "Pending").count()
    elif filter == "pending_enrollment":
        count = Application.objects.filter(state = "Pending").count()
    elif filter == "joined_enrollment":
        count = Application.objects.filter(state = "Joined").count()
    elif filter == "declined_enrollment":
        count = Application.objects.filter(state = "Declined").count()
    elif filter == "approved_enrollment":
        count = Application.objects.filter(state = "Approved").count()
    elif filter == "enrollment":
        count = Application.objects.count()
    else:
        count = Student.objects.count()
    return Response({"count": count})

@api_view(['GET'])
def get_current_and_previous_enrollment(request):
    """
    API to return current and previous intake student counts.
    Frontend can then calculate % change.
    """
    currentTerm = Term.objects.filter(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).first()
    previousTerm = Term.objects.filter(id = currentTerm.id - 1).first()
    if not previousTerm:
        previousTerm = currentTerm

    # Count students for each intake
    current_count = Application.objects.filter(intake = currentTerm.name, year = currentTerm.year).count()
    previous_count = Application.objects.filter(intake = previousTerm.name, year = previousTerm.year ).count()

    return JsonResponse({
        "current": current_count,
        "previous": previous_count
    })

@api_view(['GET'])
def get_current_and_previous_pending_enrollment(request):
    """
    API to return current and previous intake pending student counts.
    Frontend can then calculate % change.
    """
    currentTerm = Term.objects.filter(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).first()
    previousTerm = Term.objects.filter(id = currentTerm.id - 1).first()
    if not previousTerm:
        previousTerm = currentTerm
    # Count students for each intake
    current_count = Application.objects.filter(intake = currentTerm.name, year = currentTerm.year, state = "Pending").count()
    previous_count = Application.objects.filter(intake = previousTerm.name, year = previousTerm.year, state = "Pending" ).count()
    
    return JsonResponse({
        "current": current_count,
        "previous": previous_count
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def batch_approve_view(request):
    application_ids = request.data.get('application_ids', [])
    results = []

    for app_id in application_ids:
        result = approve_application(app_id)
        result['id'] = app_id
        results.append(result)

    return Response({'results': results})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def allocate_view(request, stud_id, class_id):
    return Response(allocate_student(stud_id, class_id))

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def batch_promote_view(request):
    student_ids = request.data.get('student_ids', [])
    results = []

    for student_id in student_ids:
        result = promote_student(student_id)
        results.append(result)

    return Response({ 'messages': results, })
 
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def batch_allocate_view(request):
    student_ids = request.data.get('student_ids', [])
    class_id = request.data.get('class_id')
    results = []

    message = {}
    errors = ""
    success = ""

    for stud_id in student_ids:
        result = allocate_student(stud_id, class_id)
        for key in result:
            if key == 'error':
                if errors == "":
                    errors += "-"+ result["error"]
                else:
                    errors += "<br/><br/>- " + result["error"]
            else:
                success=(result["message"])

    message["error"] = errors
    message["success"] = success

    print(message)

    return Response(message)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def student_units(request, id):
    student_object = Allocate_Student.objects.get(studentno__id = id)
    course_id = student_object.Class.course.id
    module_id = student_object.module.id
    units = Unit.objects.filter(course__id = course_id, module__id = module_id)
    serializer = UnitSerializer(units, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_current_and_previous_pending_allocation(request):
    """
    API to return current and previous allocations pending student counts.
    Frontend can then calculate % change.
    """
    currentTerm = Term.objects.filter(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).first()
    previousTerm = Term.objects.filter(id = currentTerm.id - 1).first()
    if not previousTerm:
        previousTerm = currentTerm

    # Count students for each allocations
    current_count = Allocate_Student.objects.filter(term = currentTerm, state = "Pending").count()
    previous_count = Allocate_Student.objects.filter(term = currentTerm, state = "Pending" ).count()
    
    return JsonResponse({
        "current": current_count,
        "previous": previous_count
    })

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

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all().order_by('id')
    serializer_class = StudentSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], url_path='department_counts')
    def department_counts(self, request):
        data = (
            Student.objects
            .values(department_name=F('course__department__abbr'))
            .annotate(student_count=Count('id'))
            .order_by('-student_count')
        )
        return Response(data)

class ApplicationViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Application.objects.all().order_by('id')
        status_param = self.request.query_params.get("status", None)
        search_param = self.request.query_params.get("search", None)

        if status_param:
            queryset = queryset.filter(state__iexact=status_param)

        # You don't need to manually filter for search_param here
        # ExtendedMultiKeywordSearchFilter should handle it

        return queryset

    # Determine which serializer to use based on action
    def get_serializer_class(self):
        if self.action == 'create':
            return ApplicationCreateSerializer
        return ApplicationDetailSerializer

    def create(self, request, *args, **kwargs):
        nat_id = request.data.get('nat_id')
        email = request.data.get('email')  # Optional: Also check email

        # Check if application with this National ID already exists
        if nat_id and Application.objects.filter(nat_id=nat_id).exists():
            return Response(
                {"detail": "An application with this National ID has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # (Optional) Check by email too
        if Application.objects.filter(email=email).exists():
            return Response(
                {"detail": "An application with this email has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().create(request, *args, **kwargs)

class StudentAllocationViewSet(viewsets.ModelViewSet):
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Allocate_Student.objects.all().order_by('id')
        state_param = self.request.query_params.get("state", None)
        search_param = self.request.query_params.get("search", None)

        if state_param:
            queryset = queryset.filter(state__iexact=state_param)

        return queryset

    serializer_class = StudentAllocationSerializer

    def list(self, request, *args, **kwargs):
            if self.request.query_params.get('all') == 'true':
                queryset = self.filter_queryset(self.get_queryset())
                serializer = self.get_serializer(queryset, many=True)
                return Response({'results': serializer.data})  # mimic paginated structure
            return super().list(request, *args, **kwargs)
        
    @action(detail=False, methods=['get'], url_path='class_counts')
    def class_counts(self, request):
        data = (
            Allocate_Student.objects
            .values(class_name=F('Class__name'))
            .annotate(student_count=Count('id'))
            .order_by('-student_count')
        )
        return Response(data)

@api_view(["GET"])
def branch_student_stats(request):
    total_students = Student.objects.count()
    if total_students == 0:
        return Response([])

    branches = (
        Branch.objects
        .annotate(student_count=Count('student'))
        .values('id', 'name', 'student_count')
    )

    # Add percentage to each branch
    stats = [
        {
            'id': b['id'],
            'name': b['name'],
            'student_count': b['student_count'],
            'percentage': round((b['student_count'] / total_students) * 100, 2)
        }
        for b in branches
    ]

    return Response(stats)

@api_view(["GET"])
def check_application_status(request):
    application_id = request.query_params.get("application_id")
    if not application_id:
        return Response({"error": "Missing application parameter"}, status=400)

    return Response({"status": Application.objects.get(id = application_id).state.lower()})

@api_view(["GET"])
def search_student_class(request):
    student_id = request.query_params.get("student_id")
    if not student_id:
        return Response({"error": "Student NOT found!"})
    
    try:
        student = Allocate_Student.objects.get(id = student_id)
    except Allocate_Student.DoesNotExist:
        return Response({"error": "Student NOT found!"})
    
    currentTerm = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)

    classes = Class.objects.filter(intake = currentTerm, branch = student.Class.branch, module = student.module, state = "Active")

    data = []
    for klass in classes:
        data.append({
            "value": klass.id,
            "label": klass.name
            
        })
        
    return Response(data)

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def change_student_class(request):
    student_id = request.query_params.get("student_id")
    class_id = request.query_params.get("class_id")

    if not student_id or not class_id:
        return Response({"error": "Missing student_id or class_id"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        student = Allocate_Student.objects.select_related("studentno").get(id=student_id)
    except Allocate_Student.DoesNotExist:
        return Response({"error": "Student NOT found!"}, status=status.HTTP_404_NOT_FOUND)

    try:
        student.Class_id = class_id  # Correct attribute name
        student.save()
    except Exception as e:
        return Response({"error": "Failed to update class."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(
        {"success": f"{student.studentno.get_full_name()}’s class has been changed successfully"},
        status=status.HTTP_200_OK
    )

# Reports
def student_master_list(request):
    students = Student.objects.filter(state="Active").select_related(
        "course", "branch", "year", "intake", "sponsor"
    ).order_by("regno")

    data = [
        {
            "regno": s.regno,
            "name": s.get_full_name(),
            "gender": s.gender,
            "dob": s.dob,
            "phone": s.phone,
            "email": s.email,
            "course": s.course.name,
            "branch": s.branch.name,
            "intake": s.intake.name,
            "year": s.year.name,
            "sponsor": s.sponsor.name,
            "state": s.state,
        }
        for s in students
    ]
    return JsonResponse(data, safe=False)

def student_demographics(request):
    today = now().date()
    students = Student.objects.filter(state="Active")

    age_groups = {
        "below_18": students.filter(dob__gte=today.replace(year=today.year - 18)).count(),
        "18_24": students.filter(
            dob__lt=today.replace(year=today.year - 18),
            dob__gte=today.replace(year=today.year - 25)
        ).count(),
        "above_24": students.filter(dob__lt=today.replace(year=today.year - 25)).count()
    }

    gender_stats = students.values("gender").annotate(count=Count("id"))

    return JsonResponse({
        "age_groups": age_groups,
        "gender_stats": list(gender_stats),
        "total_students": students.count()
    })

def application_summary(request):
    applications = Application.objects.all()

    by_course = applications.values("course__name").annotate(count=Count("id"))
    by_gender = applications.values("gender").annotate(count=Count("id"))
    by_grade = applications.values("examgrade").annotate(count=Count("id"))

    return JsonResponse({
        "total_applications": applications.count(),
        "by_course": list(by_course),
        "by_gender": list(by_gender),
        "by_grade": list(by_grade),
    })

def allocation_report(request):
    allocations = Allocate_Student.objects.select_related("studentno", "module", "term", "Class").all()

    data = [
        {
            "student": a.studentno.get_full_name(),
            "regno": a.studentno.regno,
            "course": a.studentno.course.name,
            "term": a.term.name,
            "module": a.module.name,
            "class": a.Class.name if a.Class else None,
            "state": a.state,
            "level": a.level
        }
        for a in allocations
    ]

    return JsonResponse(data, safe=False)

def sponsor_distribution(request):
    data = Student.objects.values("sponsor__name").annotate(count=Count("id")).order_by("-count")
    return JsonResponse(list(data), safe=False)

# Report
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def institution_enrollment_summary(request):
    try:
        this_year = date.today().year
        last_year = this_year - 1
        # Current year students
        all_students = Student.objects.all()

        this_year_students = Student.objects.filter(state = "Active", dor__year = this_year)
        male_students = this_year_students.filter(gender = "Male")
        female_students =  this_year_students.filter(gender = "Female")

        last_year_students = Student.objects.filter(state = "Active", dor__year = last_year)
        last_year_male_students = last_year_students.filter(gender = "Male")
        last_year_female_students = last_year_students.filter(gender  = "Female")

        return Response({
            "summary": {
                "totalActive": this_year_students.count(),
                "totalRegistered": all_students.count(),
                "prevTotalRegistered": last_year_students.count(),

                "male": male_students.count(),
                "female": female_students.count(),
                "prevMale": last_year_male_students.count(),
                "prevFemale": last_year_female_students.count(),
 
                "applied": Application.objects.filter(doa__year = this_year).count(),
                "joined": Application.objects.filter(state = "Joined", doa__year = this_year).count(),
                "prevJoined": Application.objects.filter(state = "Joined", doa__year = last_year).count()
            }
        })

    except Exception as e:
        print("Error in institution_fee_summary:", e)
        return Response({"error": str(e)}, status=500)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def institution_enrollment_trend(request):
    current_year = date.today().year
    start_year = current_year - 4  # Past 5 years

    # Annotate and aggregate invoice totals by year
    student_data = (
        Student.objects.filter(dor__year__gte = start_year)
        .annotate(trendyear = ExtractYear("dor"))
        .values("trendyear")
        .annotate(total = Count("id"))
        .order_by("trendyear")
    )

    # Convert to dict: {year: amount}
    student_map = {str(i["trendyear"]): float(i["total"]) for i in student_data}

    # Combine into trend list
    trend = []
    for year in range(start_year, current_year + 1):
        y = str(year)
        trend.append({
            "year": y,
            "students": round(student_map.get(y, 0))
        })
 
    return Response(trend)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def student_enrollment_status_trend(request):
    current_year = date.today().year
    start_year = current_year - 4  # Past 5 years
    
    # Annotate and aggregate invoice totals by year
    pending_data = (
        Application.objects.filter(state = "Pending", doa__year__gte=start_year)
        .annotate(trend_year=ExtractYear("doa"))
        .values("trend_year")
        .annotate(total=Count("id"))
        .order_by("trend_year")
    )

    declined_data = (
        Application.objects.filter(state = "Declined", doa__year__gte=start_year)
        .annotate(trend_year=ExtractYear("doa"))
        .values("trend_year")
        .annotate(total=Count("id"))
        .order_by("trend_year")
    )

    approved_data = (
        Application.objects.filter(state = "Approved", doa__year__gte=start_year)
        .annotate(trend_year=ExtractYear("doa"))
        .values("trend_year")
        .annotate(total=Count("id"))
        .order_by("trend_year")
    )

    joined_data = (
        Application.objects.filter(state = "Joined", doa__year__gte=start_year)
        .annotate(trend_year=ExtractYear("doa"))
        .values("trend_year")
        .annotate(total=Count("id"))
        .order_by("trend_year")
    )

    # Convert to dict: {year: amount}
    declined_map = {str(i["trend_year"]): float(i["total"]) for i in declined_data}
    pending_map = {str(i["trend_year"]): float(i["total"]) for i in pending_data}
    approved_map = {str(i["trend_year"]): float(i["total"]) for i in approved_data}
    joined_map = {str(i["trend_year"]): float(i["total"]) for i in joined_data}

    # Combine into trend list
    trend = []
    for year in range(start_year, current_year + 1):
        trend.append({
            "year": str(year),
            "declined": declined_map.get(str(year), 0),
            "pending": pending_map.get(str(year), 0),
            "approved": approved_map.get(str(year), 0),
            "joined": joined_map.get(str(year), 0),
        })

    return Response(trend)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def student_gender_trend(request):
    current_year = date.today().year
    start_year = current_year - 4  # Past 5 years
    
    # Annotate and aggregate invoice totals by year
    male_data = (
        Student.objects.filter(gender = "Male", dor__year__gte=start_year)
        .annotate(trend_year=ExtractYear("dor"))
        .values("trend_year")
        .annotate(total=Count("id"))
        .order_by("trend_year")
    )

    # Annotate and aggregate receipt totals by year
    female_data = (
        Student.objects.filter(gender = "Female", dor__year__gte = start_year)
        .annotate(trend_year=ExtractYear("dor"))
        .values("trend_year")
        .annotate(total=Count("id"))
        .order_by("trend_year")
    )

    # Convert to dict: {year: amount}
    male_map = {str(i["trend_year"]): float(i["total"]) for i in male_data}
    female_map = {str(i["trend_year"]): float(i["total"]) for i in female_data}

    # Combine into trend list
    trend = []
    for year in range(start_year, current_year + 1):
        trend.append({
            "year": str(year),
            "male": male_map.get(str(year), 0),
            "female": female_map.get(str(year), 0),
        })

    return Response(trend)

# Predictions
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def predict_applications(request):
    current_year = datetime.now().year
    data = Application.objects.annotate(year_applied=ExtractYear("doa"))

    # 1. Total Applications Per Year
    yearly_data = data.values("year_applied").annotate(total=Count("id")).order_by("year_applied")
    years = [int(row["year_applied"]) for row in yearly_data]
    totals = [row["total"] for row in yearly_data]

    # Predict total applications next year
    reg = LinearRegression()
    reg.fit(np.array(years).reshape(-1, 1), totals)
    next_year = current_year + 1
    total_pred = int(reg.predict([[next_year]])[0])

    # 2. Per Course Prediction
    course_data = data.values("year_applied", "course__id").annotate(total=Count("id"))
    course_trends = defaultdict(list)
    for row in course_data:
        course_trends[row["course__id"]].append((row["year_applied"], row["total"]))

    course_predictions = {}
    for course, vals in course_trends.items():
        ys, ts = zip(*vals)
        if len(ys) > 1:
            model = LinearRegression().fit(np.array(ys).reshape(-1, 1), ts)
            course_predictions[course] = int(model.predict([[next_year]])[0])
        else:
            course_predictions[course] = ts[0]  # fallback

    # 3. Gender Prediction
    gender_data = data.values("year_applied", "gender").annotate(total=Count("id"))
    gender_trends = defaultdict(list)
    for row in gender_data:
        gender_trends[row["gender"]].append((row["year_applied"], row["total"]))

    gender_predictions = {}
    for gender, vals in gender_trends.items():
        ys, ts = zip(*vals)
        if len(ys) > 1:
            model = LinearRegression().fit(np.array(ys).reshape(-1, 1), ts)
            gender_predictions[gender] = int(model.predict([[next_year]])[0])
        else:
            gender_predictions[gender] = ts[0]

    # 4. Age Groups
    age_groups = {"<18": 0, "18-24": 0, ">24": 0}
    for app in data.filter(year_applied=current_year):
        age = (datetime.now().date() - app.dob.date()).days // 365
        if age < 18:
            age_groups["<18"] += 1
        elif age <= 24:
            age_groups["18-24"] += 1
        else:
            age_groups[">24"] += 1

    # Assume next year follows similar proportion trend
    age_predictions = {k: int(v * (total_pred / sum(age_groups.values()))) for k, v in age_groups.items()}

    # 5. Gradewise Predictions
    grade_data = data.values("year_applied", "examgrade").annotate(total=Count("id"))
    grade_trends = defaultdict(list)
    for row in grade_data:
        grade_trends[row["examgrade"]].append((row["year_applied"], row["total"]))

    grade_predictions = {}
    for grade, vals in grade_trends.items():
        ys, ts = zip(*vals)
        if len(ys) > 1:
            model = LinearRegression().fit(np.array(ys).reshape(-1, 1), ts)
            grade_predictions[grade] = int(model.predict([[next_year]])[0])
        else:
            grade_predictions[grade] = ts[0]

    return JsonResponse({
        "year": next_year,
        "total_predicted": total_pred,
        "by_course": course_predictions,
        "by_gender": gender_predictions,
        "by_age": age_predictions,
        "by_grade": grade_predictions,
    })

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])       
def department_gender_summary(request):
    filter_mode = request.GET.get("filter_mode")
    start = request.GET.get("start")
    end = request.GET.get("end")
    start_intake_id = ""
    end_intake_id = ""

    filter_kwargs = {}

    # Handle filtering based on mode
    if filter_mode == "Annual":
        if start and end:
            filter_kwargs["year__id__range"] = (start, end)
        elif start:
            filter_kwargs["year__id"] = start
        elif end:
            filter_kwargs["year__id"] = end

    elif filter_mode == "Termly":
        if start and end:
            start_intake_id = Term.objects.get(id = start).name
            end_intake_id = Term.objects.get(id = end).name
            filter_kwargs["intake__id__range"] = (start_intake_id.id, end_intake_id.id)
        elif start:
            filter_kwargs["intake__id"] = start_intake_id.id
        elif end:
            filter_kwargs["intake__id"] = end_intake_id.id

    departments = Department.objects.all()
    result = []

    applications = Application.objects.filter(**filter_kwargs) if filter_kwargs else Application.objects.all()

    for dept in departments:
        dept_data = {
            "id": dept.id,
            "name": dept.name,
            "abbr": dept.abbr,
            "male": 0,
            "female": 0,
            "total": 0,
            "courses": []
        }

        courses = Course.objects.filter(department=dept)
 
        for course in courses:
            course_apps = applications.filter(course=course)
            male_count = course_apps.filter(course=course, gender="Male").count()
            female_count = course_apps.filter(course=course, gender="Female").count()
            course_total = male_count + female_count

            dept_data["male"] += male_count
            dept_data["female"] += female_count
            dept_data["total"] += course_total

            dept_data["courses"].append({
                "id": course.id,
                "name": course.name,
                "abbr": course.abbr,
                "male": male_count,
                "female": female_count,
                "total": course_total,
            })

        result.append(dept_data)

    return JsonResponse(result, safe=False)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def department_age_summary(request):
    filter_mode = request.GET.get("filter_mode")
    start = request.GET.get("start")
    end = request.GET.get("end")
    start_intake_id = ""
    end_intake_id = ""

    filter_kwargs = {}

    # Filter Applications by Year or Term
    if filter_mode == "Annual":
        if start and end:
            filter_kwargs["year__id__range"] = (start, end)
        elif start:
            filter_kwargs["year__id"] = start
        elif end:
            filter_kwargs["year__id"] = end

    elif filter_mode == "Termly":
        if start and end:
            start_intake_id = Term.objects.get(id = start).name
            end_intake_id = Term.objects.get(id = end).name
            filter_kwargs["intake__id__range"] = (start_intake_id.id, end_intake_id.id)
        elif start:
            filter_kwargs["intake__id"] = start_intake_id.id
        elif end:
            filter_kwargs["intake__id"] = end_intake_id.id

    applications = Application.objects.filter(**filter_kwargs) if filter_kwargs else Application.objects.all()
    departments = Department.objects.all()
    result = []

    for dept in departments:
        dept_data = {
            "id": dept.id,
            "name": dept.name,
            "abbr": dept.abbr,
            "less18": 0,
            "btn18_24": 0,
            "great24": 0,
            "total": 0,
            "courses": []
        }

        courses = Course.objects.filter(department=dept)

        for course in courses:
            course_apps = applications.filter(course = course)

            less18 = 0
            btn18_24 = 0
            great24 = 0

            for app in course_apps:
                if app.dob:
                    age = calculate_age(app.dob)
                    if age < 18:
                        less18 += 1
                    elif 18 <= age <= 24:
                        btn18_24 += 1
                    else:
                        great24 += 1

            total = less18 + btn18_24 + great24

            dept_data["less18"] += less18
            dept_data["btn18_24"] += btn18_24
            dept_data["great24"] += great24
            dept_data["total"] += total

            dept_data["courses"].append({
                "id": course.id,
                "name": course.name,
                "abbr": course.abbr,
                "less18": less18,
                "btn18_24": btn18_24,
                "great24": great24,
                "total": total
            })

        result.append(dept_data)

    return JsonResponse(result, safe=False)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def department_exams_summary(request):
    filter_mode = request.GET.get("filter_mode")
    start = request.GET.get("start")
    end = request.GET.get("end")
    start_intake_id = ""
    end_intake_id = ""

    filter_kwargs = {}

    # Filter Applications by Year or Term
    if filter_mode == "Annual":
        if start and end:
            filter_kwargs["year__id__range"] = (start, end)
        elif start:
            filter_kwargs["year__id"] = start
        elif end:
            filter_kwargs["year__id"] = end

    elif filter_mode == "Termly":
        if start and end:
            start_intake_id = Term.objects.get(id = start).name
            end_intake_id = Term.objects.get(id = end).name
            filter_kwargs["intake__id__range"] = (start_intake_id.id, end_intake_id.id)
        elif start:
            filter_kwargs["intake__id"] = start_intake_id.id
        elif end:
            filter_kwargs["intake__id"] = end_intake_id.id

    applications = Application.objects.filter(**filter_kwargs) if filter_kwargs else Application.objects.all()
    departments = Department.objects.all()
    result = []

    for dept in departments:
        dept_data = {
            "id": dept.id,
            "name": dept.name,
            "abbr": dept.abbr,
            "diploma": 0,
            "certificate": 0,
            "kcse": 0,
            "kcpe": 0,
            "total": 0,
            "courses": []
        }

        courses = Course.objects.filter(department=dept)

        for course in courses:
            diploma = 0
            certificate = 0
            kcse = 0
            kcpe = 0

            diploma += applications.filter(course = course, examtype = "Diploma").count()
            certificate += applications.filter(course = course, examtype = "Certificate").count()
            kcse += applications.filter(course = course, examtype = "KCSE").count()
            kcpe += applications.filter(course = course, examtype = "KCPE").count()
                    
            total = diploma + certificate + kcse + kcpe

            dept_data["diploma"] += diploma
            dept_data["certificate"] += certificate
            dept_data["kcse"] += kcse
            dept_data["kcpe"] += kcpe
            dept_data["total"] += total

            dept_data["courses"].append({
                "id": course.id,
                "name": course.name,
                "abbr": course.abbr,
                "diploma": diploma,
                "certificate": certificate,
                "kcse": kcse,
                "kcpe": kcpe,
                "total": total
            })

        result.append(dept_data)

    return JsonResponse(result, safe=False)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def course_gender_breakdown(request):
    course_id = request.query_params.get('course_id')
    filter_mode = request.query_params.get('filter_mode')
    start = request.query_params.get('start')
    end = request.query_params.get('end')
    filter_kwargs = {}

    try:
        # Get course
        course = Course.objects.filter(id = course_id).first()
        if not course:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        if filter_mode == "Annual":
            if start and end:
                filter_kwargs["year__id__range"] = (start, end)
            elif start:
                filter_kwargs["year__id"] = start
            elif end:
                filter_kwargs["year__id"] = end

        elif filter_mode == "Termly":
            if start and end:
                start_intake_id = Term.objects.get(id = start).name
                end_intake_id = Term.objects.get(id = end).name
                filter_kwargs["intake__id__range"] = (start_intake_id.id, end_intake_id.id)
            elif start:
                filter_kwargs["intake__id"] = start_intake_id.id
            elif end:
                filter_kwargs["intake__id"] = end_intake_id.id

        # Get applications in course
        applications = Application.objects.filter(course = course, **filter_kwargs) if filter_kwargs else Application.objects.filter(course = course)
        student_data = []

        for app in applications:
            student_data.append({
                "profile_picture": app.passport.url if app.passport else None,
                "student_name": app.get_full_name(),
                "regno": app.regno,
                "gender": app.gender,
                "status": app.state
            })

        return Response(student_data, status=status.HTTP_200_OK)

    except Exception as e:
        print("Error in Course student breakdown view:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def course_age_summary(request):
    course_id = request.query_params.get('course_id')
    filter_mode = request.GET.get("filter_mode")
    start = request.GET.get("start")
    end = request.GET.get("end")
    start_intake_id = ""
    end_intake_id = ""

    filter_kwargs = {}

    try:
        
        # Get course
        course = Course.objects.filter(id = course_id).first()
        if not course:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        # Filter Applications by Year or Term
        if filter_mode == "Annual":
            if start and end:
                filter_kwargs["year__id__range"] = (start, end)
            elif start:
                filter_kwargs["year__id"] = start
            elif end:
                filter_kwargs["year__id"] = end

        elif filter_mode == "Termly":
            if start and end:
                start_intake_id = Term.objects.get(id = start).name
                end_intake_id = Term.objects.get(id = end).name
                filter_kwargs["intake__id__range"] = (start_intake_id.id, end_intake_id.id)
            elif start:
                filter_kwargs["intake__id"] = start_intake_id.id
            elif end:
                filter_kwargs["intake__id"] = end_intake_id.id

        applications = Application.objects.filter(course = course, **filter_kwargs) if filter_kwargs else Application.objects.filter(course = course)
        student_data = []

        for app in applications:
            student_data.append({
                "profile_picture": app.passport.url if app.passport else None,
                "student_name": app.get_full_name(),
                "regno": app.regno,
                "age": calculate_age(app.dob),
                "status": app.state
            })

        return JsonResponse(student_data, safe=False)
    except Exception as e:
        print("Error in Course student breakdown view:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def course_exams_summary(request):
    course_id = request.query_params.get('course_id')
    filter_mode = request.GET.get("filter_mode")
    start = request.GET.get("start")
    end = request.GET.get("end")
    start_intake_id = ""
    end_intake_id = ""

    filter_kwargs = {}

    try:
        # Get course
        course = Course.objects.filter(id = course_id).first()
        if not course:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        # Filter Applications by Year or Term
        if filter_mode == "Annual":
            if start and end:
                filter_kwargs["year__id__range"] = (start, end)
            elif start:
                filter_kwargs["year__id"] = start
            elif end:
                filter_kwargs["year__id"] = end

        elif filter_mode == "Termly":
            if start and end:
                start_intake_id = Term.objects.get(id = start).name
                end_intake_id = Term.objects.get(id = end).name
                filter_kwargs["intake__id__range"] = (start_intake_id.id, end_intake_id.id)
            elif start:
                filter_kwargs["intake__id"] = start_intake_id.id
            elif end:
                filter_kwargs["intake__id"] = end_intake_id.id

        applications = Application.objects.filter(course = course, **filter_kwargs) if filter_kwargs else Application.objects.filter(course = course)
        student_data = []

        for app in applications:
            student_data.append({
                "profile_picture": app.passport.url if app.passport else None,
                "student_name": app.get_full_name(),
                "regno": app.regno,
                "exams": app.examtype,
                "grade": app.examgrade,
                "status": app.state
            })

        return JsonResponse(student_data, safe=False)
    except Exception as e:
        print("Error in Course student breakdown view:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

