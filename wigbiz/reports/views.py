# reports/views.py
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.core.paginator import Paginator
from django.shortcuts import render

from sales.models import Sale, SaleItem
from purchases.models import Purchase, PurchaseItem
from inventory.models import Inventory
from suppliers.models import Supplier
from customers.models import Customer

from core.utils import parse_date_or_none, build_querystring
from .utils import (
    ZERO,
    get_gross_profit,
    get_total_expenses,
    get_period_type,
    get_trunc_function,
    get_sales_breakdown,
    get_purchases_breakdown,
    get_expenses_breakdown,
)


@login_required
def reports_dashboard(request):
    completed_sales = Sale.objects.filter(status=Sale.Status.COMPLETED)
    total_sales = completed_sales.aggregate(total=Sum("total_amount"))["total"] or ZERO
    total_sales_paid = completed_sales.aggregate(total=Sum("paid_amount"))["total"] or ZERO
    customer_outstanding = completed_sales.aggregate(total=Sum("balance"))["total"] or ZERO

    received_purchases = Purchase.objects.filter(status=Purchase.Status.RECEIVED)
    total_purchases = received_purchases.aggregate(total=Sum("total_amount"))["total"] or ZERO
    total_purchase_paid = received_purchases.aggregate(total=Sum("paid_amount"))["total"] or ZERO
    supplier_outstanding = received_purchases.aggregate(total=Sum("balance"))["total"] or ZERO

    sale_items = SaleItem.objects.filter(sale__status=Sale.Status.COMPLETED)
    revenue, cost_of_goods_sold, gross_profit = get_gross_profit(sale_items)
    total_expenses = get_total_expenses()
    net_profit = gross_profit - total_expenses

    inventory = Inventory.objects.select_related("product")
    total_products = inventory.count()
    total_stock = inventory.aggregate(total=Sum("quantity_available"))["total"] or 0
    stock_value = inventory.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("quantity_available") * F("product__cost_price"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
    )["total"] or ZERO

    total_customers = Customer.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()

    context = {
        "total_sales": total_sales,
        "total_sales_paid": total_sales_paid,
        "customer_outstanding": customer_outstanding,
        "total_purchases": total_purchases,
        "total_purchase_paid": total_purchase_paid,
        "supplier_outstanding": supplier_outstanding,
        "revenue": revenue,
        "cost_of_goods_sold": cost_of_goods_sold,
        "gross_profit": gross_profit,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "total_products": total_products,
        "total_stock": total_stock,
        "stock_value": stock_value,
        "total_customers": total_customers,
        "total_suppliers": total_suppliers,
    }
    return render(request, "reports/dashboard.html", context)


# =========================================================
# SALES REPORT
# =========================================================

@login_required
def sales_report(request):
    sales = Sale.objects.select_related("customer", "created_by").all()

    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    status = request.GET.get("status", "").strip()

    date_from = parse_date_or_none(date_from_raw)
    date_to = parse_date_or_none(date_to_raw)

    if date_from_raw and not date_from:
        error = "Invalid 'date from' — use YYYY-MM-DD."
    elif date_to_raw and not date_to:
        error = "Invalid 'date to' — use YYYY-MM-DD."
    else:
        error = None

    if date_from:
        sales = sales.filter(sale_date__date__gte=date_from)
    if date_to:
        sales = sales.filter(sale_date__date__lte=date_to)
    if status:
        sales = sales.filter(status=status)

    sales = sales.order_by("-sale_date")

    period_type = get_period_type(request)
    breakdown = get_sales_breakdown(sales, period_type)

    summary = sales.aggregate(
        total_sales=Count("id"),
        total_revenue=Sum("total_amount"),
        total_paid=Sum("paid_amount"),
        total_balance=Sum("balance"),
    )

    paginator = Paginator(sales, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "sales": page_obj,
        "breakdown": breakdown,
        "period_type": period_type,
        "querystring": build_querystring(request, exclude=["period"]),
        "page_querystring": build_querystring(request, exclude=["page"]),
        "date_from": date_from_raw,
        "date_to": date_to_raw,
        "status": status,
        "error": error,
        "total_sales": summary["total_sales"] or 0,
        "total_revenue": summary["total_revenue"] or ZERO,
        "total_paid": summary["total_paid"] or ZERO,
        "total_balance": summary["total_balance"] or ZERO,
    }
    return render(request, "reports/sales_report.html", context)


# =========================================================
# PURCHASE REPORT
# =========================================================

@login_required
def purchase_report(request):
    purchases = Purchase.objects.select_related("supplier", "created_by").all()

    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    status = request.GET.get("status", "").strip()
    payment_status = request.GET.get("payment_status", "").strip()

    date_from = parse_date_or_none(date_from_raw)
    date_to = parse_date_or_none(date_to_raw)

    if date_from:
        purchases = purchases.filter(purchase_date__date__gte=date_from)
    if date_to:
        purchases = purchases.filter(purchase_date__date__lte=date_to)
    if status:
        purchases = purchases.filter(status=status)
    if payment_status:
        purchases = purchases.filter(payment_status=payment_status)

    purchases = purchases.order_by("-purchase_date", "-id")

    period_type = get_period_type(request)
    breakdown = get_purchases_breakdown(purchases, period_type)

    summary = purchases.aggregate(
        total_purchases=Count("id"),
        total_amount=Sum("total_amount"),
        total_paid=Sum("paid_amount"),
        total_balance=Sum("balance"),
    )

    paginator = Paginator(purchases, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "purchases": page_obj,
        "breakdown": breakdown,
        "period_type": period_type,
        "querystring": build_querystring(request, exclude=["period"]),
        "page_querystring": build_querystring(request, exclude=["page"]),
        "date_from": date_from_raw,
        "date_to": date_to_raw,
        "status": status,
        "payment_status": payment_status,
        "total_purchases": summary["total_purchases"] or 0,
        "total_amount": summary["total_amount"] or ZERO,
        "total_paid": summary["total_paid"] or ZERO,
        "total_balance": summary["total_balance"] or ZERO,
    }
    return render(request, "reports/purchase_report.html", context)


# =========================================================
# INVENTORY REPORT
# =========================================================

@login_required
def inventory_report(request):
    inventory = Inventory.objects.select_related("product").order_by("product__name")

    total_products = inventory.count()
    total_available = inventory.aggregate(total=Sum("quantity_available"))["total"] or 0
    total_received = inventory.aggregate(total=Sum("quantity_received"))["total"] or 0
    total_sold = inventory.aggregate(total=Sum("quantity_sold"))["total"] or 0

    low_stock = inventory.filter(
        quantity_available__lte=F("product__reorder_level"),
        quantity_available__gt=0,
    ).count()
    out_of_stock = inventory.filter(quantity_available=0).count()

    paginator = Paginator(inventory, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "inventory": page_obj,
        "page_querystring": build_querystring(request, exclude=["page"]),
        "total_products": total_products,
        "total_available": total_available,
        "total_received": total_received,
        "total_sold": total_sold,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
    }
    return render(request, "reports/inventory_report.html", context)


# =========================================================
# SUPPLIER REPORT
# =========================================================

@login_required
def supplier_report(request):
    suppliers = Supplier.objects.all().order_by("name")

    total_suppliers = suppliers.count()
    active_suppliers = suppliers.filter(is_active=True).count()
    inactive_suppliers = suppliers.filter(is_active=False).count()
    total_outstanding = suppliers.aggregate(total=Sum("balance"))["total"] or ZERO

    paginator = Paginator(suppliers, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "suppliers": page_obj,
        "page_querystring": build_querystring(request, exclude=["page"]),
        "total_suppliers": total_suppliers,
        "active_suppliers": active_suppliers,
        "inactive_suppliers": inactive_suppliers,
        "total_outstanding": total_outstanding,
    }
    return render(request, "reports/supplier_report.html", context)


# =========================================================
# CUSTOMER REPORT
# =========================================================

@login_required
def customer_report(request):
    customers = Customer.objects.filter(is_active=True).order_by("first_name")

    total_customers = customers.count()
    total_customer_balance = customers.aggregate(total=Sum("balance"))["total"] or ZERO

    paginator = Paginator(customers, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "customers": page_obj,
        "page_querystring": build_querystring(request, exclude=["page"]),
        "total_customers": total_customers,
        "total_customer_balance": total_customer_balance,
    }
    return render(request, "reports/customer_report.html", context)


# =========================================================
# PROFIT REPORT
# =========================================================

@login_required
def profit_report(request):
    sale_items = SaleItem.objects.select_related("sale", "product").filter(
        sale__status=Sale.Status.COMPLETED
    )

    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    date_from = parse_date_or_none(date_from_raw)
    date_to = parse_date_or_none(date_to_raw)

    if date_from:
        sale_items = sale_items.filter(sale__sale_date__date__gte=date_from)
    if date_to:
        sale_items = sale_items.filter(sale__sale_date__date__lte=date_to)

    revenue, cost, gross_profit = get_gross_profit(sale_items)
    total_expenses = get_total_expenses(date_from, date_to)
    net_profit = gross_profit - total_expenses

    period_type = get_period_type(request)
    trunc = get_trunc_function(period_type, 'sale__sale_date')
    profit_breakdown = list(
        sale_items.annotate(period=trunc)
        .values('period')
        .annotate(
            revenue=Sum(
                ExpressionWrapper(
                    F('quantity') * F('selling_price'),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            cost=Sum(
                ExpressionWrapper(
                    F('quantity') * F('product__cost_price'),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
        )
        .order_by('period')
    )

    expenses_by_period = {
        row['period']: row['total_expenses']
        for row in get_expenses_breakdown(period_type, date_from, date_to)
    }
    for row in profit_breakdown:
        row['gross_profit'] = (row['revenue'] or ZERO) - (row['cost'] or ZERO)
        row['expenses'] = expenses_by_period.get(row['period'], ZERO)
        row['net_profit'] = row['gross_profit'] - row['expenses']

    context = {
        "sale_items": sale_items,
        "date_from": date_from_raw,
        "date_to": date_to_raw,
        "revenue": revenue,
        "cost": cost,
        "gross_profit": gross_profit,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "period_type": period_type,
        "profit_breakdown": profit_breakdown,
        "querystring": build_querystring(request, exclude=["period"]),
    }
    return render(request, "reports/profit_report.html", context)


# =========================================================
# FINANCIAL SUMMARY
# =========================================================

@login_required
def financial_summary(request):
    sales = Sale.objects.filter(status=Sale.Status.COMPLETED)
    purchases = Purchase.objects.filter(status=Purchase.Status.RECEIVED)

    total_sales = sales.aggregate(total=Sum("total_amount"))["total"] or ZERO
    total_sales_paid = sales.aggregate(total=Sum("paid_amount"))["total"] or ZERO
    customer_outstanding = sales.aggregate(total=Sum("balance"))["total"] or ZERO

    total_purchases = purchases.aggregate(total=Sum("total_amount"))["total"] or ZERO
    total_purchase_paid = purchases.aggregate(total=Sum("paid_amount"))["total"] or ZERO
    supplier_outstanding = purchases.aggregate(total=Sum("balance"))["total"] or ZERO

    sale_items = SaleItem.objects.filter(sale__status=Sale.Status.COMPLETED)
    revenue, cost_of_goods_sold, gross_profit = get_gross_profit(sale_items)
    total_expenses = get_total_expenses()
    net_profit = gross_profit - total_expenses

    context = {
        "total_sales": total_sales,
        "total_sales_paid": total_sales_paid,
        "customer_outstanding": customer_outstanding,
        "total_purchases": total_purchases,
        "total_purchase_paid": total_purchase_paid,
        "supplier_outstanding": supplier_outstanding,
        "revenue": revenue,
        "cost_of_goods_sold": cost_of_goods_sold,
        "gross_profit": gross_profit,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
    }
    return render(request, "reports/financial_summary.html", context)