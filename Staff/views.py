from rest_framework import viewsets, status, permissions #type: ignore
from django.contrib.auth.models import Group #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, permission_classes, action #type: ignore
from django.db.models import Count, F #type: ignore

from django.core.mail import send_mail  #type: ignore
from django.conf import settings #type: ignore
 
from rest_framework.pagination import PageNumberPagination #type: ignore
 
from Core.application import generate_password, generate_username
from Core.serializers import ClassSerializer
from Core.models import Institution
from Timetable.models import Timetable

from .models import *
from .serializers import *
from .filters import *
from .application import *
 
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
def staff_count(request, filter):
    if filter == "workload":
        count = StaffWorkload.objects.count()
    elif filter == "tutor":
        count = ClassTutor.objects.count()
    else:
        count = Staff.objects.count()
    return Response({"count": count})

@api_view(['GET'])
def staff_workload(request, id):
    workloads = StaffWorkload.objects.filter(regno__id = id).select_related('unit', 'Class', 'term')
    serializer = StaffWorkloadSerializer(workloads, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_workload_view(request, unit_id, lecturer_id, class_id):
    return Response(assign_workload(unit_id, lecturer_id, class_id))

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def assign_workloads_batch(request):
    unit_ids = request.data.get("unit_ids", [])
    lecturer_id = request.data.get("lecturer_id")
    class_id = request.data.get("class_id")

    if not unit_ids or not lecturer_id or not class_id:
        return Response(
            {"error": "Unit(s), Lecturer, and Class are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    message = {}
    errors = ""
    success = ""

    try:
        for unit_id in unit_ids:
            response = assign_workload(unit_id, lecturer_id, class_id)
            for key in response:
                if key == 'error':
                    if errors == "":
                        errors += "-"+ response["error"]
                    else:
                        errors += "<br/><br/>- " + response["error"]
                else:
                    success=(response["message"])
        
        message["error"] = errors
        message["success"] = success

        return Response(message)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def assign_tutor_view(request, class_id, lecturer_id):
    print("Class ID:", class_id, "Lecturer ID: ", lecturer_id)
    message = assign_tutor(class_id, lecturer_id)

    return Response(message)

class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all().order_by('id')
    serializer_class = StaffSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='staff_counts')
    def staff_counts(self, request):
        data = (
            Staff.objects
            .values(department_name=F('department__abbr'))
            .annotate(staff_count=Count('id'))
            .order_by('-staff_count')
        )
        return Response(data)

    @action(detail=False, methods=['get'], url_path='load_counts')
    def load_counts(self, request):
        data = (
            Staff.objects
            .values(load_state_name=F('load_state'))
            .annotate(staff_count=Count('id'))
            .order_by('-staff_count')
        )
        return Response(data)

    def perform_create(self, serializer_class):
        staff = serializer_class.save()

        # Generate a unique username
        username = generate_username(staff.fname, staff.sname, "")

        # Generate a secure password
        password = generate_password()

        # Create the user
        user = User.objects.create_user(
            username=username, password=password,
            first_name=staff.fname, last_name=staff.sname,
            email=staff.email, is_active=True
        )
        user.save()

        userprofile = UserProfile.objects.create(
            user = user, picture = staff.passport,
            phone = staff.phone, branch = staff.branch
        )
        userprofile.save()

        staff.user = userprofile
        staff.save()

        # Assign user to closest matching group (e.g., "Staff" or "Class Tutor")
        group = Group.objects.filter(name__icontains="Lecturer").first()
        if group:
            user.groups.add(group)

        # Send credentials via email
        try:
            send_mail(
                subject="JiEdu Staff Account",
                message=(
                    f"Dear {staff.fname},\n\n"
                    f"Your account has been created.\n\n"
                    f"Username: {user.username}\n"
                    f"Password: {password}\n\n"
                    f"Please log in and change your password immediately.\n\n"
                    f"Regards,\nJiEdu Admin Team."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[staff.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email failed to send: {e}")

# STAFF WORKLOAD
class StaffWorkloadViewSet(viewsets.ModelViewSet):
    queryset = StaffWorkload.objects.all().order_by('id')
    serializer_class = StaffWorkloadSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)

class ClassTutorViewSet(viewsets.ModelViewSet):
    queryset = ClassTutor.objects.all().order_by('id')
    serializer_class = ClassTutorSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)

@api_view(["GET"])
def unassigned_classes(request):
    unassigned = Class.objects.exclude(id__in=ClassTutor.objects.values_list('Class_id', flat=True))
    serializer = ClassSerializer(unassigned, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def search_class_lecturers(request):
    class_id = request.query_params.get("class_id")
    if not class_id:
        return Response({"error": "Class NOT found!"})
    
    try:
        tutor = ClassTutor.objects.get(id = class_id)
    except ClassTutor.DoesNotExist:
        return Response({"error": "Class NOT found!"})
    
    lecturers = Staff.objects.filter(department = tutor.Class.course.department, branch = tutor.Class.branch)

    data = []
    for lecturer in lecturers:
        data.append({
            "value": lecturer.id,
            "label": lecturer.get_name_reg()
            
        })
        
    return Response(data)

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def change_class_tutor(request):
    lecturer_id = request.query_params.get("lecturer_id")
    class_name = request.query_params.get("class_name")

    if not lecturer_id or not class_name:
        return Response(
            {"error": "Missing Lecturer ID or Class Name."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        tutor = ClassTutor.objects.select_related("Class").get(Class__name=class_name)
    except ClassTutor.DoesNotExist:
        return Response(
            {"error": f"No tutor record found for class '{class_name}'."},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        lecturer = Staff.objects.get(id=lecturer_id)
    except Staff.DoesNotExist:
        return Response(
            {"error": "Lecturer not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check if the lecturer is already assigned to any class (excluding the current one)
    already_assigned = ClassTutor.objects.filter(regno=lecturer).exclude(id=tutor.id).exists()
    if already_assigned:
        return Response(
            {"error": f"{lecturer.get_full_name()} is already assigned to another class."},
            status=status.HTTP_400_BAD_REQUEST
        )

    tutor.regno = lecturer  # Assuming `regno` is the FK to Staff
    try:
        tutor.save()
    except Exception as e:
        return Response(
            {"error": f"Failed to update class tutor: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        {"success": f"{tutor.Class.name}'s tutor has been changed successfully."},
        status=status.HTTP_200_OK
    )

@api_view(["GET"])
def search_workload_lecturers(request):
    workload_id = request.query_params.get("workload_id")
    if not workload_id:
        return Response({"error": "Workload NOT found!"})
    
    try:
        tutor = StaffWorkload.objects.get(id = workload_id)
    except StaffWorkload.DoesNotExist:
        return Response({"error": "Workload NOT found!"})
    
    lecturers = Staff.objects.filter(department = tutor.Class.course.department, branch = tutor.Class.branch)

    data = []
    for lecturer in lecturers:
        data.append({
            "value": lecturer.id,
            "label": lecturer.get_name_reg()
            
        })
        
    return Response(data)

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def check_new_lecturer_workload(request):
    lecturer_id = request.query_params.get("lecturer_id")
    load_id = request.query_params.get("load_id")

    try:
        trainer = Staff.objects.get(id=lecturer_id)
    except Staff.DoesNotExist:
        return Response({"conflict": True, "message": "Lecturer not found"}, status=404)

    try:
        workload = StaffWorkload.objects.get(id=load_id)
    except StaffWorkload.DoesNotExist:
        return Response({"conflict": True, "message": "Workload not found"}, status=404)

    currentTerm = Term.objects.get(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year)

    # Check New Staff Used/Unused Load hours
    new_assigned_lessons = Timetable.objects.filter(term = currentTerm, unit__regno = trainer)
    new_totalHours = 0
    if new_assigned_lessons:
        for entry in new_assigned_lessons:
            duration = entry.lesson.duration  # assuming lesson is FK and duration is TimeField or timedelta
            if duration:
                try:
                    total_seconds = duration.hour * 3600 + duration.minute * 60 + duration.second
                except AttributeError:
                    total_seconds = duration.total_seconds()
                new_totalHours += total_seconds / 3600
    
    if new_totalHours >= trainer.weekly_hours:
        return Response({"conflict": True, "message": f"{trainer.get_name_reg()} has reached maximum lesson hours."})
    unused_hours = trainer.weekly_hours - new_totalHours

    # Check Previous Load Load hours
    previous_assigned_lessons = Timetable.objects.filter(term = currentTerm, unit = workload)
    previous_totalHours = 0
    if previous_assigned_lessons:
        for entry in previous_assigned_lessons:
            duration = entry.lesson.duration  # assuming lesson is FK and duration is TimeField or timedelta
            if duration:
                try:
                    total_seconds = duration.hour * 3600 + duration.minute * 60 + duration.second
                except AttributeError:
                    total_seconds = duration.total_seconds()
                previous_totalHours += total_seconds / 3600
    
    if previous_totalHours > unused_hours:
        return Response({"conflict": True, "message": f"{trainer.get_name_reg()} has only {unused_hours}hrs remaining yet the workload carries {previous_totalHours}hrs."})

    return Response({"success": f"Trainer Available"})

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def change_unit_workload(request):
    lecturer_id = request.query_params.get("lecturer_id")
    workload_id = request.query_params.get("workload_id")

    if not lecturer_id or not workload_id:
        return Response(
            {"error": "Missing Lecturer ID or Class Name."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        tutor = StaffWorkload.objects.get(id = workload_id)
    except StaffWorkload.DoesNotExist:
        return Response(
            {"error": f"No workload record found !."},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        lecturer = Staff.objects.get(id=lecturer_id)
    except Staff.DoesNotExist:
        return Response(
            {"error": "Lecturer not found."},
            status=status.HTTP_404_NOT_FOUND
        )
 
    tutor.regno = lecturer  # Assuming `regno` is the FK to Staff
    try:
        tutor.save()
    except Exception as e:
        return Response(
            {"error": f"Failed to update unit workload: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
 
    return Response(
        {"success": f"{tutor.Class.name}'s {tutor.unit.abbr} has been changed successfully."},
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
def get_current_and_previous_pending_workload(request):
    """
    API to return current and previous workload pending student counts.
    Frontend can then calculate % change.
    """
    currentTerm = Term.objects.filter(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).first()
    previousTerm = Term.objects.filter(id = currentTerm.id - 1).first()
    if not previousTerm:
        previousTerm = currentTerm

    # Count students for each workload
    current_count = StaffWorkload.objects.filter(term = currentTerm).count()
    previous_count = StaffWorkload.objects.filter(term = currentTerm ).count()
    
    return JsonResponse({
        "current": current_count,
        "previous": previous_count
    })

@api_view(['GET'])
def get_current_and_previous_pending_tutor(request):
    """
    API to return current and previous tutor pending student counts.
    Frontend can then calculate % change.
    """
    currentTerm = Term.objects.filter(name = Institution.objects.first().current_intake, year = Institution.objects.first().current_year).first()
    previousTerm = Term.objects.filter(id = currentTerm.id - 1).first()
    if not previousTerm:
        previousTerm = currentTerm

    # Count students for each tutor
    current_count = ClassTutor.objects.filter(Class__intake = currentTerm).count()
    previous_count = ClassTutor.objects.filter(Class__intake = currentTerm ).count()
    
    return JsonResponse({
        "current": current_count,
        "previous": previous_count
    })
