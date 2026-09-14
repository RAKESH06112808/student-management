from django.urls import path
from . import views
from .views import (
    DashboardView,
    BranchDashboardView,
    MyProfileView,
    StudentListView,
    StudentDetailView,
    StudentCreateView,
    StudentUpdateView,
    StudentDeleteView,
    AttendanceView,
    ForgotPasswordView,
    VerifyMobileView,
    VerifyOTPView,
    NewPasswordView,
    download_all_students_pdf,
    download_student_pdf,
    download_my_profile_pdf,
)


urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),

    path(
        "students/",
        StudentListView.as_view(),
        name="student-list"
    ),

    path(
        "students/add/",
        StudentCreateView.as_view(),
        name="student-create"
    ),

    path(
        "students/<int:pk>/",
        StudentDetailView.as_view(),
        name="student-detail"
    ),

    path(
        "students/<int:pk>/attendance/",
        AttendanceView.as_view(),
        name="student-attendance"
    ),

    path(
    "attendance/<int:pk>/edit/",
    views.EditAttendanceView.as_view(),
    name="edit-attendance",
),

    path(
        "students/<int:pk>/edit/",
        StudentUpdateView.as_view(),
        name="student-update"
    ),

    path(
        "students/<int:pk>/delete/",
        StudentDeleteView.as_view(),
        name="student-delete"
    ),

    path(
        "branch/<str:code>/",
        BranchDashboardView.as_view(),
        name="branch-dashboard"
    ),

    path(
        "branch/<str:code>/" \
        "bulk-attendance/",
        views.BulkAttendanceView.as_view(),
        name="bulk-attendance",
    ),

    path(
    "branch/<str:code>/attendance/export/",
    views.export_branch_attendance_excel,
    name="export-branch-attendance",
),
    path(
        "my-profile/",
        MyProfileView.as_view(),
        name="my-profile"
    ),

    path(
        "my-attendance/",
        views.MyAttendanceView.as_view(),
        name="my-attendance"
    ),

    path(
        "forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot_password"
    ),

    path(
        "forgot-password/verify/",
        VerifyMobileView.as_view(),
        name="verify_mobile"
    ),

    path(
        "forgot-password/otp/",
        VerifyOTPView.as_view(),
        name="verify_otp"
    ),

    path(
        "forgot-password/new-password/",
        NewPasswordView.as_view(),
        name="new_password"
    ),

    path(
        "students/pdf/",
        download_all_students_pdf,
        name="students-pdf"
    ),

    path(
        "students/<int:pk>/pdf/",
        download_student_pdf,
        name="student-pdf"
    ),

    path(
        "my-profile/pdf/",
        download_my_profile_pdf,
        name="my-profile-pdf"
    ),
]