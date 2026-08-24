from django import forms
from .models import Expense


class ExpenseForm(forms.ModelForm):

    class Meta:
        model = Expense

        fields = [
            "expense_number",
            "category",
            "description",
            "amount",
            "expense_date",
            "payment_method",
        ]

        widgets = {
            "expense_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. EXP-000001",
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Describe the expense",
                    "rows": 3,
                }
            ),

            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter amount",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),

            "expense_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "payment_method": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")

        if amount is not None and amount <= 0:
            raise forms.ValidationError(
                "Expense amount must be greater than zero."
            )

        return amount