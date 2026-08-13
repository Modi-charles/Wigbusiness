from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import (
    Sum,
    Count,
    F,
    DecimalField,
    ExpressionWrapper,
)
from django.shortcuts import render

from sales.models import Sale, SaleItem
from purchases.models import Purchase, PurchaseItem
from inventory.models import Inventory
from suppliers.models import Supplier
from customers.models import Customer


ZERO = Decimal("0.00")


@login_required
def reports_dashboard(request):

    # =========================
    # SALES
    # =========================

    completed_sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED
    )

    total_sales = completed_sales.aggregate(
        total=Sum("total_amount")
    )["total"] or ZERO

    total_sales_paid = completed_sales.aggregate(
        total=Sum("paid_amount")
    )["total"] or ZERO

    customer_outstanding = completed_sales.aggregate(
        total=Sum("balance")
    )["total"] or ZERO


    # =========================
    # PURCHASES
    # =========================

    received_purchases = Purchase.objects.filter(
        status=Purchase.Status.RECEIVED
    )

    total_purchases = received_purchases.aggregate(
        total=Sum("total_amount")
    )["total"] or ZERO

    total_purchase_paid = received_purchases.aggregate(
        total=Sum("paid_amount")
    )["total"] or ZERO

    supplier_outstanding = received_purchases.aggregate(
        total=Sum("balance")
    )["total"] or ZERO


    # =========================
    # PROFIT
    # =========================

    sale_items = SaleItem.objects.filter(
        sale__status=Sale.Status.COMPLETED
    )

    revenue_expression = ExpressionWrapper(
        F("quantity") * F("selling_price"),
        output_field=DecimalField(
            max_digits=14,
            decimal_places=2
        )
    )

    cost_expression = ExpressionWrapper(
        F("quantity") * F("product__cost_price"),
        output_field=DecimalField(
            max_digits=14,
            decimal_places=2
        )
    )

    profit_totals = sale_items.aggregate(

        revenue=Sum(
            revenue_expression
        ),

        cost=Sum(
            cost_expression
        ),
    )

    revenue = profit_totals["revenue"] or ZERO

    cost_of_goods_sold = (
        profit_totals["cost"] or ZERO
    )

    gross_profit = (
        revenue - cost_of_goods_sold
    )


    # =========================
    # INVENTORY
    # =========================

    inventory = Inventory.objects.select_related(
        "product"
    )

    total_products = inventory.count()

    total_stock = inventory.aggregate(
        total=Sum("quantity_available")
    )["total"] or 0


    # Calculate current stock value
    stock_value = ZERO

    for item in inventory:

        stock_value += (
            item.quantity_available
            * item.product.cost_price
        )


    # =========================
    # CUSTOMERS
    # =========================

    total_customers = Customer.objects.filter(
        is_active=True
    ).count()


    # =========================
    # SUPPLIERS
    # =========================

    total_suppliers = Supplier.objects.filter(
        is_active=True
    ).count()


    context = {

        # Sales
        "total_sales": total_sales,
        "total_sales_paid": total_sales_paid,
        "customer_outstanding": customer_outstanding,

        # Purchases
        "total_purchases": total_purchases,
        "total_purchase_paid": total_purchase_paid,
        "supplier_outstanding": supplier_outstanding,

        # Profit
        "revenue": revenue,
        "cost_of_goods_sold": cost_of_goods_sold,
        "gross_profit": gross_profit,

        # Inventory
        "total_products": total_products,
        "total_stock": total_stock,
        "stock_value": stock_value,

        # Customers / Suppliers
        "total_customers": total_customers,
        "total_suppliers": total_suppliers,
    }

    return render(
        request,
        "reports/dashboard.html",
        context
    )


# =========================================================
# SALES REPORT
# =========================================================

@login_required
def sales_report(request):

    sales = Sale.objects.select_related(
        "customer",
        "created_by",
    ).all()

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    ).strip()

    if date_from:
        sales = sales.filter(
            sale_date__date__gte=date_from
        )

    if date_to:
        sales = sales.filter(
            sale_date__date__lte=date_to
        )

    if status:
        sales = sales.filter(
            status=status
        )

    sales = sales.order_by(
        "-sale_date"
    )

    summary = sales.aggregate(

        total_sales=Count("id"),

        total_revenue=Sum(
            "total_amount"
        ),

        total_paid=Sum(
            "paid_amount"
        ),

        total_balance=Sum(
            "balance"
        ),
    )

    context = {

        "sales": sales,

        "date_from": date_from,

        "date_to": date_to,

        "status": status,

        "total_sales":
            summary["total_sales"] or 0,

        "total_revenue":
            summary["total_revenue"] or ZERO,

        "total_paid":
            summary["total_paid"] or ZERO,

        "total_balance":
            summary["total_balance"] or ZERO,
    }

    return render(
        request,
        "reports/sales_report.html",
        context
    )


# =========================================================
# PURCHASE REPORT
# =========================================================

@login_required
def purchase_report(request):

    purchases = Purchase.objects.select_related(
        "supplier",
        "created_by",
    ).all()

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    ).strip()

    payment_status = request.GET.get(
        "payment_status",
        ""
    ).strip()

    if date_from:
        purchases = purchases.filter(
            purchase_date__date__gte=date_from
        )

    if date_to:
        purchases = purchases.filter(
            purchase_date__date__lte=date_to
        )

    if status:
        purchases = purchases.filter(
            status=status
        )

    if payment_status:
        purchases = purchases.filter(
            payment_status=payment_status
        )

    purchases = purchases.order_by(
        "-purchase_date",
        "-id"
    )

    summary = purchases.aggregate(

        total_purchases=Count("id"),

        total_amount=Sum(
            "total_amount"
        ),

        total_paid=Sum(
            "paid_amount"
        ),

        total_balance=Sum(
            "balance"
        ),
    )

    context = {

        "purchases": purchases,

        "date_from": date_from,

        "date_to": date_to,

        "status": status,

        "payment_status": payment_status,

        "total_purchases":
            summary["total_purchases"] or 0,

        "total_amount":
            summary["total_amount"] or ZERO,

        "total_paid":
            summary["total_paid"] or ZERO,

        "total_balance":
            summary["total_balance"] or ZERO,
    }

    return render(
        request,
        "reports/purchase_report.html",
        context
    )


# =========================================================
# INVENTORY REPORT
# =========================================================

@login_required
def inventory_report(request):

    inventory = Inventory.objects.select_related(
        "product"
    ).order_by(
        "product__name"
    )

    total_products = inventory.count()

    total_available = inventory.aggregate(
        total=Sum("quantity_available")
    )["total"] or 0

    total_received = inventory.aggregate(
        total=Sum("quantity_received")
    )["total"] or 0

    total_sold = inventory.aggregate(
        total=Sum("quantity_sold")
    )["total"] or 0

    low_stock = inventory.filter(
        quantity_available__lte=F(
            "product__reorder_level"
        ),
        quantity_available__gt=0,
    ).count()

    out_of_stock = inventory.filter(
        quantity_available=0
    ).count()

    context = {

        "inventory": inventory,

        "total_products": total_products,

        "total_available": total_available,

        "total_received": total_received,

        "total_sold": total_sold,

        "low_stock": low_stock,

        "out_of_stock": out_of_stock,
    }

    return render(
        request,
        "reports/inventory_report.html",
        context
    )


# =========================================================
# SUPPLIER REPORT
# =========================================================

@login_required
def supplier_report(request):

    suppliers = Supplier.objects.all().order_by(
        "name"
    )

    total_suppliers = suppliers.count()

    active_suppliers = suppliers.filter(
        is_active=True
    ).count()

    inactive_suppliers = suppliers.filter(
        is_active=False
    ).count()

    total_outstanding = suppliers.aggregate(
        total=Sum("balance")
    )["total"] or ZERO

    context = {

        "suppliers": suppliers,

        "total_suppliers":
            total_suppliers,

        "active_suppliers":
            active_suppliers,

        "inactive_suppliers":
            inactive_suppliers,

        "total_outstanding":
            total_outstanding,
    }

    return render(
        request,
        "reports/supplier_report.html",
        context
    )


# =========================================================
# CUSTOMER REPORT
# =========================================================

@login_required
def customer_report(request):

    customers = Customer.objects.filter(
        is_active=True
    ).order_by(
        "first_name"
    )

    total_customers = customers.count()

    total_customer_balance = customers.aggregate(
        total=Sum("balance")
    )["total"] or ZERO

    context = {

        "customers": customers,

        "total_customers":
            total_customers,

        "total_customer_balance":
            total_customer_balance,
    }

    return render(
        request,
        "reports/customer_report.html",
        context
    )


# =========================================================
# PROFIT REPORT
# =========================================================

@login_required
def profit_report(request):

    sale_items = SaleItem.objects.select_related(
        "sale",
        "product",
    ).filter(
        sale__status=Sale.Status.COMPLETED
    )

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    if date_from:
        sale_items = sale_items.filter(
            sale__sale_date__date__gte=date_from
        )

    if date_to:
        sale_items = sale_items.filter(
            sale__sale_date__date__lte=date_to
        )

    revenue_expression = ExpressionWrapper(
        F("quantity") * F("selling_price"),
        output_field=DecimalField(
            max_digits=14,
            decimal_places=2
        )
    )

    cost_expression = ExpressionWrapper(
        F("quantity") * F("product__cost_price"),
        output_field=DecimalField(
            max_digits=14,
            decimal_places=2
        )
    )

    totals = sale_items.aggregate(
        revenue=Sum(revenue_expression),
        cost=Sum(cost_expression),
    )

    revenue = totals["revenue"] or ZERO

    cost = totals["cost"] or ZERO

    gross_profit = revenue - cost

    context = {
        "sale_items": sale_items,
        "date_from": date_from,
        "date_to": date_to,
        "revenue": revenue,
        "cost": cost,
        "gross_profit": gross_profit,
    }

    return render(
        request,
        "reports/profit_report.html",
        context
    )


# =========================================================
# FINANCIAL SUMMARY
# =========================================================

@login_required
def financial_summary(request):

    sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED
    )

    purchases = Purchase.objects.filter(
        status=Purchase.Status.RECEIVED
    )

    total_sales = sales.aggregate(
        total=Sum("total_amount")
    )["total"] or ZERO

    total_sales_paid = sales.aggregate(
        total=Sum("paid_amount")
    )["total"] or ZERO

    customer_outstanding = sales.aggregate(
        total=Sum("balance")
    )["total"] or ZERO

    total_purchases = purchases.aggregate(
        total=Sum("total_amount")
    )["total"] or ZERO

    total_purchase_paid = purchases.aggregate(
        total=Sum("paid_amount")
    )["total"] or ZERO

    supplier_outstanding = purchases.aggregate(
        total=Sum("balance")
    )["total"] or ZERO

    gross_profit = (
        total_sales - total_purchases
    )

    context = {

        "total_sales":
            total_sales,

        "total_sales_paid":
            total_sales_paid,

        "customer_outstanding":
            customer_outstanding,

        "total_purchases":
            total_purchases,

        "total_purchase_paid":
            total_purchase_paid,

        "supplier_outstanding":
            supplier_outstanding,

        "gross_profit":
            gross_profit,
    }

    return render(
        request,
        "reports/financial_summary.html",
        context
    )