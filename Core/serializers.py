from rest_framework import serializers #type: ignore
from django.contrib.auth.models import Group #type: ignore
from django.contrib.auth import authenticate    #type: ignore
from rest_framework_simplejwt.tokens import RefreshToken #type: ignore
from django.utils.translation import gettext_lazy as _ #type: ignore

from .models import *
from datetime import date

# Authentication
class CleanLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )

            if not user:
                raise serializers.ValidationError({
                    "detail": _("Incorrect username or password."),
                    "code": "invalid_credentials"
                })

            if not user.is_active:
                raise serializers.ValidationError({
                    "detail": _("This account is inactive. Please contact support."),
                    "code": "inactive_account"
                })

            refresh = RefreshToken.for_user(user)

            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.groups.first().name if user.groups.exists() else 'user',
                }
            }
        else:
            raise serializers.ValidationError({
                "detail": _("Username and password are required."),
                "code": "missing_credentials"
            })

class GroupSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name')
    class Meta:
        model = GroupProfile
        fields = ['id', 'group_name', 'icon']

    def create(self, validated_data):
        group_data = validated_data.pop('group')
        group, created = Group.objects.get_or_create(name=group_data['name'])
        return GroupProfile.objects.create(group=group, **validated_data)

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    userfullname = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()
    status = serializers.CharField(source = 'user.is_active')
    email = serializers.EmailField(source = 'user.email')
    lastlogin = serializers.CharField(source = 'user.last_login')
    branch_name = serializers.CharField(source = 'branch.name')

    class Meta: 
        model = UserProfile
        fields = ['id', 'picture', 'username', 'userfullname', 'group', 'status', 'email', 'branch_name', 'phone', 'lastlogin']

    def get_userfullname(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def get_group(self, obj):
        # Assuming one group per user, else return a list
        group = obj.user.groups.all()
        return group[0].name if group else None
    
class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = '__all__'

class IntakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intake
        fields = '__all__'

class TermSerializer(serializers.ModelSerializer):
    term_name = serializers.CharField(source='name.name', read_only=True)
    year_name = serializers.CharField(source='year.name', read_only=True)
    termyear = serializers.SerializerMethodField()

    class Meta:
        model = Term
        fields = '__all__'

    def get_termyear(self, obj):
        return f"{obj.name.name} - {obj.year.name}".strip()
    
class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class UnitSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.abbr', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)

    class Meta:
        model = Unit
        fields = '__all__'

class ClassSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.abbr', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)
    year_name = serializers.CharField(source='intake.year.name', read_only=True)
    intake_name = serializers.CharField(source='intake.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    class Meta:
        model = Class
        fields = ['id', 'name', 'course', 'intake', 'branch', 'module', 
                'level', 'state', 'dor', 'course_name', 'module_name',
                'year_name', 'branch_name', 'intake_name'
        ]

class ClassroomSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    class Meta:
        model = Classroom
        fields = '__all__'

class SponsorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sponsor
        fields = [
            'id', 'name', 'phone', 'email', 'dor', 'state'
        ]

class InstitutionSerializer(serializers.ModelSerializer):
    year = serializers.CharField(source='current_year.name', read_only=True)
    intake = serializers.CharField(source='current_intake.name', read_only=True)
    passport = serializers.SerializerMethodField()
    
    class Meta:
        model = Institution
        fields =  [
            'id', 'name', 'mission', 'vision', 'logo', 'year', 'intake',
            'current_year', 'current_intake', 'motto', 'paddr', 'telegram',
            'tel_a', 'tel_b', 'facebook', 'instagram', 'youtube', 'instagram',
            'twitter', 'tiktok', 'email', 'newsystem', 'passport'
        ]
        extra_kwargs = {
            'logo': {'required': False, 'allow_null': True}
        }

    def get_passport(self, obj):
        request = self.context.get('request')
        if obj.logo and hasattr(obj.logo, 'url'):
            return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url
        return None