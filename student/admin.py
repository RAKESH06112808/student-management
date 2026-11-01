from django.contrib import admin
from .models import Branch, Student, HODProfile, FacultyProfile, Attendance

@admin.register(HODProfile)
class HODProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "email")

@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "branch")
    list_filter = ("branch",)
    search_fields = ("user__username", "branch__code")

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        "admission_no",
        "roll_no",
        "first_name",
        "last_name",
        "branch",
        "current_semester",
        "status",
    ]

    list_filter = [
    "branch",
    "current_semester",
    "status",
    "admission_year",
]

    search_fields = [
    "admission_no",
    "roll_no",
    "first_name",
    "last_name",
    "phone",
]

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "date",
        "status",
        "is_extension_day",
    )

    list_filter = (
    "status",
    "is_extension_day",
    "date",
)

    search_fields = (
    "student__admission_no",
    "student__roll_no",
    "student__first_name",
    "student__last_name",
)

    ordering = ("-date", "student")