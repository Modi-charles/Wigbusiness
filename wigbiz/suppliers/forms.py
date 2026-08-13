from django import forms

from .models import Supplier, SupplierPayment


class SupplierForm(forms.ModelForm):

    class Meta:
        model = Supplier

        fields = [
            "name",
            "company_name",
            "phone",
            "email",
            "address",
        ]

        widgets = {
            "address": forms.Textarea(
                attrs={
                    "rows": 3
                }
            ),
        }

    def clean_name(self):

        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Supplier name is required."
            )

        return name

    def clean_phone(self):

        phone = self.cleaned_data["phone"].strip()

        if not phone:
            raise forms.ValidationError(
                "Phone number is required."
            )

        return phone


class SupplierPaymentForm(forms.ModelForm):

    class Meta:
        model = SupplierPayment

        fields = [
            "amount",
            "payment_method",
            "reference",
            "notes",
        ]

        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "min": "0.01",
                    "step": "0.01"
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "rows": 3
                }
            ),
        }

    def clean_amount(self):

        amount = self.cleaned_data["amount"]

        if amount <= 0:
            raise forms.ValidationError(
                "Payment amount must be greater than zero."
            )

        return amount