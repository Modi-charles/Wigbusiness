from django.db import models
from accounts.models import User


class Employee(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee_profile"
    )

    employee_number = models.CharField(
        max_length=50,
        unique=True
    )

    address = models.TextField(
        blank=True
    )

    position = models.CharField(
        max_length=100
    )

    department = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    hire_date = models.DateField()

    status = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.position}"