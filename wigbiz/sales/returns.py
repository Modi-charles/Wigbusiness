from .models import SaleReturn, SaleReturnItem, Refund
from inventory.models import Inventory, InventoryTransaction
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

def generate_return_number():
    """Generate unique return number."""
    from datetime import datetime
    latest = SaleReturn.objects.all().order_by('-id').first()
    num = (latest.id + 1) if latest else 1
    return f"RET-{datetime.now().strftime('%Y%m%d')}-{num:06d}"

@transaction.atomic
def create_sale_return(sale, created_by, items, reason=""):
    """
    Create a sale return with validation.
    items: list of dicts with 'sale_item' and 'quantity' keys
    """
    if not items:
        raise ValidationError("Return must contain at least one item.")
    
    total_refund = 0
    
    sale_return = SaleReturn.objects.create(
        sale=sale,
        return_number=generate_return_number(),
        reason=reason,
        created_by=created_by,
        status=SaleReturn.Status.PENDING,
    )
    
    for item_data in items:
        sale_item = item_data['sale_item']
        quantity = item_data['quantity']
        
        if quantity <= 0 or quantity > sale_item.quantity:
            raise ValidationError(
                f"Invalid return quantity for {sale_item.product.name}."
            )
        
        refund_amount = quantity * sale_item.selling_price
        total_refund += refund_amount
        
        SaleReturnItem.objects.create(
            sale_return=sale_return,
            sale_item=sale_item,
            quantity=quantity,
            refund_amount=refund_amount,
        )
    
    sale_return.total_refund = total_refund
    sale_return.save(update_fields=['total_refund'])
    
    return sale_return


def approve_sale_return(sale_return, approved_by, approval_note=""):
    """
    Approve a sale return and restore inventory.
    """
    if sale_return.status != SaleReturn.Status.PENDING:
        raise ValidationError("This return is not pending approval.")
    
    with transaction.atomic():
        # FIXED: Restore inventory for each returned item
        for return_item in sale_return.items.all():
            sale_item = return_item.sale_item
            product = sale_item.product
            quantity = return_item.quantity
            
            # Update inventory
            inventory = Inventory.objects.select_for_update().get(
                product=product
            )
            inventory.quantity_available += quantity
            inventory.quantity_sold = max(0, inventory.quantity_sold - quantity)
            inventory.save(
                update_fields=['quantity_available', 'quantity_sold', 'updated_at']
            )
            
            # Create inventory transaction for return
            InventoryTransaction.objects.create(
                product=product,
                transaction_type="RETURN",
                quantity=quantity,
                reference_id=sale_return.id,
                description=f"Returned {quantity} unit(s) of {product.name} (Return: {sale_return.return_number})",
                created_by=approved_by,
            )
        
        # Update sale return status
        sale_return.status = SaleReturn.Status.APPROVED
        sale_return.approved_by = approved_by
        sale_return.approved_at = timezone.now()
        sale_return.approval_note = approval_note
        sale_return.save(
            update_fields=['status', 'approved_by', 'approved_at', 'approval_note']
        )


def reject_sale_return(sale_return, rejection_reason=""):
    """
    Reject a sale return.
    """
    if sale_return.status != SaleReturn.Status.PENDING:
        raise ValidationError("This return is not pending approval.")
    
    sale_return.status = SaleReturn.Status.REJECTED
    sale_return.rejection_reason = rejection_reason
    sale_return.save(
        update_fields=['status', 'rejection_reason']
    )


@transaction.atomic
def create_refund(sale_return, refunded_by, payment_method):
    """
    Create a refund for an approved return.
    """
    if sale_return.status != SaleReturn.Status.APPROVED:
        raise ValidationError(
            "Sale return must be approved before creating a refund."
        )
    
    if not payment_method:
        raise ValidationError("Payment method is required.")
    
    refund = Refund.objects.create(
        sale_return=sale_return,
        amount=sale_return.total_refund,
        payment_method=payment_method,
        refunded_by=refunded_by,
        status=Refund.Status.COMPLETED,
    )
    
    # Mark return as completed
    sale_return.status = SaleReturn.Status.COMPLETED
    sale_return.save(update_fields=['status'])
    
    # FIXED: Update customer balance to reduce what they owe (refund credit)
    sale = sale_return.sale
    if sale.customer:
        sale.customer.sync_balance()
    
    return refund
