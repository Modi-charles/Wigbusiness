from .models import Sale, SaleItem, Payment, InvoiceSequence
from django.db import transaction
from decimal import Decimal
from inventory.models import Inventory, InventoryTransaction
from django.core.exceptions import ValidationError

def generate_invoice_number():
    sequence, created = InvoiceSequence.objects.get_or_create(
        name="SALES",
        defaults={"last_number": 0},
    )
    sequence = InvoiceSequence.objects.select_for_update().get(
        pk=sequence.pk
    )

    sequence.last_number += 1
    sequence.save(update_fields=["last_number"])

    return f"INV-{sequence.last_number:06d}"

def create_sale(
    customer,
    created_by,
    items,
    discount=Decimal("0.00"),
    tax=Decimal("0.00"),
    payment_method=None,
    amount_paid=Decimal("0.00"),
    ):
    with transaction.atomic():
#--------------create sale---------------------------
        if not items:
            raise ValidationError(
                "A sale must contain at least one item."
            )

        if discount < Decimal("0.00"):
            raise ValidationError(
                "Discount cannot be negative."
            )

        if tax < Decimal("0.00"):
            raise ValidationError(
                "Tax cannot be negative."
            )

        if amount_paid < Decimal("0.00"):
            raise ValidationError(
                "Amount paid cannot be negative."
            )
        
        sale=Sale.objects.create(
            customer=customer,
            invoice_number=generate_invoice_number(),
            discount=discount,
            tax=tax,
            payment_method=payment_method,
            created_by=created_by,
            status=Sale.Status.DRAFT,

        )
        subtotal=Decimal("0.00")
#---------------Create Sale Items----------------------
        for item in items:
            product=item["product"]
            quantity=item["quantity"]
            if quantity <= 0:
                raise ValidationError(
            f"Quantity for {product.name} must be greater than zero."
        )
           
#-----------------------dynamic changes in the inventory-----------------------------------
            inventory=Inventory.objects.select_for_update().get(
                product=product        )
            if quantity > inventory.quantity_available:
                raise ValidationError(
                    f"{product.name} is not enough in the stock."
                    f"Available: {inventory.quantity_available}."
                    )
            selling_price=product.selling_price
            sale_item=SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                selling_price=selling_price,
                    )   
            subtotal+=sale_item.line_total
            inventory.quantity_available -=quantity
            inventory.quantity_sold+=quantity
            inventory.save(
                update_fields=[
                    "quantity_available",
                    "quantity_sold",
                    "updated_at",
                ]
            )
#------------------------transaction history-------------------------------
            InventoryTransaction.objects.create(
                product=product,
                transaction_type="SALE",
                quantity=-quantity,
                reference_id=sale.id,
                description=f"Sold {quantity} unit(s) of {product.name}",
                created_by=created_by,
                )
#-----------------validate Discount------------------
        if discount > subtotal:
            raise ValidationError(
                "Discount cannot be greater than subtotal."
            )
#-----------------Calculate Sale Totals----------------
        taxable_amount =subtotal-discount
        total_amount =taxable_amount+tax
        if amount_paid < Decimal("0.00"):
            raise ValidationError(
                "Payment cannot be negative."
            )

        if amount_paid > total_amount:
            raise ValidationError(
                "Please wait for balance."
            )
        balance =total_amount-amount_paid 
#------------------update sale-------------------------
        sale.subtotal=subtotal
        sale.total_amount=total_amount
        sale.paid_amount=amount_paid
        sale.balance=balance  
       
#-------------------Create Payment----------------------
        if amount_paid > Decimal("0.00"):
            if payment_method is None:
                raise ValidationError(
                    "Payment method is required when payment is made."
                )
            Payment.objects.create(
                sale=sale,
                amount=amount_paid,
                payment_method=payment_method,
                received_by=created_by,
                status=Payment.Status.COMPLETED,
            )
        sale.status=Sale.Status.COMPLETED
        sale.save(
            update_fields=[
                "subtotal",
                "discount",
                "tax",
                "total_amount",
                "paid_amount",
                "balance",
                "payment_method",
                "status",
            ]
        )
        return sale
    