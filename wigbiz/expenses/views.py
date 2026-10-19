from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from notifications.models import Notification
from notifications.services import create_notification, notify_role

from .forms import ExpenseForm, ExpenseCategoryForm
from .models import Expense, ExpenseCategory
from .Permissions import ADMINISTRATOR, MANAGER, SALESPERSON, has_role, roles_required
from .utils import generate_expense_number

NAME_MAX = ExpenseCategory._meta.get_field("name").max_length


def _expense_url(expense):
    return reverse("expenses:expense_detail", args=[expense.pk])


def can_delete_expense(user, expense):
    """Administrators can delete any expense; salespeople only their own pending ones."""
    if has_role(user, ADMINISTRATOR):
        return True
    return (
        has_role(user, SALESPERSON)
        and expense.created_by_id == user.id
        and expense.status == Expense.STATUS_PENDING
    )


# ============================================================
# EXPENSES
# ============================================================

@roles_required(ADMINISTRATOR, SALESPERSON)
def create_expense(request):
    """Administrators and salespeople submit expenses; they start as PENDING."""

    # An expense needs a category: if none exist yet, add some first
    if not ExpenseCategory.objects.filter(is_active=True).exists():
        messages.info(request, "Add at least one expense category first.")
        return redirect("expenses:category_create")

    if request.method == "POST":
        form = ExpenseForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                expense = form.save(commit=False)
                expense.expense_number = generate_expense_number()
                expense.created_by = request.user
                expense.status = Expense.STATUS_PENDING
                expense.save()

                # Tell every manager there is something to approve
                notified = notify_role(
                    MANAGER,
                    title="Expense awaiting approval",
                    message=(
                        f"{request.user.get_full_name() or request.user.username} submitted "
                        f"expense {expense.expense_number} for UGX {expense.amount:,.2f} "
                        f"({expense.category.name})."
                    ),
                    action_url=_expense_url(expense),
                    notification_type=Notification.NotificationType.EXPENSE,
                    metadata={"expense_id": expense.pk, "event": "submitted"},
                )

            if notified:
                messages.success(request, "Expense submitted for manager approval.")
            else:
                messages.warning(
                    request,
                    "Expense saved, but no active manager was found to approve it.",
                )

            return redirect("expenses:expense_list")

    else:
        form = ExpenseForm()

    return render(request, "expenses/create_expense.html", {"form": form})


@roles_required(ADMINISTRATOR, MANAGER, SALESPERSON)
def expense_list(request):

    expenses = Expense.objects.select_related(
        "category",
        "created_by"
    ).all()

    # Salespeople only see the expenses they submitted
    if has_role(request.user, SALESPERSON):
        expenses = expenses.filter(created_by=request.user)

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
    # STATUS FILTER
    # =========================

    status = request.GET.get("status", "").strip()

    if status in dict(Expense.STATUS_CHOICES):
        expenses = expenses.filter(status=status)
    else:
        status = ""

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
    # TOTAL (approved expenses only)
    # =========================

    total_expenses = expenses.filter(
        status=Expense.STATUS_APPROVED
    ).aggregate(total=Sum("amount"))["total"] or 0

    # =========================
    # PAGINATION
    # =========================

    paginator = Paginator(
        expenses,
        10
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    for expense in page_obj:
        expense.can_delete = can_delete_expense(request.user, expense)

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
        "status": status,
        "date_from": date_from,
        "date_to": date_to,

        "total_expenses": total_expenses,
        "is_manager": has_role(request.user, MANAGER),
        "pending_count": Expense.objects.filter(status=Expense.STATUS_PENDING).count(),
    }

    return render(
        request,
        "expenses/expense_list.html",
        context
    )


@roles_required(ADMINISTRATOR, MANAGER, SALESPERSON)
def expense_detail(request, pk):
    expense = get_object_or_404(
        Expense.objects.select_related("category", "created_by", "reviewed_by"),
        pk=pk,
    )

    # Salespeople may only open their own expenses
    if has_role(request.user, SALESPERSON) and expense.created_by_id != request.user.id:
        return redirect("expenses:expense_list")

    can_review = (
        has_role(request.user, MANAGER)
        and expense.status == Expense.STATUS_PENDING
        and expense.created_by_id != request.user.id
    )

    return render(
        request,
        "expenses/expense_detail.html",
        {
            "expense": expense,
            "can_review": can_review,
            "can_delete": can_delete_expense(request.user, expense),
        },
    )


def _review(request, pk, new_status):
    """Shared approve/reject logic. Returns the expense, or None if it was already reviewed."""
    expense = get_object_or_404(Expense, pk=pk)

    if expense.created_by_id == request.user.id:
        messages.error(request, "You cannot review an expense you submitted yourself.")
        return None

    reason = request.POST.get("rejection_reason", "").strip() if new_status == Expense.STATUS_REJECTED else ""

    # Only a still-PENDING expense can be reviewed (guards against double clicks / two managers)
    updated = Expense.objects.filter(pk=pk, status=Expense.STATUS_PENDING).update(
        status=new_status,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
        rejection_reason=reason,
        updated_at=timezone.now(),
    )
    if not updated:
        messages.warning(request, "This expense has already been reviewed.")
        return None

    expense.refresh_from_db()
    return expense


@roles_required(MANAGER)
@require_POST
def expense_approve(request, pk):
    expense = _review(request, pk, Expense.STATUS_APPROVED)

    if expense is not None:
        if expense.created_by:
            create_notification(
                recipient=expense.created_by,
                title="Expense approved",
                message=(
                    f"Your expense {expense.expense_number} for UGX {expense.amount:,.2f} "
                    f"was approved by {request.user.get_full_name() or request.user.username}."
                ),
                action_url=_expense_url(expense),
                notification_type=Notification.NotificationType.EXPENSE,
                metadata={"expense_id": expense.pk, "event": "approved"},
            )
        messages.success(request, f"Expense {expense.expense_number} approved.")

    return redirect("expenses:expense_detail", pk=pk)


@roles_required(MANAGER)
@require_POST
def expense_reject(request, pk):
    if not request.POST.get("rejection_reason", "").strip():
        messages.error(request, "Please give a reason for rejecting this expense.")
        return redirect("expenses:expense_detail", pk=pk)

    expense = _review(request, pk, Expense.STATUS_REJECTED)

    if expense is not None:
        if expense.created_by:
            create_notification(
                recipient=expense.created_by,
                title="Expense rejected",
                message=(
                    f"Your expense {expense.expense_number} for UGX {expense.amount:,.2f} "
                    f"was rejected by {request.user.get_full_name() or request.user.username}. "
                    f"Reason: {expense.rejection_reason}"
                ),
                action_url=_expense_url(expense),
                notification_type=Notification.NotificationType.EXPENSE,
                metadata={"expense_id": expense.pk, "event": "rejected"},
            )
        messages.success(request, f"Expense {expense.expense_number} rejected.")

    return redirect("expenses:expense_detail", pk=pk)


@roles_required(ADMINISTRATOR, SALESPERSON)
@require_POST
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    if not can_delete_expense(request.user, expense):
        raise PermissionDenied

    number = expense.expense_number
    with transaction.atomic():
        # Remove notifications that point at this expense so no dead links remain
        Notification.objects.filter(metadata__expense_id=expense.pk).delete()
        expense.delete()

    messages.success(request, f"Expense {number} deleted.")
    return redirect("expenses:expense_list")


# ============================================================
# EXPENSE CATEGORIES
# ============================================================

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
            {
                "name": n.strip(),
                "description": (descriptions[i] if i < len(descriptions) else "").strip(),
            }
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
                messages.success(
                    request,
                    f"{len(created)} categor{'y' if len(created) == 1 else 'ies'} added: " + ", ".join(created),
                )
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