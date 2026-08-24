# reports/utils.py
from decimal import Decimal
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

ZERO = Decimal("0.00")

TRUNC_MAP = {
    'daily': TruncDate,
    'weekly': TruncWeek,
    'monthly': TruncMonth,
}

VALID_PERIODS = ('daily', 'weekly', 'monthly')


def get_trunc_function(period_type, field_name):
    trunc_class = TRUNC_MAP.get(period_type, TruncDate)
    return trunc_class(field_name)


def get_period_type(request):
    """Read ?period= from the URL, default to 'daily', reject anything invalid."""
    period = request.GET.get('period', 'daily').strip().lower()
    return period if period in VALID_PERIODS else 'daily'


def get_gross_profit(sale_items_qs):
    """
    Given a SaleItem queryset (already filtered to whatever date range /
    status you want), return (revenue, cost_of_goods_sold, gross_profit).

    Single source of truth for gross profit — dashboard, profit_report,
    and financial_summary all call this instead of each computing their
    own version.
    """
    revenue_expr = ExpressionWrapper(
        F("quantity") * F("selling_price"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    cost_expr = ExpressionWrapper(
        F("quantity") * F("product__cost_price"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )

    totals = sale_items_qs.aggregate(
        revenue=Sum(revenue_expr),
        cost=Sum(cost_expr),
    )

    revenue = totals["revenue"] or ZERO
    cost = totals["cost"] or ZERO
    return revenue, cost, revenue - cost


def get_total_expenses(date_from=None, date_to=None):
    """
    Sum of all recorded expenses, optionally filtered to a date range.
    Expense model field is 'expense_date', not 'date'.
    """
    from expenses.models import Expense

    qs = Expense.objects.all()
    if date_from:
        qs = qs.filter(expense_date__gte=date_from)
    if date_to:
        qs = qs.filter(expense_date__lte=date_to)

    return qs.aggregate(total=Sum("amount"))["total"] or ZERO


def get_sales_breakdown(sales_qs, period_type):
    """Group an already-filtered Sale queryset by day/week/month."""
    trunc = get_trunc_function(period_type, 'sale_date')
    return (
        sales_qs
        .annotate(period=trunc)
        .values('period')
        .annotate(
            total_revenue=Sum('total_amount'),
            total_paid=Sum('paid_amount'),
            num_sales=Count('id'),
        )
        .order_by('period')
    )


def get_purchases_breakdown(purchases_qs, period_type):
    """Group an already-filtered Purchase queryset by day/week/month."""
    trunc = get_trunc_function(period_type, 'purchase_date')
    return (
        purchases_qs
        .annotate(period=trunc)
        .values('period')
        .annotate(
            total_amount=Sum('total_amount'),
            total_paid=Sum('paid_amount'),
            num_purchases=Count('id'),
        )
        .order_by('period')
    )


def get_expenses_breakdown(period_type, date_from=None, date_to=None):
    """
    Group Expense records by day/week/month, optionally date-filtered.
    Expense model field is 'expense_date', not 'date'.
    """
    from expenses.models import Expense
    trunc = get_trunc_function(period_type, 'expense_date')

    qs = Expense.objects.all()
    if date_from:
        qs = qs.filter(expense_date__gte=date_from)
    if date_to:
        qs = qs.filter(expense_date__lte=date_to)

    return (
        qs.annotate(period=trunc)
        .values('period')
        .annotate(total_expenses=Sum('amount'), num_entries=Count('id'))
        .order_by('period')
    )