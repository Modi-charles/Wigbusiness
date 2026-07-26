from django.shortcuts import render
from django.contrib.auth.decorators import login_required
# Create your views here.
@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")
def add_employee(request):
    return render(request, "Employee/view_employees.html")
def view_employee(request):
    return render(request, "Employee/view_employees.html")
def update_employee(request):
    return render(request, "Employee/view_employees.html")
def delete_employee(request):
    return render(request, "Employee/view_employees.html")