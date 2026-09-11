from django.shortcuts import render,redirect, get_object_or_404
from .forms import PurchaseForm,PurchaseItemFormSet, PurchasePaymentForm
from .models import Purchase
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import transaction
from django.contrib import messages
from inventory.models import Inventory, InventoryTransaction
from django.db import models
from django.core.paginator import Paginator
from django.db.models import Sum, Count
from suppliers.services import record_supplier_purchase
from django.contrib.auth.decorators import user_passes_test
from decimal import Decimal
from django.utils import timezone

# Create your views here.
@login_required
def purchase_details(request, id):
    purchase=get_object_or_404(Purchase, id=id)
    items = purchase.items.all()
    payments = purchase.payments.all().order_by("-payment_date")
    return render(
        request, "purchase/purchase_details.html",
        {
            "purchase":purchase,
            "items":items,
            "payments": payments,
        }
                  )


@login_required
def add_purchase(request):
    if request.method == "POST":
        purchase_form = PurchaseForm(request.POST)
        formset = PurchaseItemFormSet(request.POST)
        if purchase_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                purchase = purchase_form.save(
                    commit=False
                )
                purchase.created_by = request.user
                purchase.total_amount = 0
                purchase.balance = 0
                purchase.save()
                items = formset.save(
                    commit=False
                )
                total = Decimal('0.00')
                for item in items:
                    item.purchase = purchase
                    item.save()
                    total += (Decimal(item.quantity) * Decimal(item.cost_price))
                purchase.total_amount = total
                purchase.balance = total
                purchase.save(
                    update_fields=[
                        "total_amount",
                        "balance",
                    ]
                )
            return redirect(
                "purchase:add_purchase_payment",
                purchase.id
            )
    else:
        purchase_form = PurchaseForm()
        formset = PurchaseItemFormSet()
    return render(
        request,
        "purchase/add_purchase.html",
        {
            "purchase_form": purchase_form,
            "formset": formset,
        }
    )


@login_required
def view_purchase(request):

    purchases = Purchase.objects.select_related(
        "supplier",
        "created_by",
    ).all()

    search = request.GET.get("search", "").strip()
    payment_status = request.GET.get("payment_status", "").strip()
    purchase_status = request.GET.get("purchase_status", "").strip()

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if search:
        purchases = purchases.filter(
            models.Q(invoice_number__icontains=search)
            | models.Q(supplier__name__icontains=search)
            | models.Q(items__product__name__icontains=search)
            | models.Q(items__product__product_code__icontains=search)
            | models.Q(items__product__barcode__icontains=search)
        )

    if payment_status:
        purchases = purchases.filter(
            payment_status=payment_status
        )

    if purchase_status:
        purchases = purchases.filter(
            status=purchase_status
        )

    if date_from:
        purchases = purchases.filter(
            purchase_date__gte=date_from
        )

    if date_to:
        purchases = purchases.filter(
            purchase_date__lte=date_to
        )

    purchases = purchases.distinct().order_by(
        "-purchase_date",
        "-id",
    )
    paginator = Paginator(
    purchases,
    10,
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
    page_number
    )
    return render(
        request,
        "purchase/view_purchase.html",
        {
            "purchases": page_obj,
            "search": search,
            "payment_status": payment_status,
            "purchase_status": purchase_status,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


def is_inventory_staff(user):
    # adjust to your project's logic for inventory staff
    return user.is_authenticated and (user.is_staff or user.groups.filter(name='inventory').exists())


def _mark_purchase_received(purchase, user):
    """
    Move the logic that actually applies the receive operation into a helper so
    we can call it from the confirmation POST-handling.
    """
    from inventory.models import Inventory, InventoryTransaction
    from suppliers.services import record_supplier_purchase

    # Get items
    items = purchase.items.select_related(
        "product"
    )

    # Update inventory and create transactions
    for item in items:

        inventory, created = Inventory.objects.get_or_create(
            product=item.product
        )

        # Increase available stock

        inventory.quantity_available += item.quantity

        # Increase total received stock

        inventory.quantity_received += item.quantity

        inventory.save(
            update_fields=[
                "quantity_available",
                "quantity_received",
                "updated_at",
            ]
        )

        # --------------------------------
        # Create inventory history
        # --------------------------------

        InventoryTransaction.objects.create(
            product=item.product,
            transaction_type="PURCHASE",
            quantity=item.quantity,
            reference_id=purchase.id,
            description=(
                f"Purchase "
                f"{purchase.invoice_number}"
            ),
            created_by=user,
        )

    # --------------------------------
    # Update supplier balance
    # --------------------------------

    record_supplier_purchase(
        supplier=purchase.supplier,
        amount=purchase.total_amount,
        purchase_id=purchase.id,
        created_by=user,
        description=(
            f"Purchase "
            f"{purchase.invoice_number}"
        ),
    )

    # --------------------------------
    # Mark purchase as received
    # --------------------------------

    purchase.status = Purchase.Status.RECEIVED

    purchase.save(
        update_fields=[
            "status"
        ]
    )


@login_required
def receive_purchase(request, id):
    # redirect to confirmation page (so the inventory staff sees the confirm screen)
    return redirect("purchase:confirm_receive", id)


@user_passes_test(is_inventory_staff)
def confirm_receive(request, id):
    """
    New confirmation page:
    - GET: show confirmation form (Received? yes/no) and amount (prefilled with purchase.total_amount)
    - POST: if received=yes, call _mark_purchase_received(); if received=no, leave status unchanged
    """
    purchase = get_object_or_404(Purchase.objects.select_related("supplier"), id=id)

    # Prevent confirming if already received
    if purchase.status == Purchase.Status.RECEIVED:
        messages.warning(request, "This purchase has already been received.")
        return redirect("purchase:purchase_details", purchase.id)

    default_amount = purchase.total_amount or Decimal("0.00")

    if request.method == "POST":
        received_val = request.POST.get('received', 'yes')
        received = True if received_val == 'yes' else False
        amount_str = request.POST.get('amount', '') or str(default_amount)

        try:
            amount = Decimal(amount_str)
        except Exception:
            amount = default_amount

        # If staff confirms received -> run the same logic as previous receive_purchase
        if received:
            with transaction.atomic():
                # lock and re-fetch
                purchase = Purchase.objects.select_for_update().select_related("supplier").get(id=id)

                if purchase.status == Purchase.Status.RECEIVED:
                    messages.warning(request, "This purchase has already been received.")
                    return redirect("purchase:purchase_details", purchase.id)

                _mark_purchase_received(purchase, request.user)

            messages.success(request, f"Purchase {purchase.invoice_number} received successfully (amount: {amount}).")
        else:
            # Staff confirmed NOT RECEIVED; you can record a message or take other actions here
            messages.info(request, f"Purchase {purchase.invoice_number} marked as NOT received (amount: {amount}).")

        return redirect("purchase:purchase_details", purchase.id)

    # GET -> render the confirm page
    return render(request, "purchase/confirm_receive.html", {
        "purchase": purchase,
        "default_amount": default_amount,
    })


@login_required
def add_purchase_payment(request, id):
    purchase = get_object_or_404(
        Purchase,
        id=id
    )
    if purchase.status == Purchase.Status.CANCELLED:
        messages.error(request,"You cannot make a payment for a cancelled purchase.")
        return redirect(
            "purchase:purchase_details",
            purchase.id
        )
    if purchase.payment_status == "PAID":
        messages.warning(request,"This purchase has already been fully paid.")
        return redirect(
            "purchase:purchase_details",
            purchase.id
        )
    if request.method == "POST":
        form = PurchasePaymentForm(
            request.POST,
            purchase=purchase
        )
        if form.is_valid():
            with transaction.atomic():
                payment = form.save(commit=False)
                payment.purchase = purchase
                payment.created_by = request.user
                payment.save()
                purchase.update_payment_status()
            messages.success(request,"Payment recorded successfully.")
            return redirect("purchase:purchase_details",
                purchase.id
            )
    else:
        form = PurchasePaymentForm(
            purchase=purchase
        )
    return render(request,"purchase/add_purchase_payment.html",
        {
            "form": form,
            "purchase": purchase,
        }
    )

def purchase_invoice(request, id):
    purchase = get_object_or_404(
        Purchase.objects.select_related(
            "supplier",
            "created_by",
        ),
        id=id,
    )
    items = purchase.items.select_related(
        "product"
    ).all()
    payments = purchase.payments.select_related(
        "created_by"
    ).order_by("-payment_date")
    return render(
        request,
        "purchase/purchase_invoice.html",
        {
            "purchase": purchase,
            "items": items,
            "payments": payments,
        },
    )


@login_required
def purchase_reports(request):

    total_purchases = Purchase.objects.count()

    total_spending = Purchase.objects.aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    total_paid = Purchase.objects.aggregate(
        total=Sum("paid_amount")
    )["total"] or 0

    total_outstanding = Purchase.objects.aggregate(
        total=Sum("balance")
    )["total"] or 0

    paid_purchases = Purchase.objects.filter(
        payment_status="PAID"
    ).count()

    partial_purchases = Purchase.objects.filter(
        payment_status="PARTIAL"
    ).count()

    unpaid_purchases = Purchase.objects.filter(
        payment_status="UNPAID"
    ).count()

    received_purchases = Purchase.objects.filter(
        status="RECEIVED"
    ).count()

    pending_purchases = Purchase.objects.exclude(
        status="RECEIVED"
    ).count()

    supplier_summary = (
        Purchase.objects
        .values("supplier__name")
        .annotate(
            purchase_count=Count("id"),
            total_amount=Sum("total_amount"),
            total_paid=Sum("paid_amount"),
            balance=Sum("balance"),
        )
        .order_by("-total_amount")
    )

    context = {
        "total_purchases": total_purchases,
        "total_spending": total_spending,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,

        "paid_purchases": paid_purchases,
        "partial_purchases": partial_purchases,
        "unpaid_purchases": unpaid_purchases,

        "received_purchases": received_purchases,
        "pending_purchases": pending_purchases,

        "supplier_summary": supplier_summary,
    }

    return render(
        request,
        "purchase/purchase_reports.html",
        context,
    )

def delete_purchase(request):
    return render(request, "purchase/view_purchase.html")
