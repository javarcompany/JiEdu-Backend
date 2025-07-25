from django.contrib import admin #type:ignore
from .models import *
from django.urls import reverse #type:ignore
from django.utils.http import urlencode #type:ignore
from django.utils.html import format_html #type:ignore

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Prevent adding new if one exists
        return not Institution.objects.exists()
    
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "paddr","tel_a","tel_b","email","dor")

@admin.register(GroupProfile)
class GroupProfileAdmin(admin.ModelAdmin):
    list_display = ("group",)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name","dor")

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "abbr", "dor")

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "openingDate", "closingDate", "year", "dor")

@admin.register(Intake)
class IntakeAdmin(admin.ModelAdmin):
    list_display = ("openingMonth","closingMonth","dor")

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name","abbr","dor", "view_staff_link")
    def view_staff_link(self, obj):
        count = obj.staff_set.count()
        url = (
            reverse("admin:Core_staff_changelist")+ "?" + urlencode({"courses__id": f"{obj.id}"})
        )
        return format_html('<a href="{}">{} Staffs</a>', url, count)

    view_staff_link.short_description = "Staffs"

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name","abbr","dor","department")

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name","abbr","dor","course","module")

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("name","course","intake","module","dor")

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name", "dor")

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ("name", "abbr", "dor")

@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ("name","phone","email","dor","state")

@admin.register(CourseDuration)
class CourseDurationAdmin(admin.ModelAdmin):
    list_display = ('course', 'module', 'duration')
