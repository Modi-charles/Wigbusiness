from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from products.models import Product
from customers.models import Customer
from sales.models import Sale
from inventory.models import Inventory
from django.utils import timezone
# Create your views here.
@login_required
def dashboard(request):
    # Total records
    total_products = Product.objects.count()

    total_customers = Customer.objects.count()


    # Today's sales
    today = timezone.now().date()

    today_sales = Sale.objects.filter(
        sale_date__date=today
    ).count()


    # Today's revenue
    today_revenue = Sale.objects.filter(
        sale_date__date=today
    ).values_list(
        "total_amount",
        flat=True
    )


    revenue_total = sum(today_revenue)


    # Low stock products
    low_stock = Inventory.objects.filter(
        quantity_available__lte=5
    ).count()


    # Recent sales
    recent_sales = Sale.objects.select_related(
        "customer"
    ).order_by(
        "-sale_date"
    )[:5]


    context = {

        "total_products": total_products,

        "total_customers": total_customers,

        "today_sales": today_sales,

        "today_revenue": revenue_total,

        "low_stock": low_stock,

        "recent_sales": recent_sales,

    }
    
    return render(request, "dashboard/home.html",context)
