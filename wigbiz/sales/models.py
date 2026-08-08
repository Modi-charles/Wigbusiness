from django.db import models
from customers.models import Customer
from products.models import Product
from accounts.models import User
from django.core.validators import MinValueValidator

# Create your models here.
class Sale(models.Model):
    PAYMENT_METHODS = (
        ("CASH", "Cash"),
        ("MOBILE_MONEY", "Mobile Money"),
        ("CARD", "Card"),
        ("BANK", "Bank"),
    )
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REFUNDED = 'REFUNDED', 'Refunded'
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="sales"
        )
    invoice_number = models.CharField(max_length=50, unique=True)
    sale_date = models.DateTimeField(auto_now_add=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="CASH")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sales_created")

    def __str__(self):
        return self.invoice_number


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)])
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    @property
    def line_total(self):
        return self.quantity * self.selling_price
    def __str__(self):
        return f"{self.product}*{self.quantity}"



class Payment(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Sale.PAYMENT_METHODS)
    transaction_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
class InvoiceSequence(models.Model):
    name = models.CharField(max_length=50, unique=True)
    last_number = models.PositiveIntegerField(default=0)
    def __str__(self):
        return f"{self.name}:{self.last_number}"
    
class SaleReturn(models.Model):

    class Status(models.TextChoices):

        PENDING = "PENDING", "Pending"

        COMPLETED = "COMPLETED", "Completed"

        CANCELLED = "CANCELLED", "Cancelled"


    sale = models.ForeignKey(
        Sale,
        on_delete=models.PROTECT,
        related_name="returns",
    )

    return_number = models.CharField(
        max_length=50,
        unique=True,
    )

    reason = models.TextField(
        blank=True,
    )

    total_refund = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_returns",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):

        return self.return_number
class SaleReturnItem(models.Model):

    sale_return = models.ForeignKey(
        SaleReturn,
        on_delete=models.CASCADE,
        related_name="items",
    )

    sale_item = models.ForeignKey(
        SaleItem,
        on_delete=models.PROTECT,
        related_name="return_items",
    )

    quantity = models.PositiveIntegerField()

    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    def __str__(self):

        return (
            f"{self.sale_return.return_number} - "
            f"{self.sale_item.product.name}"
        )
class Refund(models.Model):

    class Status(models.TextChoices):

        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    sale_return = models.OneToOneField(
        SaleReturn,
        on_delete=models.PROTECT,
        related_name="refund",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=Sale.PAYMENT_METHODS,
    )

    refunded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="refunds_processed",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):

        return (
            f"Refund for "
            f"{self.sale_return.return_number}"
        )    