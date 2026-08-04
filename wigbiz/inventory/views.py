from django.shortcuts import render
from .models import Inventory
from .models import Inventory, InventoryTransaction
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
# Create your views here.
@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")

def inventory_history(request):
    transactions = InventoryTransaction.objects.select_related(
        "product",
        "created_by"
    ).order_by("-created_at")

    context = {
        "transactions": transactions
    }

    return render(
        request,
        "inventory/inventory_history.html",
        context)

def view_inventory(request):
    search = request.GET.get("search", "")

    inventory = Inventory.objects.select_related("product").all()

    if search:
        inventory = inventory.filter(
            Q(product__name__icontains=search) |
            Q(product__product_code__icontains=search)
        )

    context = {
        "inventory": inventory,
        "search": search,
    }

    return render(request, "Inventory/view_inventory.html", context)

def update_inventory(request, id):
    inventory=get_object_or_404(Inventory, id=id)
    if request.method=="POST":
        quantity=int(request.POST.get("quantity"))
        inventory.quantity_available=quantity
        inventory.save()
        messages.success(request,"Inventory Updated Succesfully.")
        return redirect("view_invetory")
    return render(request, "Inventory/update_inventory.html",{"inventory":inventory})

def delete_inventory(request):
    return render(request, "Inventory/view_inventory.html")