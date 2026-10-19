from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import role_required
from core.utils import parse_date_or_none
from products.models import Product

from .forms import SaleForm, SaleItemFormSet
from .models import Refund, Sale, SaleReturn
from .notify import (
    notify_managers_return_requested,
    notify_return_completed,
    notify_return_decision,
)
from .returns import (
    attach_return_quantities,
    complete_sale_return,
    create_refund,
    create_sale_return,
)
from .services import create_sale


# ==========================================================
# SMALL HELPERS
# ==========================================================

REVIEWER_ROLES = ("manager", "administrator")


def _role_name(user):
    role = getattr(user, "role", None)
    return (getattr(role, "name", "") or "").lower()


def _is_reviewer(user):
    """Managers and administrators may see every return and refund."""
    return _role_name(user) in REVIEWER_ROLES


# ==========================================================
# SALES
# ==========================================================

@login_required
def create_sale_view(request):
    if request.method == "POST":
        sale_form = SaleForm(request.POST)
        item_formset = SaleItemFormSet(request.POST)
        if sale_form.is_valid() and item_formset.is_valid():
            items = []
            for form in item_formset:
                if form.cleaned_data:
                    items.append({
                        "product": form.cleaned_data["product"],
                        "quantity": form.cleaned_data["quantity"],
                    })

            try:
                sale = create_sale(
                    customer=sale_form.cleaned_data["customer"],
                    created_by=request.user,
                    items=items,
                    discount=sale_form.cleaned_data["discount"] or 0,
                    tax=sale_form.cleaned_data["tax"] or 0,
                    payment_method=sale_form.cleaned_data["payment_method"],
                    amount_paid=sale_form.cleaned_data["amount_paid"] or 0,
                )
                return redirect("sales:sale_detail", pk=sale.pk)

            except ValidationError as e:
                sale_form.add_error(None, e.message)
    else:
        sale_form = SaleForm()
        item_formset = SaleItemFormSet()

    return render(
        request,
        "sales/create_sale.html",
        {"sale_form": sale_form, "item_formset": item_formset},
    )


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.prefetch_related("items__product", "payments"),
        pk=pk,
    )
    return render(request, "sales/sale_detail.html", {"sale": sale})


@login_required
@require_GET
def product_by_barcode(request):
    barcode = request.GET.get("barcode", "").strip()

    if not barcode:
        return JsonResponse(
            {"success": False, "message": "Barcode is required."}, status=400
        )

    try:
        product = Product.objects.get(barcode=barcode, status=True)
    except Product.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Product not found."}, status=404
        )

    return JsonResponse({
        "success": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "barcode": product.barcode,
            "selling_price": str(product.selling_price),
        },
    })


@login_required
def sales_history(request):
    sales = (
        Sale.objects.select_related("customer", "created_by")
        .prefetch_related("items__product")
        .order_by("-sale_date")
    )

    search = request.GET.get("search", "").strip()
    if search:
        sales = sales.filter(
            Q(invoice_number__icontains=search) | Q(customer__name__icontains=search)
        )

    status = request.GET.get("status", "")
    if status:
        sales = sales.filter(status=status)

    payment_method = request.GET.get("payment_method", "")
    if payment_method:
        sales = sales.filter(payment_method=payment_method)

    date_from_raw = request.GET.get("date_from", "")
    date_to_raw = request.GET.get("date_to", "")
    date_from = parse_date_or_none(date_from_raw)
    date_to = parse_date_or_none(date_to_raw)
    if date_from:
        sales = sales.filter(sale_date__date__gte=date_from)
    if date_to:
        sales = sales.filter(sale_date__date__lte=date_to)

    page_obj = Paginator(sales, 20).get_page(request.GET.get("page"))

    # Units returned / waiting / still available, for the whole page in ONE query.
    for sale in page_obj:
        sale.item_rows = list(sale.items.all())

    attach_return_quantities([item for sale in page_obj for item in sale.item_rows])

    is_salesperson = _role_name(request.user) == "salesperson"
    for sale in page_obj:
        # Only the salesperson who made the sale can return it.
        sale.can_return = (
            is_salesperson
            and sale.created_by_id == request.user.id
            and sale.status == Sale.Status.COMPLETED
            and any(item.available_qty > 0 for item in sale.item_rows)
        )

    return render(
        request,
        "sales/sales_history.html",
        {
            "sales": page_obj,
            "search": search,
            "selected_status": status,
            "selected_payment_method": payment_method,
            "status_choices": Sale.Status.choices,
            "payment_choices": Sale.PAYMENT_METHODS,
            "date_from": date_from_raw,
            "date_to": date_to_raw,
        },
    )


# ==========================================================
# STEP 1: SALESPERSON REQUESTS A RETURN  ->  managers notified
# ==========================================================

@login_required
@role_required("Salesperson")
def create_return(request, pk):
    # created_by=request.user: a salesperson can only return their own sales.
    sale = get_object_or_404(
        Sale.objects.prefetch_related("items__product"),
        pk=pk,
        created_by=request.user,
    )

    if sale.status != Sale.Status.COMPLETED:
        messages.error(request, "Only completed sales can be returned.")
        return redirect("sales:sales_history")

    items = attach_return_quantities(sale.items.all())
    context = {"sale": sale, "items": items}

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        selected = []

        for sale_item in items:
            try:
                quantity = int(request.POST.get(f"quantity_{sale_item.id}", "0"))
            except (TypeError, ValueError):
                quantity = 0
            if quantity > 0:
                selected.append({"sale_item": sale_item, "quantity": quantity})

        if not reason:
            context["error"] = "Please give a reason for the return."
            context["reason"] = reason
            return render(request, "sales/create_return.html", context)

        try:
            sale_return = create_sale_return(
                sale=sale,
                created_by=request.user,
                items=selected,
                reason=reason,
            )
        except ValidationError as e:
            context["error"] = "; ".join(e.messages)
            context["reason"] = reason
            return render(request, "sales/create_return.html", context)

        notify_managers_return_requested(sale_return)

        messages.success(
            request,
            "Return requested. A manager must approve it before you can return the product.",
        )
        return redirect("sales:return_detail", pk=sale_return.pk)

    return render(request, "sales/create_return.html", context)


# ==========================================================
# STEP 2: MANAGER APPROVES OR REJECTS  ->  salesperson notified
# ==========================================================

@login_required
@role_required("Manager")
def return_approval_list(request):
    returns = (
        SaleReturn.objects
        .select_related("sale", "created_by")
        .prefetch_related("items")
        .filter(status=SaleReturn.Status.PENDING)
        .order_by("-created_at")
    )
    return render(request, "sales/return_approval_list.html", {"returns": returns})


@login_required
@role_required("Manager")
def return_approval_detail(request, pk):
    sale_return = get_object_or_404(
        SaleReturn.objects
        .select_related("sale", "created_by", "approved_by")
        .prefetch_related("items__sale_item__product"),
        pk=pk,
    )
    return render(
        request,
        "sales/return_approval_detail.html",
        {"sale_return": sale_return},
    )


@login_required
@role_required("Manager")
@require_POST
@transaction.atomic
def approve_return(request, pk):
    """Approving ONLY marks the return APPROVED. Stock and refund wait for step 3."""
    sale_return = get_object_or_404(SaleReturn.objects.select_for_update(), pk=pk)

    if sale_return.status != SaleReturn.Status.PENDING:
        messages.error(request, "This return is no longer pending approval.")
        return redirect("sales:return_approval_list")

    sale_return.status = SaleReturn.Status.APPROVED
    sale_return.approved_by = request.user
    sale_return.approved_at = timezone.now()
    sale_return.save(update_fields=["status", "approved_by", "approved_at"])

    transaction.on_commit(lambda: notify_return_decision(sale_return, approved=True))

    messages.success(
        request,
        f"Return {sale_return.return_number} approved. The salesperson has been notified.",
    )
    return redirect("sales:return_approval_list")


@login_required
@role_required("Manager")
@require_POST
@transaction.atomic
def reject_return(request, pk):
    sale_return = get_object_or_404(SaleReturn.objects.select_for_update(), pk=pk)

    if sale_return.status != SaleReturn.Status.PENDING:
        messages.error(request, "This return is no longer pending approval.")
        return redirect("sales:return_approval_list")

    rejection_reason = request.POST.get("rejection_reason", "").strip()
    if not rejection_reason:
        messages.error(request, "Please provide a reason for rejecting the return.")
        return redirect("sales:return_approval_detail", pk=sale_return.pk)

    sale_return.status = SaleReturn.Status.REJECTED
    sale_return.rejection_reason = rejection_reason
    # approved_by / approved_at double as "reviewed by / reviewed at"
    sale_return.approved_by = request.user
    sale_return.approved_at = timezone.now()
    sale_return.save(
        update_fields=["status", "rejection_reason", "approved_by", "approved_at"]
    )

    transaction.on_commit(lambda: notify_return_decision(sale_return, approved=False))

    messages.success(request, f"Return {sale_return.return_number} rejected.")
    return redirect("sales:return_approval_list")


# ==========================================================
# STEP 3: SALESPERSON CLICKS "RETURN PRODUCT"
#         -> stock restored, refund recorded, managers notified
# ==========================================================

@login_required
@require_POST
def complete_return(request, pk):
    try:
        # Everything in this block succeeds together or is undone together.
        with transaction.atomic():
            sale_return = get_object_or_404(
                SaleReturn.objects.select_for_update().select_related("sale"),
                pk=pk,
            )

            # Only the salesperson who requested the return may finish it.
            if sale_return.created_by_id != request.user.id:
                raise PermissionDenied

            if sale_return.status != SaleReturn.Status.APPROVED:
                raise ValidationError("This return has not been approved by a manager.")

            complete_sale_return(sale_return, request.user)

            create_refund(
                sale_return=sale_return,
                refunded_by=request.user,
                payment_method=sale_return.sale.payment_method,
            )

            transaction.on_commit(lambda: notify_return_completed(sale_return))

    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
        return redirect("sales:return_detail", pk=pk)

    messages.success(
        request,
        f"Return {sale_return.return_number} is complete and the refund has been recorded.",
    )
    return redirect("sales:return_detail", pk=pk)


# ==========================================================
# HISTORY PAGES
# ==========================================================

@login_required
def return_detail(request, pk):
    sale_return = get_object_or_404(
        SaleReturn.objects
        .select_related("sale", "created_by", "approved_by")
        .prefetch_related("items__sale_item__product"),
        pk=pk,
    )

    is_owner = sale_return.created_by_id == request.user.id
    if not (is_owner or _is_reviewer(request.user)):
        raise PermissionDenied

    refund = getattr(sale_return, "refund", None)

    return render(
        request,
        "sales/return_detail.html",
        {
            "sale_return": sale_return,
            "refund": refund,
            # part of the refund that was taken off the customer's unpaid balance
            "written_off": (sale_return.total_refund - refund.amount) if refund else 0,
            "can_complete": is_owner and sale_return.status == SaleReturn.Status.APPROVED,
            "can_review": (
                _role_name(request.user) == "manager"
                and sale_return.status == SaleReturn.Status.PENDING
            ),
        },
    )


@login_required
def return_history(request):
    returns = (
        SaleReturn.objects
        .select_related("sale", "created_by")
        .prefetch_related("items")
        .order_by("-created_at")
    )

    if not _is_reviewer(request.user):
        returns = returns.filter(created_by=request.user)

    search = request.GET.get("search", "").strip()
    if search:
        returns = returns.filter(
            Q(return_number__icontains=search)
            | Q(sale__invoice_number__icontains=search)
        )

    status = request.GET.get("status", "")
    if status:
        returns = returns.filter(status=status)

    page_obj = Paginator(returns, 20).get_page(request.GET.get("page"))

    for sale_return in page_obj:
        sale_return.total_qty = sum(item.quantity for item in sale_return.items.all())

    return render(
        request,
        "sales/return_history.html",
        {
            "returns": page_obj,
            "search": search,
            "selected_status": status,
            "status_choices": SaleReturn.Status.choices,
        },
    )


@login_required
def refund_history(request):
    if not _is_reviewer(request.user):
        raise PermissionDenied

    refunds = (
        Refund.objects
        .select_related("sale_return", "sale_return__sale", "refunded_by")
        .order_by("-created_at")
    )

    search = request.GET.get("search", "").strip()
    if search:
        refunds = refunds.filter(
            Q(sale_return__return_number__icontains=search)
            | Q(sale_return__sale__invoice_number__icontains=search)
        )

    payment_method = request.GET.get("payment_method", "")
    if payment_method:
        refunds = refunds.filter(payment_method=payment_method)

    page_obj = Paginator(refunds, 20).get_page(request.GET.get("page"))

    return render(
        request,
        "sales/refund_history.html",
        {
            "refunds": page_obj,
            "search": search,
            "selected_payment_method": payment_method,
            "payment_choices": Sale.PAYMENT_METHODS,
        },
    )
