from django.contrib import admin
from .models import Branch, Student


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