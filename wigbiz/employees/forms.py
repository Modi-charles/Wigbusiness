from django import forms
from .models import Employee


class EmployeeForm(forms.ModelForm):

    class Meta:
        model = Employee

        fields = [
            "user",
            "employee_number",
            "address",
            "position",
            "department",
            "salary",
            "hire_date",
            "status",
        ]

        widgets = {
            "hire_date": forms.DateInput(
                attrs={
                    "type": "date"
                }
            ),

            "address": forms.Textarea(
                attrs={
                    "rows": 3
                }
            ),

            "salary": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01"
                }
            ),
        }

    def clean_employee_number(self):
        employee_number = self.cleaned_data[
            "employee_number"
        ].strip()

        if not employee_number:
            raise forms.ValidationError(
                "Employee number is required."
            )

        return employee_number

    def clean_position(self):
        position = self.cleaned_data[
            "position"
        ].strip()

        if not position:
            raise forms.ValidationError(
                "Position is required."
            )

        return position

    def clean_salary(self):
        salary = self.cleaned_data["salary"]

        if salary < 0:
            raise forms.ValidationError(
                "Salary cannot be negative."
            )

        return salary