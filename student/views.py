from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, get_object_or_404

from .models import Student, Branch
from .forms import StudentForm

class HODRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class DashboardView(HODRequiredMixin, TemplateView):
    template_name = "students/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["student_count"] = Student.objects.count()

        context["active_student_count"] = Student.objects.filter(
            status="Active"
        ).count()

        context["branch_stats"] = Branch.objects.annotate(
            student_count=Count("students")
        )

        return context


class StudentListView(HODRequiredMixin, ListView):
    model = Student
    template_name = "students/student_list.html"
    context_object_name = "students"

    def get_queryset(self):
        students = Student.objects.select_related("branch")

        search = self.request.GET.get("q", "").strip()
        branch = self.request.GET.get("branch", "").strip()

        if search:
            students = students.filter(
                Q(admission_no__icontains=search)
                | Q(roll_no__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
            )

        if branch:
            students = students.filter(
                branch__code=branch
            )

        return students

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["branches"] = Branch.objects.all()
        return context


class StudentDetailView(HODRequiredMixin, DetailView):
    model = Student
    template_name = "students/student_detail.html"
    context_object_name = "student"


class StudentCreateView(HODRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "students/student_form.html"
    success_url = reverse_lazy("student-list")


class StudentUpdateView(HODRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "students/student_form.html"
    success_url = reverse_lazy("student-list")


class StudentDeleteView(HODRequiredMixin, DeleteView):
    model = Student
    template_name = "students/student_confirm_delete.html"
    success_url = reverse_lazy("student-list")


class BranchDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "students/branch_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        code = self.kwargs.get("code")
        branch = get_object_or_404(Branch, code=code)
        students = Student.objects.filter(branch=branch)
        context["branch"] = branch
        context["students"] = students
        return context


class MyProfileView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = "students/my_profile.html"
    context_object_name = "student"

    def get_object(self, queryset=None):
        return get_object_or_404(Student, user=self.request.user)


class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        if self.request.user.is_superuser:
            return "/"
        return "/my-profile/"