from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Max
from .models import Customer
from .forms import CustomerForm


@login_required
def customer_list(request):

    query = request.GET.get("q", "").strip()

    customers = Customer.objects.filter(
        is_active=True
    )

    if query:
        customers = customers.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        )

    customers = customers.annotate(

        total_sales=Count(
            "sales",
            filter=Q(
                sales__status="COMPLETED"
            ),
            distinct=True
        ),

        total_spent=Sum(
            "sales__total_amount",
            filter=Q(
                sales__status="COMPLETED"
            )
        ),

        total_paid=Sum(
            "sales__paid_amount",
            filter=Q(
                sales__status="COMPLETED"
            )
        ),

        outstanding_balance=Sum(
            "sales__balance",
            filter=Q(
                sales__status="COMPLETED"
            )
        ),

        last_purchase=Max(
            "sales__sale_date",
            filter=Q(
                sales__status="COMPLETED"
            )
        )

    )

    customers = customers.order_by(
        "first_name"
    )

    paginator = Paginator(
        customers,
        20
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        "page_obj": page_obj,
        "query": query,
    }

    return render(
        request,
        "customers/customer_list.html",
        context
    )

@login_required
def customer_detail(request, pk):

    customer = get_object_or_404(
        Customer,
        pk=pk,
        is_active=True
    )

    sales = customer.sales.all().order_by(
        "-sale_date"
    )

    total_spent = sum(
        sale.total_amount
        for sale in sales
        if sale.status == "COMPLETED"
    )

    paginator = Paginator(
        sales,
        10
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        "customer": customer,
        "sales": page_obj,
        "page_obj": page_obj,
        "total_spent": total_spent,
    }

    return render(
        request,
        "customers/customer_details.html",
        context
    )
@login_required
def customer_create(request):

    if request.method == "POST":

        form = CustomerForm(request.POST)

        if form.is_valid():

            customer = form.save()

            customer_name = (
                f"{customer.first_name} "
                f"{customer.last_name}"
            ).strip()

            messages.success(
                request,
                f'Customer "{customer_name}" added successfully.'
            )

            return redirect(
                "customers:customer_details",
                pk=customer.pk
            )

    else:

        form = CustomerForm()

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "action": "Add",
        }
    )

@login_required
def customer_update(request, pk):

    customer = get_object_or_404(
        Customer,
        pk=pk,
        is_active=True
    )

    if request.method == "POST":

        form = CustomerForm(
            request.POST,
            instance=customer
        )

        if form.is_valid():

            form.save()

            customer_name = (
                f"{customer.first_name} "
                f"{customer.last_name}"
            ).strip()

            messages.success(
                request,
                f'Customer "{customer_name}" updated successfully.'
            )

            return redirect(
                "customers:customer_details",
                pk=customer.pk
            )

    else:

        form = CustomerForm(
            instance=customer
        )

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "action": "Edit",
            "customer": customer,
        }
    )

@login_required
def customer_delete(request, pk):

    customer = get_object_or_404(
        Customer,
        pk=pk,
        is_active=True
    )

    customer_name = (
        f"{customer.first_name} "
        f"{customer.last_name}"
    ).strip()

    if request.method == "POST":

        customer.is_active = False

        customer.save(
            update_fields=["is_active"]
        )

        messages.success(
            request,
            f'Customer "{customer_name}" deactivated.'
        )

        return redirect(
            "customers:customer_list"
        )

    return render(
        request,
        "customers/customer_confirm_delete.html",
        {
            "customer": customer
        }
    )