from django.shortcuts import render

from django.contrib.auth.decorators import login_required
# Create your views here.
@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")
def add_inventory(request):
    return render(request, "Inventory/view_inventory.html")
def view_inventory(request):
    return render(request, "Inventory/view_inventory.html")
def update_inventory(request):
    return render(request, "Inventory/view_inventory.html")
def delete_inventory(request):
    return render(request, "Inventory/view_inventory.html")