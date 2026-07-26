from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    @property
    def role_name(self):
        return self.role.name if self.role else None