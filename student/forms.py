from django import forms
from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student

        fields = [
            "admission_no",
            "roll_no",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "phone",
            "email",
            "address",
            "branch",
            "admission_year",
            "current_semester",
            "status",
        ]

        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date"}
            ),
            "address": forms.Textarea(
                attrs={"rows": 3}
            ),
        }