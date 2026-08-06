from django import forms
from customers.models import Customer
from .models import Sale
from products.models import Product
from django.forms import formset_factory


class SaleForm(forms.Form):

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        required=False,
    )

    discount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        initial=0,
        required=False,
    )

    tax = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        initial=0,
        required=False,
    )

    payment_method = forms.ChoiceField(
        choices=Sale.PAYMENT_METHODS,
        required=False,
    )

    amount_paid = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        initial=0,
        required=False,
    )
class ProductSelect(forms.Select):

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex,
            attrs,
        )

        if value:

            try:
                product = Product.objects.get(
                    pk=value.value
                )

                option["attrs"]["data-price"] = str(
                    product.selling_price
                )

            except Product.DoesNotExist:
                pass

        return option   
class SaleItemForm(forms.Form):

    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(status=True),
                widget=ProductSelect(),

    )

    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
    )    
SaleItemFormSet = formset_factory(
    SaleItemForm,
    extra=1,
    can_delete=True,
)