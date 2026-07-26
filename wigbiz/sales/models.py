from django.db import models
from customers.models import Customer
from products.models import Product
from accounts.models import User

# Create your models here.
class Sale(models.Model):
    PAYMENT_METHODS = (
        ("CASH", "Cash"),
        ("MOBILE_MONEY", "Mobile Money"),
        ("CARD", "Card"),
        ("BANK", "Bank"),
    )

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    invoice_number = models.CharField(max_length=50, unique=True)
    sale_date = models.DateTimeField(auto_now_add=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="CASH")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.invoice_number


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.selling_price


class Payment(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Sale.PAYMENT_METHODS)
    transaction_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)