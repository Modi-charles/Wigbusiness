from django.contrib import admin
from .models import Supplier ,SupplierPayment, SupplierLedger
# Register your models here.
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "company_name",
        "phone",
        "balance",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "company_name",
        "phone",
        "email",
    )

    ordering = (
        "name",
    )


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):

    list_display = (
        "supplier",
        "amount",
        "payment_method",
        "reference",
        "received_by",
        "payment_date",
    )

    list_filter = (
        "payment_method",
        "payment_date",
    )

    search_fields = (
        "supplier__name",
        "supplier__company_name",
        "reference",
    )

    readonly_fields = (
        "supplier",
        "amount",
        "payment_method",
        "reference",
        "notes",
        "received_by",
        "payment_date",
        "created_at",
    )

@admin.register(SupplierLedger)
class SupplierLedgerAdmin(admin.ModelAdmin):

    list_display = (
        "supplier",
        "transaction_type",
        "amount",
        "balance_after",
        "created_by",
        "created_at",
    )

    list_filter = (
        "transaction_type",
        "created_at",
    )

    search_fields = (
        "supplier__name",
        "supplier__company_name",
        "description",
    )

    readonly_fields = (
        "supplier",
        "transaction_type",
        "amount",
        "balance_after",
        "reference_id",
        "description",
        "created_by",
        "created_at",
    )