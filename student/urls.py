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
]