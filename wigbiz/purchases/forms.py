from django import forms
from purchases.models import Purchase, PurchaseItem, PurchasePayment
from django.forms import inlineformset_factory


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = [
            "supplier",
            "invoice_number",
            "purchase_date",
        ]
        widgets = {
            "purchase_date": forms.DateInput(
                attrs={
                    "type": "date"
                }
            ),
        }

class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = [
            "product",
            "quantity",
            "cost_price",
        ]
    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity < 1:
            raise forms.ValidationError(
                "Quantity must be at least 1."
            )
        return quantity
    def clean_cost_price(self):
        cost_price = self.cleaned_data["cost_price"]
        if cost_price < 0:
            raise forms.ValidationError(
                "Cost price cannot be negative."
            )
        return cost_price

class PurchasePaymentForm(forms.ModelForm):
    def __init__(self, *args, purchase=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.purchase = purchase
    class Meta:
        model = PurchasePayment
        fields = [
            "amount",
            "payment_method",
            "reference",
        ]
    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError(
                "Payment amount must be greater than zero."
            )
        if self.purchase:
            if amount > self.purchase.balance:
                raise forms.ValidationError(
                    f"Payment cannot exceed the outstanding balance "
                    f"of {self.purchase.balance}."
                )
        return amount
PurchaseItemFormSet = inlineformset_factory(
    Purchase,
    PurchaseItem,
    form=PurchaseItemForm,
    extra=1,
    can_delete=True,
)
