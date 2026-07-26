from django.db import models

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")

    product_code = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    hair_type = models.CharField(max_length=50, blank=True)   
    texture = models.CharField(max_length=50, blank=True)     
    length = models.IntegerField(null=True, blank=True)       
    color = models.CharField(max_length=50, blank=True)

    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    reorder_level = models.IntegerField(default=5)

    image = models.ImageField(upload_to="products/", blank=True, null=True)
    status = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name