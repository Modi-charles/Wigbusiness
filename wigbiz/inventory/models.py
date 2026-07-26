from django.db import models
from products.models import Product
from accounts.models import User
# Create your models here.
class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    quantity_available = models.IntegerField(default=0)
    quantity_sold = models.IntegerField(default=0)
    quantity_received = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} stock"


class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = (
        ("PURCHASE", "Purchase"),
        ("SALE", "Sale"),
        ("RETURN", "Return"),
        ("DAMAGE", "Damage"),
        ("ADJUSTMENT", "Adjustment"),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()  # positive for in, negative for out
    reference_id = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)