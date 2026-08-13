from django import forms
from .models import Customer

class CustomerForm(forms.ModelForm):
    class Meta:
        model=Customer
        fields=[
            "first_name",
            "last_name",
            "phone",
            "email",
            "address",
            "gender",
            "date_of_birth"
        ]
    widgets = {
            "date_of_birth": forms.DateInput(
                attrs={
                    "type": "date"
                }
            ),

            "address": forms.Textarea(
                attrs={
                    "rows": 3
                }
            ),
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()

        if not phone:
            raise forms.ValidationError(
                "Phone number is required."
            )

        return phone    