import secrets
import os
from twilio.rest import Client
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, get_object_or_404, redirect

from .models import Student, Branch, HODProfile
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

class ForgotPasswordView(TemplateView):
    template_name = "registration/forgot_password.html"

    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "").strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return render(
                request,
                self.template_name,
                {
                    "error": "Invalid username or recovery details."
                }
            )

        # HOD / Supervisor
        if user.is_superuser:
            try:
                hod_profile = user.hod_profile
            except Exception:
                return render(
                    request,
                    self.template_name,
                    {
                        "error": "Invalid username or recovery details."
                    }
                )

            request.session["reset_user_id"] = user.id
            request.session["reset_type"] = "hod"

            return redirect("/forgot-password/verify/")

        # Student
        try:
            student = user.student_profile
        except Exception:
            return render(
                request,
                self.template_name,
                {
                    "error": "Invalid username or recovery details."
                }
            )

        request.session["reset_user_id"] = user.id
        request.session["reset_type"] = "student"

        return redirect("/forgot-password/verify/")

class VerifyMobileView(TemplateView):
    template_name = "registration/verify_mobile.html"

    def post(self, request, *args, **kwargs):
        user_id = request.session.get("reset_user_id")
        reset_type = request.session.get("reset_type")

        if not user_id or not reset_type:
            return redirect("/forgot-password/")

        phone = request.POST.get("phone", "").strip()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            request.session.flush()
            return redirect("/forgot-password/")

        registered_phone = None

        if reset_type == "hod":
            try:
                registered_phone = user.hod_profile.phone
            except HODProfile.DoesNotExist:
                pass

        elif reset_type == "student":
            try:
                registered_phone = user.student_profile.phone
            except Student.DoesNotExist:
                pass

        # Check the phone number first
        if not registered_phone or phone != registered_phone:
            return render(
                request,
                self.template_name,
                {
                    "error": "Invalid username or recovery details."
                }
            )

        # Send OTP through Twilio Verify
        try:
            client = Client(
                os.environ["TWILIO_ACCOUNT_SID"],
                os.environ["TWILIO_AUTH_TOKEN"]
            )

            verification = client.verify.v2.services(
                os.environ["TWILIO_VERIFY_SERVICE_SID"]
            ).verifications.create(
                to=registered_phone,
                channel="sms"
            )

            print("TWILIO OTP STATUS:", verification.status)

        except Exception as e:
            print("TWILIO ERROR:", e)

            return render(
                request,
                self.template_name,
                {
                    "error": "Unable to send OTP. Please try again."
                }
            )

        request.session["mobile_verified"] = True
        request.session["reset_phone"] = registered_phone

        return redirect("/forgot-password/otp/")


class VerifyOTPView(TemplateView):
    template_name = "registration/verify_otp.html"

    def get(self, request, *args, **kwargs):
        user_id = request.session.get("reset_user_id")
        mobile_verified = request.session.get("mobile_verified")

        if not user_id or not mobile_verified:
            return redirect("/forgot-password/")

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user_id = request.session.get("reset_user_id")
        mobile_verified = request.session.get("mobile_verified")
        reset_phone = request.session.get("reset_phone")

        if not user_id or not mobile_verified or not reset_phone:
            return redirect("/forgot-password/")

        entered_otp = request.POST.get("otp", "").strip()

        if not entered_otp:
            return render(
                request,
                self.template_name,
                {
                    "error": "Please enter the OTP."
                }
            )

        try:
            client = Client(
                os.environ["TWILIO_ACCOUNT_SID"],
                os.environ["TWILIO_AUTH_TOKEN"]
            )

            verification_check = client.verify.v2.services(
                os.environ["TWILIO_VERIFY_SERVICE_SID"]
            ).verification_checks.create(
                to=reset_phone,
                code=entered_otp
            )

            print(
                "TWILIO OTP CHECK STATUS:",
                verification_check.status
            )

        except Exception as e:
            print("TWILIO OTP CHECK ERROR:", e)

            return render(
                request,
                self.template_name,
                {
                    "error": "Unable to verify OTP. Please try again."
                }
            )

        if verification_check.status != "approved":
            return render(
                request,
                self.template_name,
                {
                    "error": "Invalid OTP. Please try again."
                }
            )

        request.session["otp_verified"] = True

        return redirect("/forgot-password/new-password/")


class NewPasswordView(TemplateView):
    template_name = "registration/new_password.html"

    def get(self, request, *args, **kwargs):
        user_id = request.session.get("reset_user_id")
        otp_verified = request.session.get("otp_verified")

        if not user_id or not otp_verified:
            return redirect("/forgot-password/")

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user_id = request.session.get("reset_user_id")
        otp_verified = request.session.get("otp_verified")

        if not user_id or not otp_verified:
            return redirect("/forgot-password/")

        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if password1 != password2:
            return render(
                request,
                self.template_name,
                {
                    "error": "Passwords do not match."
                }
            )

        if not password1:
            return render(
                request,
                self.template_name,
                {
                    "error": "Password cannot be empty."
                }
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            request.session.flush()
            return redirect("/forgot-password/")

        user.set_password(password1)
        user.save()

        request.session.pop("reset_user_id", None)
        request.session.pop("reset_type", None)
        request.session.pop("mobile_verified", None)
        request.session.pop("otp_verified", None)

        return redirect("login")
