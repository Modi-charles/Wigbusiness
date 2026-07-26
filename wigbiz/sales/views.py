from django.shortcuts import render
from django.contrib.auth.decorators import login_required
# Create your views here.
@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")
def add_sale(request):
    return render(request, "Sale/view_sales.html")
def view_sale(request):
    return render(request, "Sale/view_sales.html")
def update_sale(request):
    return render(request, "Sale/view_sales.html")
def delete_sale(request):
    return render(request, "Sale/view_sales.html")