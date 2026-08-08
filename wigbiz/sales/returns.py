from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from inventory.models import Inventory, InventoryTransaction
from .models import SaleReturn, SaleReturnItem,Sale


def generate_return_number():
    latest_return = (
        SaleReturn.objects
        .order_by("-created_at")
        .first()
    )

    if latest_return is None:
        return "RET-000001"

    number = latest_return.return_number[4:]
    number = int(number)
    number += 1

    return f"RET-{number:06d}"


@transaction.atomic
def create_sale_return(
    sale,
    created_by,
    items,
    reason="",
):
    if not items:
        raise ValidationError(
            "A return must contain at least one item."
        )

    if sale.status == sale.Status.CANCELLED:
        raise ValidationError(
            "Cancelled sales cannot be returned."
        )

    if sale.status == sale.Status.REFUNDED:
        raise ValidationError(
            "This sale has already been fully refunded."
        )

    sale_return = SaleReturn.objects.create(
        sale=sale,
        return_number=generate_return_number(),
        reason=reason,
        created_by=created_by,
        status=SaleReturn.Status.PENDING,
    )

    total_refund = Decimal("0.00")

    for item in items:
        sale_item = item["sale_item"]
        quantity = item["quantity"]

        if quantity <= 0:
            raise ValidationError(
                "Return quantity must be greater than zero."
            )

        if sale_item.sale_id != sale.id:
            raise ValidationError(
                "The selected item does not belong to this sale."
            )

        already_returned = (
            SaleReturnItem.objects
            .filter(
                sale_item=sale_item,
                sale_return__status=SaleReturn.Status.COMPLETED,
            )
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        remaining_quantity = sale_item.quantity - already_returned

        if quantity > remaining_quantity:
            raise ValidationError(
                f"Cannot return {quantity} "
                f"unit(s) of "
                f"{sale_item.product.name}. "
                f"Only {remaining_quantity} "
                f"unit(s) can be returned."
            )

        refund_amount = sale_item.selling_price * quantity

        SaleReturnItem.objects.create(
            sale_return=sale_return,
            sale_item=sale_item,
            quantity=quantity,
            refund_amount=refund_amount,
        )

        total_refund += refund_amount

        inventory = (
            Inventory.objects
            .select_for_update()
            .get(product=sale_item.product)
        )

        inventory.quantity_available += quantity
        inventory.quantity_sold -= quantity

        inventory.save(
            update_fields=[
                "quantity_available",
                "quantity_sold",
                "updated_at",
            ]
        )

        InventoryTransaction.objects.create(
            product=sale_item.product,
            transaction_type="RETURN",
            quantity=quantity,
            reference_id=sale_return.id,
            description=(
                f"Returned {quantity} "
                f"unit(s) of "
                f"{sale_item.product.name}"
            ),
            created_by=created_by,
        )

    sale_return.total_refund = total_refund
    sale_return.status = SaleReturn.Status.COMPLETED
    sale_return.save(
        update_fields=[
            "total_refund",
            "status",
        ]
    )

    return sale_return
@transaction.atomic
def create_refund(
    sale_return,
    refunded_by,
    payment_method,
):
    from .models import Refund

    if sale_return.status != SaleReturn.Status.COMPLETED:
        raise ValidationError(
            "Only completed returns can be refunded."
        )

    if hasattr(sale_return, "refund"):
        raise ValidationError(
            "This return has already been refunded."
        )

    if sale_return.total_refund <= Decimal("0.00"):
        raise ValidationError(
            "Refund amount must be greater than zero."
        )

    if payment_method not in dict(Sale.PAYMENT_METHODS):
        raise ValidationError(
            "Invalid payment method."
        )

    refund = Refund.objects.create(
        sale_return=sale_return,
        amount=sale_return.total_refund,
        payment_method=payment_method,
        refunded_by=refunded_by,
        status=Refund.Status.COMPLETED,
    )

    return refund