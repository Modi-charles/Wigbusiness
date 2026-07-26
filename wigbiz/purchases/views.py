from django.shortcuts import render

from django.contrib.auth.decorators import login_required
# Create your views here.
@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")
def add_purchase(request):
    return render(request, "Purchase/view_purchases.html")
def view_purchase(request):
    return render(request, "Purchase/view_purchases.html")
def update_purchase(request):
    return render(request, "Purchase/view_purchases.html")
def delete_purchase(request):
    return render(request, "Purchase/view_purchases.html")