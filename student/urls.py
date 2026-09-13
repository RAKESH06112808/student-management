from django.urls import path
from . import views 
urlpatterns = [
]


from .views import (
    DashboardView,
    BranchDashboardView,
    MyProfileView,
    StudentListView,
    StudentDetailView,
    StudentCreateView,
    StudentUpdateView,
    StudentDeleteView,
    ForgotPasswordView,
    VerifyMobileView,
    VerifyOTPView,
    NewPasswordView,
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
           name="branch-dashboard"),

    path(
        "my-profile/",
        MyProfileView.as_view(),
        name="my-profile"
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
    )
]