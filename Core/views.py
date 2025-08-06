from rest_framework import filters, viewsets, status, permissions #type: ignore
from django.contrib.auth.models import Permission, Group #type: ignore
from rest_framework.generics import ListCreateAPIView #type: ignore
from rest_framework.views import APIView #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, action, permission_classes #type: ignore
from django.views.decorators.csrf import csrf_exempt #type: ignore
from django.apps import apps #type: ignore
from django.views.decorators.http import require_GET, require_POST #type: ignore
from django.http import JsonResponse #type: ignore
from rest_framework.pagination import PageNumberPagination #type: ignore
from rest_framework_simplejwt.tokens import RefreshToken, TokenError #type: ignore
from django.core.mail import send_mail  #type: ignore

from .models import *
from .application import *
from .serializers import *
from .filters import *

from Students.application import deactivate_student

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
def gender_choices(request):
    return Response([{'value': choice[0], 'label': choice[1]} for choice in GENDER_CHOICES])

@api_view(['GET'])
def relationship_choices(request):
    return Response([{'value': choice[0], 'label': choice[1]} for choice in RELATIONSHIP_CHOICES])

@api_view(['GET'])
def exam_choices(request):
    return Response([{'value': choice[0], 'label': choice[1]} for choice in EXAM_CHOICES])

class AppModelListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        data = []
        for app_config in apps.get_app_configs():
            models = [model._meta.object_name for model in app_config.get_models()]
            if models:
                data.append({
                    'app_label': app_config.label,
                    'verbose_name': app_config.verbose_name,
                    'models': models,
                })
        return Response(data)

class GroupListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = GroupProfile.objects.all()
    serializer_class = GroupSerializer

class DeleteGroupView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, group_id):
        try:
            group = GroupProfile.objects.get(id = group_id)
            group.delete()
            return Response({ "message": "Group deleted" }, status=status.HTTP_200_OK)
        except GroupProfile.DoesNotExist:
            return Response( { "error": "Group not found" }, status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def assign_permission_to_group(request, group):
    group_id = request.data.get("group_id")
    perm_ids = request.data.get("permissions", [])

    try:
        group_profile = GroupProfile.objects.get(id=group_id)
        group = group_profile.group

        existing_perms = set(group.permissions.values_list("id", flat=True))
        new_perm_ids = set(perm_ids) - existing_perms

        if new_perm_ids:
            new_permissions = Permission.objects.filter(id__in=new_perm_ids)
            group.permissions.add(*new_permissions)

        return Response({"message": "Permissions added successfully"})
    
    except GroupProfile.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)

@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_role_permissions(request):
    app_label = request.GET.get('app')
    group_name = request.GET.get('group')

    if not app_label or not group_name:
        return Response({'detail': 'Missing app or group parameter'}, status=400)

    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return Response({'detail': 'Group not found'}, status=404)

    # Get all permissions assigned to the group for the app
    group_permissions = group.permissions.filter(content_type__app_label=app_label)

    result = {}

    for perm in group_permissions:
        model = perm.content_type.model_class().__name__.lower()
        action = perm.codename.split('_')[0]  # e.g. 'add', 'change', 'view', 'delete'

        if model not in result:
            result[model] = {
                "view": False,
                "add": False,
                "change": False,
                "delete": False
            }

        if action == 'view':
            result[model]["view"] = True
        elif action == 'add':
            result[model]["add"] = True
        elif action == 'change':
            result[model]["change"] = True
        elif action == 'delete':
            result[model]["delete"] = True

    return Response(result, status=200)

@require_GET
def list_permissions(request):
    permissions = Permission.objects.select_related("content_type").all()
    data = {}

    for perm in permissions:
        app = perm.content_type.app_label
        model = perm.content_type.model
        codename = perm.codename

        if app not in data:
            data[app] = {}
        if model not in data[app]:
            data[app][model] = []

        data[app][model].append({
            "id": perm.id,
            "codename": codename,
            "name": perm.name
        })
    return JsonResponse(data)

@api_view(['GET'])
def users_count(request):
    count = UserProfile.objects.count()
    return Response({"count": count})

@api_view(['GET'])
def unit_count(request):
    count = Unit.objects.count()
    return Response({"count": count})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        # Add any custom fields here
    })

@api_view(['GET'])
def branch_count(request):
    """
    API to return current and active branches.
    Frontend can then calculate % change.
    """
    current_count = Branch.objects.all().count()
    
    return JsonResponse({
        "current": current_count,
    })

class UsersViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all().order_by('id')
    serializer_class = UserProfileSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all().order_by('id')
    serializer_class = AcademicYearSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

class IntakeViewSet(viewsets.ModelViewSet):
    queryset = Intake.objects.all().order_by('id')
    serializer_class = IntakeSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)
    
    def perform_create(self, seralizer_class):
        intake = seralizer_class.save()
        intake.name = str(intake.openingMonth)[0:3]+'/'+str(intake.closingMonth)[0:3]
        intake.save()

class TermViewSet(viewsets.ModelViewSet):
    queryset = Term.objects.all().order_by('id')
    serializer_class = TermSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        
        range_param = request.query_params.get('range')
        if range_param:
            try:
                year_range = int(range_param)
                current_year_name = Institution.objects.first().current_year.name

                # Convert year string to integer for arithmetic
                current_year = int(current_year_name.split("/")[0])

                # Create a list of acceptable year strings like "2024/2025", "2025/2026", etc.
                year_strings = [
                    f"{year}/{year + 1}" for year in range(current_year - year_range, current_year + year_range + 1)
                ]

                queryset = self.get_queryset().filter(year__name__in=year_strings)

                queryset = self.filter_queryset(queryset)
                serializer = self.get_serializer(queryset, many=True)
                return Response({'results': serializer.data})
            except (ValueError, AttributeError):
                return Response({'results': []})
            
        return super().list(request, *args, **kwargs)

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all().order_by('id')
    serializer_class = ModuleSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all().order_by('id')
    serializer_class = BranchSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def with_coordinates(self, request):
        branches = self.get_queryset().filter(latitude__isnull=False, longitude__isnull=False)
        data = [
            {
                "name": b.name,
                "latLng": [b.latitude, b.longitude],
            }
            for b in branches
        ]
        return Response(data)

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('id')
    serializer_class = DepartmentSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by('id')
    serializer_class = CourseSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def create(self, request, *args, **kwargs):
        serializer = CourseCreateSerializer(data=request.data)
        if serializer.is_valid():
            course = serializer.save()
            # Use main serializer for response
            return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})
        return super().list(request, *args, **kwargs)

class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all().order_by('id')
    serializer_class = UnitSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.all().order_by('id')
    serializer_class = ClassSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        
        if request.query_params.get('course_id'):
            course_id = request.query_params.get('course_id')
            queryset = Class.objects.filter(course__id = course_id)
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        
        return super().list(request, *args, **kwargs)

class ClassroomViewSet(viewsets.ModelViewSet):
    queryset = Classroom.objects.all().order_by('id')
    serializer_class = ClassroomSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

class SponsorViewSet(viewsets.ModelViewSet):
    queryset = Sponsor.objects.all().order_by('id')
    serializer_class = SponsorSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        return super().list(request, *args, **kwargs)

class InstitutionViewSet(viewsets.ViewSet):
    """
    A viewset for viewing, creating, and updating the single Institution instance.
    """
    serializer_class = InstitutionSerializer

    def get_object(self):
        return Institution.objects.first()

    def list(self, request):
        institution = self.get_object()
        if not institution:
            return Response({'detail': 'No institution found'}, status=404)
        serializer = self.serializer_class(institution, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        if Institution.objects.exists():
            return Response({'detail': 'Institution already exists. Use update instead.'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        instance = self.get_object()
        if not instance:
            return Response({'detail': 'No institution found to update.'}, status=404)
        data = request.data.copy()

        # If no new logo is uploaded, remove it from the data to preserve the existing one
        if 'logo' not in request.FILES:
            data.pop('logo', None)

        serializer = self.serializer_class(instance, data=data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        return self.list(request)  # reuse list for single instance

    def destroy(self, request, pk=None):
        return Response({'detail': 'Delete not allowed on Institution.'}, status=405)

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def promote_system(request):
    institution = Institution.objects.first()

    if not institution:
        return Response({"error": "No institution found."}, status=status.HTTP_404_NOT_FOUND)

    current_year = institution.current_year
    current_intake = institution.current_intake

    intakes = list(Intake.objects.all().order_by("id"))
    years = list(AcademicYear.objects.all().order_by("id"))

    if not current_year or not current_intake:
        return Response({"error": "Current year or intake not set."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        current_intake_index = intakes.index(current_intake)
    except ValueError:
        return Response({"error": "Current intake not in intake list."}, status=status.HTTP_400_BAD_REQUEST)

    if current_intake_index < len(intakes) - 1:
        # Promote to next intake within the same year
        next_intake = intakes[current_intake_index + 1]
        # Check if the next intake is registered in Term
        next_term = Term.objects.filter(name=next_intake, year=current_year).first()
        if not next_term:
            # Create next term if it doesn't exist
            start, end = map(int, current_year.name.split("/"))
            next_term = Term.objects.get_or_create(
                name=next_intake,
                year=current_year,
                defaults={
                    "openingDate": get_opening_date(start, next_intake.openingMonth.title()),
                    "closingDate": get_closing_date(start, next_intake.closingMonth.title()),
                }
            )
        institution.current_intake = next_intake
        institution.promotionMode = True  # Set promotion mode to true
        message = f"Promoted to next intake: {next_intake.name}"
    else:
        # Promote to next academic year and first intake
        try:
            current_year_index = years.index(current_year)
        except ValueError:
            return Response({"error": "Current year not in year list."}, status=status.HTTP_400_BAD_REQUEST)

        if current_year_index < len(years) - 1:
            next_year = years[current_year_index + 1]
        else:
            # Create next year
            try:
                start, end = map(int, current_year.name.split("/"))
                new_name = f"{start + 1}/{end + 1}"
            except (ValueError, AttributeError):
                return Response({"error": "Invalid current academic year format. Expected 'YYYY/YYYY'."}, status=400)
            
            next_year, created = AcademicYear.objects.get_or_create(name=new_name)

            # Create next term
            next_term, created = Term.objects.get_or_create(
                name=intakes[0],
                year=next_year,
                defaults={
                    "openingDate": get_opening_date(start + 1, intakes[0].openingMonth.title()),
                    "closingDate": get_closing_date(start + 1, intakes[0].closingMonth.title()),
                }
            )
            if created:
                print(f"Created new term: {next_term.name} for year: {next_year.name}")

        institution.current_year = next_year
        institution.current_intake = intakes[0]
        institution.promotionMode = True  # Set promotion mode to true
        message = f"Promoted to new academic year: {next_year.name} and intake: {intakes[0].name}"
        
    institution.save()

    # Mark all students inactive
    response = deactivate_student("all")

    # Bring forward all active student's fee status

    # Check Cleared Classes and Mark them inactive
 
    return Response({
        "success": "System promoted successfully.",
        "current_year": institution.current_year.name,
        "current_intake": institution.current_intake.name,
        "message": message
    }, status=status.HTTP_200_OK)

# Authentication
class CleanLoginView(APIView):
    permission_classes = []  # Allow anyone to access login

    def post(self, request, *args, **kwargs):
        serializer = CleanLoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
        except KeyError:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def reset_own_password(request, username):
    try:
        if request.query_params.get("user_type") == "Student":
            user = User.objects.get(email = username)
        else:
            user = User.objects.get(username = username)

        # Generate a random password
        new_password = generate_password()

        # Set the new password
        user.set_password(new_password)
        user.save()

        # Send email to the user
        send_mail(
            subject="Your password has been reset",
            message=f"Hello {user.first_name},\n\nYour new password is: {new_password}\n\nPlease login and change it immediately.",
            from_email="no-reply@jiedu.com",
            recipient_list=[user.email],
        )

        return Response({"message": "Password reset and sent via email successfully."})
    except Exception as e:
        return Response({"message": "No Internet Connection"})