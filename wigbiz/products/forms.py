from django import forms
from .models import Product


class ProductForm(forms.ModelForm):

    class Meta:

        model = Product

        fields = [
            "category",
            "brand",
            "product_code",
            "barcode",
            "name",
            "description",
            "hair_type",
            "texture",
            "length",
            "color",
            "cost_price",
            "selling_price",
            "reorder_level",
            "image",
            "status",
        ]


        widgets = {

            "description": forms.Textarea(
                attrs={
                    "rows":3
                }
            ),

            "length": forms.NumberInput(),

            "cost_price": forms.NumberInput(
                attrs={
                    "step":"0.01"
                }
            ),

            "selling_price": forms.NumberInput(
                attrs={
                    "step":"0.01"
                }
            ),

        }