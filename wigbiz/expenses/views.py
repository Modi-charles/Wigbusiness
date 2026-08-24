from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect

from .forms import ExpenseForm
from .models import Expense, ExpenseCategory
from .utils import generate_expense_number


@login_required
def create_expense(request):

    if request.method == "POST":
        form = ExpenseForm(request.POST)

        if form.is_valid():
            expense = form.save(commit=False)

            expense.expense_number = generate_expense_number()
            expense.created_by = request.user

            expense.save()

            messages.success(
                request,
                "Expense created successfully."
            )

            return redirect("expense_list")

    else:
        form = ExpenseForm()

    context = {
        "form": form
    }

    return render(
        request,
        "expenses/create_expense.html",
        context
    )


@login_required
def expense_list(request):

    expenses = Expense.objects.select_related(
        "category",
        "created_by"
    ).all()

    # =========================
    # SEARCH
    # =========================

    search = request.GET.get("search", "").strip()

    if search:
        expenses = expenses.filter(
            Q(expense_number__icontains=search) |
            Q(description__icontains=search) |
            Q(category__name__icontains=search)
        )

    # =========================
    # CATEGORY FILTER
    # =========================

    category_id = request.GET.get("category", "").strip()

    if category_id:
        expenses = expenses.filter(
            category_id=category_id
        )

    # =========================
    # PAYMENT METHOD FILTER
    # =========================

    payment_method = request.GET.get(
        "payment_method",
        ""
    ).strip()

    if payment_method:
        expenses = expenses.filter(
            payment_method=payment_method
        )

    # =========================
    # DATE FILTER
    # =========================

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    if date_from:
        expenses = expenses.filter(
            expense_date__gte=date_from
        )

    if date_to:
        expenses = expenses.filter(
            expense_date__lte=date_to
        )

    # =========================
    # ORDERING
    # =========================

    expenses = expenses.order_by(
        "-expense_date",
        "-created_at"
    )

    # =========================
    # TOTAL
    # =========================

    total_expenses = sum(
        expense.amount for expense in expenses
    )

    # =========================
    # PAGINATION
    # =========================

    paginator = Paginator(
        expenses,
        10
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    # =========================
    # CATEGORIES
    # =========================

    categories = ExpenseCategory.objects.filter(
        is_active=True
    ).order_by("name")

    context = {
        "expenses": page_obj,
        "page_obj": page_obj,
        "categories": categories,

        "search": search,
        "category_id": category_id,
        "payment_method": payment_method,
        "date_from": date_from,
        "date_to": date_to,

        "total_expenses": total_expenses,
    }

    return render(
        request,
        "expenses/expense_list.html",
        context
    )