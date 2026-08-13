from django.db import models
from suppliers.models import Supplier
from products.models import Product
from accounts.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

# Create your models here.
class Purchase(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RECEIVED = "RECEIVED", "Received"
        CANCELLED = "CANCELLED", "Cancelled"

    PAYMENT_STATUS = (
        ("PAID", "Paid"),
        ("PARTIAL", "Partial"),
        ("UNPAID", "Unpaid"),
    )
    supplier = models.ForeignKey(Supplier,on_delete=models.PROTECT,related_name="purchases")
    invoice_number = models.CharField(max_length=50,unique=True)
    purchase_date = models.DateField()
    status = models.CharField(max_length=20,choices=Status.choices,default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    paid_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    balance = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    payment_status = models.CharField(max_length=10,choices=PAYMENT_STATUS,default="UNPAID")
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def update_payment_status(self):
            total_paid = sum(
                payment.amount
                for payment in self.payments.all()
            )
            self.paid_amount = total_paid
            self.balance = self.total_amount - total_paid
            if total_paid <= 0:
                self.payment_status = "UNPAID"
            elif total_paid >= self.total_amount:
                self.payment_status = "PAID"
                self.balance = 0
            else:
                self.payment_status = "PARTIAL"
            self.save(
                update_fields=[
                    "paid_amount",
                    "balance",
                    "payment_status",
                ]
            )
    def __str__(self):
        return self.invoice_number


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    quantity = models.IntegerField( validators=[MinValueValidator(1)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2,  validators=[MinValueValidator(0)])

    @property
    def subtotal(self):
        return self.quantity * self.cost_price
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purchase", "product"],
                name="unique_product_per_purchase"
            )]
class PurchasePayment(models.Model):

    PAYMENT_METHODS = (
        ("CASH", "Cash"),
        ("MOBILE_MONEY", "Mobile Money"),
        ("CARD", "Card"),
        ("BANK", "Bank"),
    )

    purchase = models.ForeignKey(Purchase,on_delete=models.PROTECT,related_name="payments" )
    amount = models.DecimalField(max_digits=12,decimal_places=2)
    payment_method = models.CharField(max_length=20,choices=PAYMENT_METHODS)
    payment_date = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100,blank=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    def clean(self):
        if self.amount <= 0:
            raise ValidationError(
                "Payment amount must be greater than zero."
            )
        if self.purchase:
            existing_paid = sum(
                payment.amount
                for payment in self.purchase.payments.exclude(
                    pk=self.pk
                )
            )
            if existing_paid + self.amount > self.purchase.total_amount:
                raise ValidationError(
                    "Payment cannot exceed the purchase total."
                )
    def __str__(self):
        return f"{self.purchase.invoice_number} - {self.amount}"