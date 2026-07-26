from django.db import models
from accounts.models import User
# Create your models here.
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee_profile")
    employee_number = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    position = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    hire_date = models.DateField()
    status = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.position}"