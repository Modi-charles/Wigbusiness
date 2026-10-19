from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum

from inventory.models import Inventory, InventoryTransaction

from .models import Refund, Sale, SaleReturn, SaleReturnItem

TWO_PLACES = Decimal("0.01")

# A return in one of these statuses "holds" units: they cannot be returned again.
ACTIVE_STATUSES = [
    SaleReturn.Status.PENDING,
    SaleReturn.Status.APPROVED,
    SaleReturn.Status.COMPLETED,
]


# ==========================================================
# HELPERS
# ==========================================================

def generate_return_number():
    """RET-000001, RET-000002 ... based on the highest id so far."""
    latest = SaleReturn.objects.order_by("-id").first()
    if latest is None:
        return "RET-000001"
    try:
        number = int(latest.return_number.split("-")[1]) + 1
    except (IndexError, ValueError):
        number = latest.id + 1
    return f"RET-{number:06d}"


def attach_return_quantities(sale_items):
    """
    For every SaleItem work out (with ONE query):
      returned_qty   - already returned (return COMPLETED)
      pending_qty    - held by a return that is PENDING or APPROVED
      available_qty  - still free to return
    The numbers are attached to the items, so a template can write
    {{ item.available_qty }}.
    """
    sale_items = list(sale_items)

    rows = (
        SaleReturnItem.objects
        .filter(sale_item__in=sale_items, sale_return__status__in=ACTIVE_STATUSES)
        .values("sale_item_id", "sale_return__status")
        .annotate(total=Sum("quantity"))
    )

    returned, pending = {}, {}
    for row in rows:
        bucket = returned if row["sale_return__status"] == SaleReturn.Status.COMPLETED else pending
        key = row["sale_item_id"]
        bucket[key] = bucket.get(key, 0) + row["total"]

    for item in sale_items:
        item.returned_qty = returned.get(item.id, 0)
        item.pending_qty = pending.get(item.id, 0)
        item.available_qty = item.quantity - item.returned_qty - item.pending_qty

    return sale_items


def _refund_factor(sale):
    """
    Share of the shelf price the customer really paid for.
    total = subtotal - discount + tax, so a discounted sale refunds less
    per unit than the selling price, and tax is given back too.
    """
    if sale.subtotal and sale.subtotal > 0:
        return sale.total_amount / sale.subtotal
    return Decimal("1")


# ==========================================================
# STEP 1: REQUEST A RETURN (status PENDING)
# ==========================================================

@transaction.atomic
def create_sale_return(sale, created_by, items, reason=""):
    """
    items = [{"sale_item": SaleItem, "quantity": int}, ...]
    Everything is validated first; nothing is saved if any check fails.
    """
    # Lock the sale so two requests cannot both pass the quantity check.
    sale = Sale.objects.select_for_update().get(pk=sale.pk)

    if not items:
        raise ValidationError("A return must contain at least one item.")

    if sale.status == Sale.Status.CANCELLED:
        raise ValidationError("Cancelled sales cannot be returned.")

    if sale.status == Sale.Status.REFUNDED:
        raise ValidationError("This sale has already been fully refunded.")

    if sale.status != Sale.Status.COMPLETED:
        raise ValidationError("Only completed sales can be returned.")

    factor = _refund_factor(sale)
    lines = []
    total_refund = Decimal("0.00")

    for row in items:
        sale_item = row["sale_item"]
        quantity = row["quantity"]

        if quantity <= 0:
            raise ValidationError("Return quantity must be greater than zero.")

        if sale_item.sale_id != sale.id:
            raise ValidationError("The selected item does not belong to this sale.")

        held = (
            SaleReturnItem.objects
            .filter(sale_item=sale_item, sale_return__status__in=ACTIVE_STATUSES)
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )
        remaining = sale_item.quantity - held

        if quantity > remaining:
            raise ValidationError(
                f"Cannot return {quantity} unit(s) of {sale_item.product.name}. "
                f"Only {max(remaining, 0)} unit(s) can be returned."
            )

        refund_amount = (sale_item.selling_price * quantity * factor).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        lines.append((sale_item, quantity, refund_amount))
        total_refund += refund_amount

    # Create the return. Retry if two requests got the same number.
    sale_return = None
    for _ in range(3):
        try:
            with transaction.atomic():
                sale_return = SaleReturn.objects.create(
                    sale=sale,
                    return_number=generate_return_number(),
                    reason=reason,
                    created_by=created_by,
                    status=SaleReturn.Status.PENDING,
                    total_refund=total_refund,
                )
            break
        except IntegrityError:
            continue

    if sale_return is None:
        raise ValidationError("Could not create the return. Please try again.")

    SaleReturnItem.objects.bulk_create([
        SaleReturnItem(
            sale_return=sale_return,
            sale_item=sale_item,
            quantity=quantity,
            refund_amount=refund_amount,
        )
        for sale_item, quantity, refund_amount in lines
    ])

    return sale_return


# ==========================================================
# STEP 3 (part 1): RESTOCK
# ==========================================================

@transaction.atomic
def complete_sale_return(sale_return, processed_by):
    """Put the returned units back into stock and mark the return COMPLETED."""
    if sale_return.status != SaleReturn.Status.APPROVED:
        raise ValidationError("Only approved returns can be completed.")

    for return_item in sale_return.items.select_related("sale_item__product"):
        product = return_item.sale_item.product

        try:
            inventory = Inventory.objects.select_for_update().get(product=product)
        except Inventory.DoesNotExist:
            raise ValidationError(f"No inventory record exists for {product.name}.")

        inventory.quantity_available += return_item.quantity
        inventory.quantity_sold = max(0, inventory.quantity_sold - return_item.quantity)
        inventory.save(update_fields=["quantity_available", "quantity_sold", "updated_at"])

        InventoryTransaction.objects.create(
            product=product,
            transaction_type="RETURN",
            quantity=return_item.quantity,
            reference_id=sale_return.id,
            description=f"Returned {return_item.quantity} unit(s) of {product.name}",
            created_by=processed_by,
        )

    sale_return.status = SaleReturn.Status.COMPLETED
    sale_return.save(update_fields=["status"])
    return sale_return


# ==========================================================
# STEP 3 (part 2): REFUND
# ==========================================================

def _mark_sale_refunded_if_fully_returned(sale):
    """Once every unit has come back the sale becomes REFUNDED."""
    units_sold = sale.items.aggregate(total=Sum("quantity"))["total"] or 0
    units_returned = (
        SaleReturnItem.objects
        .filter(sale_item__sale=sale, sale_return__status=SaleReturn.Status.COMPLETED)
        .aggregate(total=Sum("quantity"))["total"]
        or 0
    )
    if units_sold and units_returned >= units_sold:
        sale.status = Sale.Status.REFUNDED
        sale.save(update_fields=["status"])


@transaction.atomic
def create_refund(sale_return, refunded_by, payment_method):
    """
    Refund a COMPLETED return.

    The customer only gets back money they really paid:
      cash_back  = min(total_refund, money paid so far - money already refunded)
      write_off  = the rest, which reduces what the customer still owes
    So a credit sale never pays out money that was never received.
    """
    if sale_return.status != SaleReturn.Status.COMPLETED:
        raise ValidationError("Only completed returns can be refunded.")

    if Refund.objects.filter(sale_return=sale_return).exists():
        raise ValidationError("This return has already been refunded.")

    if payment_method not in dict(Sale.PAYMENT_METHODS):
        raise ValidationError("Invalid payment method.")

    sale = Sale.objects.select_for_update().get(pk=sale_return.sale_id)

    paid = min(sale.paid_amount, sale.total_amount)
    already_refunded = (
        Refund.objects
        .filter(sale_return__sale=sale, status=Refund.Status.COMPLETED)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    refundable_cash = max(Decimal("0.00"), paid - already_refunded)

    cash_back = min(sale_return.total_refund, refundable_cash)
    write_off = sale_return.total_refund - cash_back

    if write_off > 0:
        sale.balance = max(Decimal("0.00"), sale.balance - write_off)
        sale.save(update_fields=["balance"])

    refund = Refund.objects.create(
        sale_return=sale_return,
        amount=cash_back,
        payment_method=payment_method,
        refunded_by=refunded_by,
        status=Refund.Status.COMPLETED,
    )

    _mark_sale_refunded_if_fully_returned(sale)
    return refund
