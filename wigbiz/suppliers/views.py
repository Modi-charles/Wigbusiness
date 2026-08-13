from decimal import Decimal

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum

from .models import Supplier
from .forms import (
    SupplierForm,
    SupplierPaymentForm,
)
from .services import record_supplier_payment


@login_required
def supplier_list(request):

    query = request.GET.get(
        "q",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        "active"
    ).strip()

    suppliers = Supplier.objects.all()


    # -------------------------
    # STATUS FILTER
    # -------------------------

    if status == "active":

        suppliers = suppliers.filter(
            is_active=True
        )

    elif status == "inactive":

        suppliers = suppliers.filter(
            is_active=False
        )


    # -------------------------
    # SEARCH
    # -------------------------

    if query:

        suppliers = suppliers.filter(

            Q(name__icontains=query)

            | Q(company_name__icontains=query)

            | Q(phone__icontains=query)

            | Q(email__icontains=query)

        )


    suppliers = suppliers.order_by(
        "name"
    )


    # -------------------------
    # SUMMARY
    # -------------------------

    total_suppliers = Supplier.objects.count()

    active_suppliers = Supplier.objects.filter(
        is_active=True
    ).count()

    inactive_suppliers = Supplier.objects.filter(
        is_active=False
    ).count()

    total_balance = (
        Supplier.objects.filter(
            is_active=True
        ).aggregate(
            total=Sum("balance")
        )["total"]
        or Decimal("0.00")
    )


    # -------------------------
    # PAGINATION
    # -------------------------

    paginator = Paginator(
        suppliers,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )


    context = {
        "page_obj": page_obj,
        "query": query,
        "status": status,

        "total_suppliers": total_suppliers,
        "active_suppliers": active_suppliers,
        "inactive_suppliers": inactive_suppliers,
        "total_balance": total_balance,
    }

    return render(
        request,
        "suppliers/supplier_list.html",
        context
    )


@login_required
def supplier_detail(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    purchases = supplier.purchases.all().order_by(
        "-purchase_date"
    )

    payments = supplier.payments.select_related(
        "received_by"
    ).order_by(
        "-payment_date"
    )

    context = {
        "supplier": supplier,
        "purchases": purchases,
        "payments": payments,
    }

    return render(
        request,
        "suppliers/supplier_detail.html",
        context
    )


@login_required
def supplier_create(request):

    if request.method == "POST":

        form = SupplierForm(
            request.POST
        )

        if form.is_valid():

            supplier = form.save()

            messages.success(
                request,
                "Supplier added successfully."
            )

            return redirect(
                "suppliers:supplier_detail",
                pk=supplier.pk
            )

    else:

        form = SupplierForm()


    return render(
        request,
        "suppliers/supplier_form.html",
        {
            "form": form,
            "action": "Add",
        }
    )


@login_required
def supplier_update(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    if request.method == "POST":

        form = SupplierForm(
            request.POST,
            instance=supplier
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Supplier updated successfully."
            )

            return redirect(
                "suppliers:supplier_detail",
                pk=supplier.pk
            )

    else:

        form = SupplierForm(
            instance=supplier
        )


    return render(
        request,
        "suppliers/supplier_form.html",
        {
            "form": form,
            "action": "Edit",
            "supplier": supplier,
        }
    )


@login_required
def supplier_deactivate(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    if request.method == "POST":

        supplier.is_active = False

        supplier.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        messages.success(
            request,
            "Supplier deactivated successfully."
        )

        return redirect(
            "suppliers:supplier_list"
        )


    return render(
        request,
        "suppliers/supplier_confirm_deactivate.html",
        {
            "supplier": supplier
        }
    )


@login_required
def supplier_activate(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    if request.method == "POST":

        supplier.is_active = True

        supplier.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        messages.success(
            request,
            "Supplier activated successfully."
        )

    return redirect(
        "suppliers:supplier_detail",
        pk=supplier.pk
    )


@login_required
def supplier_payment(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    if request.method == "POST":

        form = SupplierPaymentForm(
            request.POST
        )

        if form.is_valid():

            try:

                payment = record_supplier_payment(
                    supplier=supplier,
                    amount=form.cleaned_data["amount"],
                    payment_method=form.cleaned_data[
                        "payment_method"
                    ],
                    reference=form.cleaned_data[
                        "reference"
                    ],
                    notes=form.cleaned_data[
                        "notes"
                    ],
                    received_by=request.user,
                )

            except Exception as error:

                form.add_error(
                    None,
                    str(error)
                )

            else:

                messages.success(
                    request,
                    "Supplier payment recorded successfully."
                )

                return redirect(
                    "suppliers:supplier_detail",
                    pk=supplier.pk
                )

    else:

        form = SupplierPaymentForm()


    return render(
        request,
        "suppliers/supplier_payment.html",
        {
            "supplier": supplier,
            "form": form,
        }
    )
@login_required
def supplier_ledger(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    entries = supplier.ledger_entries.select_related(
        "created_by"
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "suppliers/supplier_ledger.html",
        {
            "supplier": supplier,
            "entries": entries,
        }
    )
@login_required
def supplier_statement(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    entries = supplier.ledger_entries.select_related(
        "created_by"
    ).order_by(
        "created_at"
    )

    context = {
        "supplier": supplier,
        "entries": entries,
    }

    return render(
        request,
        "suppliers/supplier_statement.html",
        context
    )