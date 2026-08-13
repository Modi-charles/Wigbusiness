from django.contrib import admin
from .models import Employee
# Register your models here.
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):

    list_display = (
        "employee_number",
        "user",
        "position",
        "department",
        "salary",
        "hire_date",
        "status",
    )

    list_filter = (
        "status",
        "department",
        "position",
    )

    search_fields = (
        "employee_number",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )

    ordering = (
        "employee_number",
    )