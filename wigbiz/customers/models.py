from django.db import models

# Create your models here.
class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, blank=True)

    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    gender = models.CharField(max_length=10, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    loyalty_points = models.IntegerField(default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()