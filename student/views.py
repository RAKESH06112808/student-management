import secrets
import os
from datetime import datetime
from io import BytesIO
import openpyxl
from reportlab.pdfgen import canvas
from django.http import HttpResponse

from twilio.rest import Client
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views import View
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from .models import Student, Branch, HODProfile, Attendance
from .forms import StudentForm, AttendanceForm
from .attendance_utils import calculate_attendance, get_default_attendance_status

class HODRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class AttendanceView(HODRequiredMixin, View):
    template_name = "students/attendance.html"

    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)

        selected_date = request.GET.get("date")

        if selected_date:
            try:
                selected_date = datetime.strptime(
                    selected_date, "%Y-%m-%d"
                ).date()
            except ValueError:
                selected_date = timezone.localdate()
        else:
            selected_date = timezone.localdate()

        attendance_record = Attendance.objects.filter(
            student=student,
            date=selected_date
        ).first()

        if attendance_record:
            form = AttendanceForm(instance=attendance_record)
        else:
            default_status = get_default_attendance_status(selected_date)

            form = AttendanceForm(
                initial={
                    "status": default_status,
                    "is_extension_day": False,
                }
            )

        records = Attendance.objects.filter(
            student=student
        ).order_by("-date")

        summary = calculate_attendance(records)

        return render(
            request,
            self.template_name,
            {
                "student": student,
                "form": form,
                "selected_date": selected_date,
                "records": records,
                "summary": summary,
            },
        )

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)

        selected_date = request.POST.get("date")

        try:
            selected_date = datetime.strptime(
                selected_date, "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            selected_date = timezone.localdate()

        attendance_record = Attendance.objects.filter(
            student=student,
            date=selected_date
        ).first()

        is_sunday = selected_date.weekday() == 6

        is_second_saturday = (
            selected_date.weekday() == 5
            and 8 <= selected_date.day <= 14
        )

        if is_sunday or is_second_saturday:
            Attendance.objects.update_or_create(
                student=student,
                date=selected_date,
                defaults={
                    "status": "Weekend Holiday",
                    "is_extension_day": False,
                },
            )
        else:
            if attendance_record:
                form = AttendanceForm(
                    request.POST,
                    instance=attendance_record,
                )
            else:
                form = AttendanceForm(request.POST)

            if form.is_valid():
                attendance = form.save(commit=False)
                attendance.student = student
                attendance.date = selected_date
                attendance.save()

        return redirect(
            "student-attendance",
            pk=student.pk,
        )

class EditAttendanceView(HODRequiredMixin, View):
    template_name = "students/attendance_edit.html"

    def get(self, request, pk):
        attendance = get_object_or_404(
            Attendance,
            pk=pk
        )

        form = AttendanceForm(instance=attendance)

        return render(
            request,
            self.template_name,
            {
                "attendance": attendance,
                "form": form,
            },
        )

    def post(self, request, pk):
        attendance = get_object_or_404(
            Attendance,
            pk=pk
        )

        form = AttendanceForm(
            request.POST,
            instance=attendance
        )

        if form.is_valid():
            form.save()

            return redirect(
                "student-attendance",
                pk=attendance.student.pk
            )

        return render(
            request,
            self.template_name,
            {
                "attendance": attendance,
                "form": form,
            },
        )


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


class BulkAttendanceView(HODRequiredMixin, View):
    template_name = "students/bulk_attendance.html"

    def get(self, request, code):
        branch = get_object_or_404(Branch, code=code)

        selected_date = request.GET.get("date")
        if selected_date:
            try:
                selected_date = datetime.strptime(
                    selected_date, "%Y-%m-%d"
                ).date()
            except ValueError:
                selected_date = timezone.localdate()
        else:
            selected_date = timezone.localdate()

        edit_mode = request.GET.get("edit") == "1"

        students = Student.objects.filter(
            branch=branch
        ).order_by("roll_no")

        attendance_records = Attendance.objects.filter(
            student__branch=branch,
            date=selected_date
        )

        attendance_map = {
            record.student_id: record
            for record in attendance_records
        }

        student_rows = [
            {
                "student": student,
                "attendance": attendance_map.get(student.id),
            }
            for student in students
        ]

        return render(request, self.template_name, {
            "branch": branch,
            "students": students,
            "student_rows": student_rows,
            "selected_date": selected_date,
            "status_choices": Attendance.STATUS_CHOICES,
            "edit_mode": edit_mode,
        })

    def post(self, request, code):
        branch = get_object_or_404(Branch, code=code)

        selected_date = request.POST.get("date")
        status = request.POST.get("status")
        student_ids = request.POST.getlist("student_ids")
        is_extension_day = request.POST.get("is_extension_day") == "on"
        edit_mode = request.POST.get("edit_mode") == "1"

        try:
            selected_date = datetime.strptime(
                selected_date,
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            selected_date = timezone.localdate()

        valid_statuses = dict(Attendance.STATUS_CHOICES)

        if status not in valid_statuses:
            return redirect(
                f"{reverse_lazy('bulk-attendance', kwargs={'code': branch.code})}"
                f"?date={selected_date}"
            )

        # If no students are selected, use ALL students in this branch.
        if student_ids:
            students = Student.objects.filter(
                branch=branch,
                id__in=student_ids
            )
        else:
            students = Student.objects.filter(
                branch=branch
            )

        is_sunday = selected_date.weekday() == 6

        is_second_saturday = (
            selected_date.weekday() == 5
            and 8 <= selected_date.day <= 14
        )

        # Sunday and second Saturday are always Weekend Holiday.
        if is_sunday or is_second_saturday:
            status = "Weekend Holiday"
            is_extension_day = False

        # Holiday and Weekend Holiday cannot be extension days.
        if status in ["Holiday", "Weekend Holiday"]:
            is_extension_day = False

        for student in students:
            Attendance.objects.update_or_create(
                student=student,
                date=selected_date,
                defaults={
                    "status": status,
                    "is_extension_day": is_extension_day,
                },
            )

        if edit_mode:
            return redirect(
                f"{reverse_lazy('bulk-attendance', kwargs={'code': branch.code})}"
                f"?edit=1&date={selected_date}"
            )

        return redirect(
            f"{reverse_lazy('bulk-attendance', kwargs={'code': branch.code})}"
            f"?date={selected_date}"
        )

def export_branch_attendance_excel(request, code):
    branch = get_object_or_404(Branch, code=code)

    records = Attendance.objects.filter(
        student__branch=branch
    ).select_related(
        "student"
    ).order_by(
        "date",
        "student__roll_no"
    )

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Attendance"

    worksheet.append([
        "PIN",
        "Roll No",
        "Student Name",
        "Semester",
        "Date",
        "Status",
        "Extension Day",
    ])

    for record in records:
        worksheet.append([
            record.student.admission_no,
            record.student.roll_no,
            f"{record.student.first_name} {record.student.last_name}".strip(),
            record.student.current_semester,
            record.date,
            record.status,
            "Yes" if record.is_extension_day else "No",
        ])

    from io import BytesIO

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{branch.code}_attendance.xlsx"'
    )

    return response

class MyProfileView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = "students/my_profile.html"
    context_object_name = "student"

    def get_object(self, queryset=None):
        return get_object_or_404(Student, user=self.request.user)

class MyAttendanceView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = "students/my_attendance.html"
    context_object_name = "student"

    def get_object(self, queryset=None):
        return get_object_or_404(
            Student,
            user=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        student = self.object

        records = Attendance.objects.filter(
            student=student
        ).order_by("-date")

        summary = calculate_attendance(records)

        context["records"] = records
        context["summary"] = summary

        return context


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

    # =========================
# PDF DOWNLOAD VIEWS
# =========================

def download_all_students_pdf(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("login")

    students = Student.objects.select_related("branch").all().order_by(
        "admission_no"
    )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.setTitle("All Students")

    y = 800

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "All Students")
    y -= 30

    pdf.setFont("Helvetica", 10)

    for student in students:
        full_name = f"{student.first_name} {student.last_name}".strip()

        lines = [
            f"Admission No: {student.admission_no}",
            f"Roll No: {student.roll_no}",
            f"Name: {full_name}",
            f"Branch: {student.branch.code} - {student.branch.name}",
            f"Admission Year: {student.admission_year}",
            f"Semester: {student.current_semester}",
            f"Gender: {student.gender}",
            f"Date of Birth: {student.date_of_birth or ''}",
            f"Phone: {student.phone}",
            f"Email: {student.email}",
            f"Status: {student.status}",
            f"Address: {student.address}",
        ]

        for line in lines:
            pdf.drawString(50, y, line)
            y -= 15

            if y < 50:
                pdf.showPage()
                y = 800
                pdf.setFont("Helvetica", 10)

        y -= 15

    pdf.save()

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        'attachment; filename="all_students.pdf"'
    )

    return response


def download_student_pdf(request, pk):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect("login")

    student = get_object_or_404(
        Student.objects.select_related("branch"),
        pk=pk
    )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    full_name = f"{student.first_name} {student.last_name}".strip()

    pdf.setTitle(f"Student Profile - {full_name}")

    y = 800

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Student Profile")
    y -= 35

    pdf.setFont("Helvetica", 11)

    lines = [
        f"Admission No: {student.admission_no}",
        f"Roll No: {student.roll_no}",
        f"Name: {full_name}",
        f"Date of Birth: {student.date_of_birth or ''}",
        f"Gender: {student.gender}",
        f"Phone: {student.phone}",
        f"Email: {student.email}",
        f"Address: {student.address}",
        f"Branch: {student.branch.code} - {student.branch.name}",
        f"Admission Year: {student.admission_year}",
        f"Current Semester: {student.current_semester}",
        f"Status: {student.status}",
    ]

    for line in lines:
        pdf.drawString(50, y, line)
        y -= 25

    pdf.save()

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="application/pdf"
    )

    filename = (
        f"{student.admission_no}_student_profile.pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    return response


def download_my_profile_pdf(request):
    if not request.user.is_authenticated:
        return redirect("login")

    student = get_object_or_404(
        Student.objects.select_related("branch"),
        user=request.user
    )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    full_name = f"{student.first_name} {student.last_name}".strip()

    pdf.setTitle(f"My Student Profile - {full_name}")

    y = 800

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "My Student Profile")
    y -= 35

    pdf.setFont("Helvetica", 11)

    lines = [
        f"Admission No: {student.admission_no}",
        f"Roll No: {student.roll_no}",
        f"Name: {full_name}",
        f"Date of Birth: {student.date_of_birth or ''}",
        f"Gender: {student.gender}",
        f"Phone: {student.phone}",
        f"Email: {student.email}",
        f"Address: {student.address}",
        f"Branch: {student.branch.code} - {student.branch.name}",
        f"Admission Year: {student.admission_year}",
        f"Current Semester: {student.current_semester}",
        f"Status: {student.status}",
    ]

    for line in lines:
        pdf.drawString(50, y, line)
        y -= 25

    pdf.save()

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="application/pdf"
    )

    filename = (
        f"{student.admission_no}_my_profile.pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    return response
