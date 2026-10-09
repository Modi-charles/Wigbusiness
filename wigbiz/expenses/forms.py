from django import forms
from .models import Expense, ExpenseCategory


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



class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ("name", "description", "is_active")
        labels = {"is_active": "Category is active"}
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Rent, Transport, Utilities"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        # Case-insensitive duplicate check (the model's unique=True is case-sensitive)
        duplicates = ExpenseCategory.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("A category with this name already exists.")
        return name