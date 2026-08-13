from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    Supplier,
    SupplierLedger,
    SupplierPayment,
)


@transaction.atomic
def record_supplier_purchase(
    supplier,
    amount,
    purchase_id=None,
    created_by=None,
    description="",
):
    amount = Decimal(amount)

    if amount <= Decimal("0.00"):
        raise ValidationError(
            "Purchase amount must be greater than zero."
        )

    supplier = Supplier.objects.select_for_update().get(
        pk=supplier.pk
    )

    new_balance = supplier.balance + amount

    ledger_entry = SupplierLedger.objects.create(
        supplier=supplier,
        transaction_type="PURCHASE",
        amount=amount,
        balance_after=new_balance,
        reference_id=purchase_id,
        description=description,
        created_by=created_by,
    )

    supplier.balance = new_balance

    supplier.save(
        update_fields=[
            "balance",
            "updated_at",
        ]
    )

    return ledger_entry


@transaction.atomic
def record_supplier_payment(
    supplier,
    amount,
    payment_method,
    reference="",
    notes="",
    received_by=None,
):
    amount = Decimal(amount)

    if amount <= Decimal("0.00"):
        raise ValidationError(
            "Payment amount must be greater than zero."
        )

    supplier = Supplier.objects.select_for_update().get(
        pk=supplier.pk
    )

    if amount > supplier.balance:
        raise ValidationError(
            "Payment cannot be greater than "
            "the supplier's outstanding balance."
        )

    new_balance = supplier.balance - amount

    payment = SupplierPayment.objects.create(
        supplier=supplier,
        amount=amount,
        payment_method=payment_method,
        reference=reference,
        notes=notes,
        received_by=received_by,
    )

    SupplierLedger.objects.create(
        supplier=supplier,
        transaction_type="PAYMENT",
        amount=-amount,
        balance_after=new_balance,
        reference_id=payment.id,
        description=(
            f"Supplier payment - {payment_method}"
        ),
        created_by=received_by,
    )

    supplier.balance = new_balance

    supplier.save(
        update_fields=[
            "balance",
            "updated_at",
        ]
    )

    return payment
def calculate_supplier_balance(supplier):

    total = Decimal("0.00")

    entries = supplier.ledger_entries.all()

    for entry in entries:
        total += entry.amount

    return total
@transaction.atomic
def reconcile_supplier_balance(supplier):

    supplier = Supplier.objects.select_for_update().get(
        pk=supplier.pk
    )

    calculated_balance = calculate_supplier_balance(
        supplier
    )

    if calculated_balance < Decimal("0.00"):
        raise ValidationError(
            "Calculated supplier balance cannot be negative."
        )

    supplier.balance = calculated_balance

    supplier.save(
        update_fields=[
            "balance",
            "updated_at",
        ]
    )

    return calculated_balance