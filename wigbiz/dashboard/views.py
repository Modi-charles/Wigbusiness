from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Sum, Avg, Count, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate
from django.utils import timezone
import datetime
from sales.models import Sale, SaleItem
from purchases.models import Purchase
from inventory.models import Inventory, InventoryTransaction
from reports.utils import ZERO, get_gross_profit, get_total_expenses


# ==========================================================
# NOTE ON DATES
#
# Sale.sale_date is a DateTimeField (date + time), NOT a
# DateField. Rules used throughout this file:
#   * Compare to a date  -> use  sale_date__date__gte / __lte / exact
#   * Group by day       -> use  TruncDate("sale_date")
# Without these, Django compares against midnight (00:00:00)
# and groups by the exact timestamp.
# ==========================================================

DEFAULT_MONTHLY_TARGET = 10_000_000


# ==========================================================
# HELPER: RESOLVE REPORT PERIOD
# ==========================================================

def _get_period_range(period):
    today = timezone.localdate()

    if period == "daily":
        return today, today

    if period == "weekly":
        start_of_week = today - datetime.timedelta(days=today.weekday())
        return start_of_week, today

    # monthly (default)
    start_of_month = today.replace(day=1)
    return start_of_month, today


# ==========================================================
# MAIN DASHBOARD
# ==========================================================

@login_required
def dashboard(request):
    if not request.user.role:
        return redirect("accounts:no_role")

    role = request.user.role.name

    # ======================================================
    # ADMINISTRATOR
    # ======================================================
    if role == "Administrator":
        from accounts.models import User, Role

        today = timezone.localdate()
        thirty_days_ago = today - datetime.timedelta(days=30)

        # USER & IDENTITY MANAGEMENT
        total_users = User.objects.count()
        active_users = User.objects.filter(
            last_login__date__gte=thirty_days_ago
        ).count()

        # PENDING APPROVALS
        pending_approvals_count = 0
        pending_users = User.objects.none()

        # SIGN-UP TREND (last 30 days)
        signups = (
            User.objects.filter(
                date_joined__date__gte=thirty_days_ago,
                date_joined__date__lte=today,
            )
            .annotate(day=TruncDate("date_joined"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        signup_by_day = {
            row["day"].isoformat(): row["count"] for row in signups
        }
        signup_labels = sorted(signup_by_day.keys())
        signup_counts = [signup_by_day[day] for day in signup_labels]

        # ROLE BREAKDOWN
        role_breakdown = (
            User.objects
            .values("role__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        role_labels = [row["role__name"] or "No Role" for row in role_breakdown]
        role_counts = [row["count"] for row in role_breakdown]

        context = {
            "total_users": total_users,
            "active_users": active_users,
            "pending_approvals_count": pending_approvals_count,
            "pending_users": pending_users,
            "signup_labels": signup_labels,
            "signup_counts": signup_counts,
            "role_labels": role_labels,
            "role_counts": role_counts,
        }

        return render(request, "administrator/dashboard.html", context)

    # ======================================================
    # MANAGER
    # ======================================================
    if role == "Manager":

        # REPORT PERIOD
        period = request.GET.get("period", "monthly")
        date_from, date_to = _get_period_range(period)

        # FIX: __date so the whole end day is included
        completed_sales = Sale.objects.filter(
            status=Sale.Status.COMPLETED,
            sale_date__date__gte=date_from,
            sale_date__date__lte=date_to,
        )

        # TOTAL SALES
        total_sales = completed_sales.aggregate(
            total=Sum("total_amount")
        )["total"] or ZERO

        # TRANSACTION COUNT
        transaction_count = completed_sales.count()

        # AVERAGE TRANSACTION
        average_transaction = completed_sales.aggregate(
            avg=Avg("total_amount")
        )["avg"] or ZERO

        # CUSTOMER OUTSTANDING
        customer_outstanding = completed_sales.aggregate(
            total=Sum("balance")
        )["total"] or ZERO

        # PROFIT
        # FIX: __date here too
        sale_items = SaleItem.objects.filter(
            sale__status=Sale.Status.COMPLETED,
            sale__sale_date__date__gte=date_from,
            sale__sale_date__date__lte=date_to,
        )

        revenue, cost_of_goods_sold, gross_profit = get_gross_profit(sale_items)
        total_expenses = get_total_expenses(date_from, date_to)
        net_profit = gross_profit - total_expenses

        # PROFIT MARGIN
        profit_margin = ZERO
        if revenue:
            profit_margin = round(
                (float(gross_profit) / float(revenue)) * 100, 2
            )

        # SALES TARGET
        sales_target = DEFAULT_MONTHLY_TARGET
        target_percentage = 0
        if sales_target:
            target_percentage = round(
                min((float(total_sales) / float(sales_target)) * 100, 100), 2
            )

        # INVENTORY
        inventory = Inventory.objects.select_related("product")
        total_products = inventory.count()
        total_stock = inventory.aggregate(
            total=Sum("quantity_available")
        )["total"] or 0

        low_stock_count = inventory.filter(
            quantity_available__lte=F("product__reorder_level"),
            quantity_available__gt=0,
        ).count()

        out_of_stock_count = inventory.filter(quantity_available=0).count()

        # PURCHASES
        # Assumes purchase_date is a DateField. If it is a DateTimeField,
        # change these two filters to purchase_date__date__gte / __lte.
        received_purchases = Purchase.objects.filter(
            status=Purchase.Status.RECEIVED,
            purchase_date__gte=date_from,
            purchase_date__lte=date_to,
        )

        total_purchases = received_purchases.aggregate(
            total=Sum("total_amount")
        )["total"] or ZERO

        # TOP SELLING PRODUCTS
        top_products = (
            sale_items
            .values("product__name")
            .annotate(
                total_quantity=Sum("quantity"),
                total_revenue=Sum(
                    ExpressionWrapper(
                        F("quantity") * F("selling_price"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
            )
            .order_by("-total_revenue")[:5]
        )

        # EMPLOYEE PERFORMANCE
        employee_sales = (
            completed_sales
            .exclude(created_by__isnull=True)
            .values("created_by__username")
            .annotate(
                transaction_count=Count("id"),
                total_sales=Sum("total_amount"),
            )
            .order_by("-total_sales")[:10]
        )

        context = {
            "period": period,

            # Sales
            "total_sales": total_sales,
            "transaction_count": transaction_count,
            "average_transaction": average_transaction,

            # Profit
            "revenue": revenue,
            "cost_of_goods_sold": cost_of_goods_sold,
            "gross_profit": gross_profit,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "profit_margin": profit_margin,

            # Target
            "sales_target": sales_target,
            "target_percentage": target_percentage,

            # Inventory
            "total_products": total_products,
            "total_stock": total_stock,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,

            # Purchases
            "total_purchases": total_purchases,

            # Customers
            "customer_outstanding": customer_outstanding,

            # Lists
            "top_products": top_products,
            "employee_sales": employee_sales,
        }

        return render(request, "manager/dashboard.html", context)

    # ======================================================
    # SALESPERSON
    # ======================================================
    if role == "Salesperson":

        today = timezone.localdate()

        # DATE FILTERS (strings from the query string, e.g. "2026-10-15")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        # BASE SALES QUERY
        sales = Sale.objects.filter(status=Sale.Status.COMPLETED)

        # FIX: __date compares only the date part of the datetime
        if date_from:
            sales = sales.filter(sale_date__date__gte=date_from)

        if date_to:
            sales = sales.filter(sale_date__date__lte=date_to)

        # TODAY'S SALES
        # FIX: was sale_date=today, which only matched exactly midnight
        today_sales = Sale.objects.filter(
            status=Sale.Status.COMPLETED,
            sale_date__date=today,
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        # SALES COUNT
        sales_count = sales.count()

        # CUSTOMER OUTSTANDING
        customer_outstanding = 0
        try:
            from customers.models import Customer

            customer_outstanding = Customer.objects.aggregate(
                total=Sum("balance")
            )["total"] or 0
        except Exception:
            customer_outstanding = 0

        # REVENUE
        revenue = sales.aggregate(total=Sum("total_amount"))["total"] or 0

        # REVENUE TARGET
        # The target is MONTHLY, so it must be compared with THIS MONTH's
        # revenue, not with "revenue" above (which follows the date filter
        # and, with no filter, covers every sale ever made).
        month_start, month_end = _get_period_range("monthly")

        month_revenue = Sale.objects.filter(
            status=Sale.Status.COMPLETED,
            sale_date__date__gte=month_start,
            sale_date__date__lte=month_end,
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        monthly_target = DEFAULT_MONTHLY_TARGET
        target_percentage = 0
        if monthly_target > 0:
            target_percentage = (float(month_revenue) / float(monthly_target)) * 100

        # AVERAGE SALE VALUE
        average_sale = sales.aggregate(average=Avg("total_amount"))["average"] or 0

        # SALESPERSON LEADERBOARD
        leaderboard = (
            sales
            .values("created_by", "created_by__username")
            .annotate(
                revenue=Sum("total_amount"),
                sales_count=Count("id"),
            )
            .order_by("-revenue")[:10]
        )

        # DAILY SALES TREND
        # FIX: sale_date is a DateTimeField, so we truncate it to a
        # date first (annotate), THEN group by that date (values).
        # Order matters: annotate -> values -> annotate.
        sales_trend = (
            sales
            .annotate(day=TruncDate("sale_date"))
            .values("day")
            .annotate(
                revenue=Sum("total_amount"),
                sales_count=Count("id"),
            )
            .order_by("day")
        )

        context = {
            "today_sales": today_sales,
            "sales_count": sales_count,
            "customer_outstanding": customer_outstanding,
            "revenue": revenue,
            "month_revenue": month_revenue,
            "monthly_target": monthly_target,
            "target_percentage": round(target_percentage, 2),
            "average_sale": average_sale,
            "leaderboard": leaderboard,
            "sales_trend": sales_trend,
            "date_from": date_from or "",
            "date_to": date_to or "",
        }

        return render(request, "salesperson/dashboard.html", context)

    # ======================================================
    # INVENTORY STAFF
    # ======================================================
    if role == "Inventory Staff":
        TREND_WINDOW_DAYS = 30
        SLOW_STOCK_DAYS = 60
        today = timezone.localdate()

        # DATE WINDOWS
        window_start = today - datetime.timedelta(days=TREND_WINDOW_DAYS)
        slow_stock_cutoff = today - datetime.timedelta(days=SLOW_STOCK_DAYS)

        # INVENTORY QUERY
        inventory = Inventory.objects.select_related("product")

        # CORE KPIs
        total_products = inventory.count()
        total_stock = inventory.aggregate(
            total=Sum("quantity_available")
        )["total"] or 0

        # INVENTORY VALUE
        inventory_value = inventory.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("quantity_available") * F("product__cost_price"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )["total"] or 0

        # LOW STOCK
        low_stock = inventory.filter(
            quantity_available__lte=F("product__reorder_level"),
            quantity_available__gt=0,
        ).count()

        # OUT OF STOCK
        out_of_stock = inventory.filter(quantity_available=0).count()

        # INVENTORY TURNS
        # InventoryTransaction.created_at is a DateTimeField,
        # so __date is correct here.
        period_cogs = (
            InventoryTransaction.objects
            .filter(
                transaction_type="SALE",
                created_at__date__gte=window_start,
                created_at__date__lte=today,
            )
            .aggregate(
                total=Sum(
                    ExpressionWrapper(
                        -F("quantity") * F("product__cost_price"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                )
            )["total"] or 0
        )

        inventory_turns = 0
        if inventory_value:
            inventory_turns = round(float(period_cogs) / float(inventory_value), 2)

        # DAYS OF SUPPLY
        period_units_sold = (
            InventoryTransaction.objects
            .filter(
                transaction_type="SALE",
                created_at__date__gte=window_start,
                created_at__date__lte=today,
            )
            .aggregate(total=Sum("quantity"))["total"] or 0
        )

        # Sale quantities are negative.
        period_units_sold = abs(period_units_sold)
        avg_daily_units_sold = period_units_sold / TREND_WINDOW_DAYS

        days_of_supply = None
        if avg_daily_units_sold > 0:
            days_of_supply = round(total_stock / avg_daily_units_sold, 1)

        # REORDER STATUS
        reorder_items = (
            inventory
            .filter(quantity_available__lte=F("product__reorder_level"))
            .select_related("product")
            .order_by("quantity_available")[:10]
        )

        # SLOW / AGED STOCK
        recently_sold_product_ids = (
            InventoryTransaction.objects
            .filter(
                transaction_type="SALE",
                created_at__date__gte=slow_stock_cutoff,
            )
            .values_list("product_id", flat=True)
            .distinct()
        )

        slow_stock_items = (
            inventory
            .filter(quantity_available__gt=0)
            .exclude(product_id__in=recently_sold_product_ids)
            .select_related("product")
            .order_by("-quantity_available")[:10]
        )

        # STOCK MOVEMENT TRENDS
        movements = (
            InventoryTransaction.objects
            .filter(
                created_at__date__gte=window_start,
                created_at__date__lte=today,
                transaction_type__in=["PURCHASE", "SALE"],
            )
            .annotate(day=TruncDate("created_at"))
            .values("day", "transaction_type")
            .annotate(total_quantity=Sum("quantity"))
            .order_by("day")
        )

        # RESHAPE MOVEMENT DATA
        trend_by_day = {}

        for row in movements:
            day_key = row["day"].isoformat()
            trend_by_day.setdefault(day_key, {"received": 0, "sold": 0})

            if row["transaction_type"] == "PURCHASE":
                trend_by_day[day_key]["received"] += row["total_quantity"]
            else:
                # Sale quantity is negative; show it as positive.
                trend_by_day[day_key]["sold"] += abs(row["total_quantity"])

        # CHART DATA
        movement_labels = sorted(trend_by_day.keys())
        movement_received = [trend_by_day[d]["received"] for d in movement_labels]
        movement_sold = [trend_by_day[d]["sold"] for d in movement_labels]

        context = {
            # Core KPIs
            "total_products": total_products,
            "total_stock": total_stock,
            "inventory_value": inventory_value,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,

            # Inventory analysis
            "inventory_turns": inventory_turns,
            "days_of_supply": days_of_supply,
            "trend_window_days": TREND_WINDOW_DAYS,

            # Reorder
            "reorder_items": reorder_items,

            # Slow stock
            "slow_stock_items": slow_stock_items,
            "slow_stock_days": SLOW_STOCK_DAYS,

            # Movement chart
            "movement_labels": movement_labels,
            "movement_received": movement_received,
            "movement_sold": movement_sold,
        }

        return render(request, "inventorystaff/dashboard.html", context)

    # ======================================================
    # ACCOUNTANT
    # ======================================================
    if role == "Accountant":

        # REPORT PERIOD
        period = request.GET.get("period", "monthly")
        date_from, date_to = _get_period_range(period)

        # SALES & REVENUE
        # FIX: __date so the whole end day is included
        completed_sales = Sale.objects.filter(
            status=Sale.Status.COMPLETED,
            sale_date__date__gte=date_from,
            sale_date__date__lte=date_to,
        )

        total_sales = completed_sales.aggregate(
            total=Sum("total_amount")
        )["total"] or ZERO

        # PROFIT & LOSS
        sale_items = SaleItem.objects.filter(
            sale__status=Sale.Status.COMPLETED,
            sale__sale_date__date__gte=date_from,
            sale__sale_date__date__lte=date_to,
        )

        revenue, cost_of_goods_sold, gross_profit = get_gross_profit(sale_items)
        total_operating_expenses = get_total_expenses(date_from, date_to)
        net_income = gross_profit - total_operating_expenses

        # MARGINS
        gross_profit_margin = ZERO
        net_profit_margin = ZERO

        if revenue:
            gross_profit_margin = round(
                (float(gross_profit) / float(revenue)) * 100, 2
            )
            net_profit_margin = round(
                (float(net_income) / float(revenue)) * 100, 2
            )

        # PURCHASES
        # Assumes purchase_date is a DateField. If it is a DateTimeField,
        # change these two filters to purchase_date__date__gte / __lte.
        received_purchases = Purchase.objects.filter(
            status=Purchase.Status.RECEIVED,
            purchase_date__gte=date_from,
            purchase_date__lte=date_to,
        )

        total_purchases = received_purchases.aggregate(
            total=Sum("total_amount")
        )["total"] or ZERO

        # RECEIVABLES (A/R)
        customer_outstanding = ZERO
        try:
            from customers.models import Customer

            customer_outstanding = Customer.objects.aggregate(
                total=Sum("balance")
            )["total"] or ZERO
        except Exception:
            customer_outstanding = ZERO

        # PAYABLES (A/P)
        # Assumes Purchase has a `balance` field. Falls back to 0.
        supplier_outstanding = ZERO
        try:
            supplier_outstanding = Purchase.objects.aggregate(
                total=Sum("balance")
            )["total"] or ZERO
        except Exception:
            supplier_outstanding = ZERO

        context = {
            "period": period,

            # Core financial metrics
            "total_sales": total_sales,
            "total_purchases": total_purchases,
            "revenue": revenue,
            "total_cogs": cost_of_goods_sold,  # renamed to match template
            "gross_profit": gross_profit,
            "total_operating_expenses": total_operating_expenses,
            "net_income": net_income,

            # Margins
            "gross_profit_margin": gross_profit_margin,
            "net_profit_margin": net_profit_margin,

            # Receivables & payables
            "customer_outstanding": customer_outstanding,
            "supplier_outstanding": supplier_outstanding,
        }

        return render(request, "accountant/dashboard.html", context)

    # ======================================================
    # UNKNOWN ROLE
    # ======================================================
    return redirect("accounts:no_role")