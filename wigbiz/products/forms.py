from django import forms
from .models import Product, Brand, Category

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
                attrs={"rows":3}
            ),
            "length": forms.NumberInput(),
            "cost_price": forms.NumberInput(
                attrs={
                    "step":"0.01"
                }
            ),
            "selling_price": forms.NumberInput(
                attrs={"step":"0.01"}
            ),

        }
class CategoryAndBrandForm(forms.Form):
    category_name = forms.CharField(max_length=100, label="Category Name")
    category_description = forms.CharField(widget=forms.Textarea, required=False, label="Category Description")
    brand_name = forms.CharField(max_length=100, label="Brand Name")
    brand_description = forms.CharField(widget=forms.Textarea, required=False, label="Brand Description")
    def save(self):
        cleaned_data = self.cleaned_data
        category = Category.objects.create(
            name=cleaned_data['category_name'],
            description=cleaned_data['category_description']
        )
        brand = Brand.objects.create(
            name=cleaned_data['brand_name'],
            description=cleaned_data['brand_description']
        )
        
        return category, brand
