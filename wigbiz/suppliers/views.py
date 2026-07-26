from django.shortcuts import render
from django.contrib.auth.decorators import login_required
# Create your views here.
@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")
def add_supplier(request):
    return render(request, "Supplier/view_suppliers.html")
def view_supplier(request):
    return render(request, "Supplier/view_suppliers.html")
def update_supplier(request):
    return render(request, "Supplier/view_suppliers.html")
def delete_supplier(request):
    return render(request, "Supplier/view_suppliers.html")