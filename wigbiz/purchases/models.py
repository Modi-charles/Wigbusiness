from django.db import models
from suppliers.models import Supplier
from products.models import Product
from accounts.models import User

# Create your models here.
class Purchase(models.Model):
    PAYMENT_STATUS = (
        ("PAID", "Paid"),
        ("PARTIAL", "Partial"),
        ("UNPAID", "Unpaid"),
    )

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchases")
    invoice_number = models.CharField(max_length=50, unique=True)
    purchase_date = models.DateField()

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default="UNPAID")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    quantity = models.IntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.cost_price