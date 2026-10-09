from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect
from django.db.models import Count, Q
from .forms import ExpenseForm, ExpenseCategoryForm
from .models import Expense, ExpenseCategory
from .utils import generate_expense_number
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.db import transaction



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

            return redirect("expenses:expense_list")

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


NAME_MAX = ExpenseCategory._meta.get_field("name").max_length


@login_required
def category_list(request):
    query = request.GET.get("q", "").strip()
    categories = ExpenseCategory.objects.annotate(
        expense_count=Count("expenses")
    ).order_by("name")

    if query:
        categories = categories.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    page_obj = Paginator(categories, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "expenses/category_list.html",
        {"page_obj": page_obj, "query": query},
    )


@login_required
def category_create(request):
    """Add one or several categories in a single submission."""
    rows = [{"name": "", "description": ""} for _ in range(3)]

    if request.method == "POST":
        names = request.POST.getlist("name")
        descriptions = request.POST.getlist("description")
        rows = [
            {"name": n.strip(), "description": (descriptions[i] if i < len(descriptions) else "").strip()}
            for i, n in enumerate(names)
        ]
        filled = [r for r in rows if r["name"]]

        too_long = [r["name"] for r in filled if len(r["name"]) > NAME_MAX]
        if not filled:
            messages.error(request, "Enter at least one category name.")
        elif too_long:
            messages.error(request, f"Category names must be {NAME_MAX} characters or fewer.")
        else:
            created, skipped, seen = [], [], set()
            with transaction.atomic():
                for r in filled:
                    key = r["name"].lower()
                    if key in seen or ExpenseCategory.objects.filter(name__iexact=r["name"]).exists():
                        skipped.append(r["name"])
                        continue
                    seen.add(key)
                    ExpenseCategory.objects.create(name=r["name"], description=r["description"])
                    created.append(r["name"])

            if skipped:
                messages.warning(request, "Already exist or repeated, skipped: " + ", ".join(skipped))
            if created:
                messages.success(request, f"{len(created)} categor{'y' if len(created) == 1 else 'ies'} added: " + ", ".join(created))
                return redirect("expenses:create_expense")
            # Nothing new was created: stay on the page so the user can fix it
            rows = [r for r in rows if r["name"]] or rows

    return render(
        request,
        "expenses/category_create.html",
        {"rows": rows, "title": "Add Expense Categories"},
    )


@login_required
def category_update(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk)

    if request.method == "POST":
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect("expenses:category_list")
    else:
        form = ExpenseCategoryForm(instance=category)

    return render(
        request,
        "expenses/category_form.html",
        {"form": form, "title": f"Edit Category: {category.name}"},
    )


@login_required
@require_POST
def category_toggle(request, pk):
    """Activate/deactivate instead of deleting (expenses protect the category)."""
    category = get_object_or_404(ExpenseCategory, pk=pk)
    category.is_active = not category.is_active
    category.save(update_fields=["is_active", "updated_at"])
    state = "activated" if category.is_active else "deactivated"
    messages.success(request, f"Category {category.name} {state}.")
    return redirect("expenses:category_list")