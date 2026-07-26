from django.shortcuts import render

from django.contrib.auth.decorators import login_required
# Create your views here.
@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")
def add_product(request):
    return render(request, "Product/view_products.html")
def view_product(request):
    return render(request, "Product/view_products.html")
def update_product(request):
    return render(request, "Product/view_products.html")
def delete_product(request):
    return render(request, "Product/view_products.html")