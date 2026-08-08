from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from .forms import SaleForm, SaleItemFormSet
from .services import create_sale
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from products.models import Product
from django.contrib.auth.decorators import login_required
from .models import Sale,Refund
from django.db.models import Q
from datetime import datetime
from django.core.paginator import Paginator
from .returns import create_sale_return, create_refund, SaleReturn

# Create your views here.
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

                return redirect(
                    "sales:sale_detail",
                    pk=sale.pk,
                )

            except ValidationError as e:
                    sale_form.add_error(None,e.message)
    else:

        sale_form = SaleForm()
        item_formset = SaleItemFormSet()

    return render(request,"sales/create_sale.html",
        {
            "sale_form": sale_form,
            "item_formset": item_formset,
        },
    )
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.prefetch_related(
            "items__product",
            "payments",
        ),
        pk=pk,
    )

    return render(
        request,
        "sales/sale_detail.html",
        {
            "sale": sale,
        },
    )
def product_by_barcode(request):
    barcode = request.GET.get("barcode", "").strip()

    if not barcode:
        return JsonResponse(
            {
                "success": False,
                "message": "Barcode is required.",
            },
            status=400,
        )

    try:
        product = Product.objects.get(
            barcode=barcode,
            status=True,
        )

    except Product.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Product not found.",
            },
            status=404,
        )

    return JsonResponse(
        {
            "success": True,
            "product": {
                "id": product.id,
                "name": product.name,
                "barcode": product.barcode,
                "selling_price": str(
                    product.selling_price
                ),
            },
        }
    )
def sales_history(request):
    sales = (
        Sale.objects
        .select_related(
            "customer",
            "created_by",
        )
        .order_by("-sale_date")
    )

    # Search
    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:
        sales = sales.filter(
            Q(invoice_number__icontains=search)
            |
            Q(customer__name__icontains=search)
        )


    # Status filter
    status = request.GET.get(
        "status",
        ""
    )

    if status:
        sales = sales.filter(
            status=status
        )


    # Payment method filter
    payment_method = request.GET.get(
        "payment_method",
        ""
    )

    if payment_method:
        sales = sales.filter(
            payment_method=payment_method
        )


    # Date filters
    date_from = request.GET.get(
        "date_from",
        ""
    )

    date_to = request.GET.get(
        "date_to",
        ""
    )

    if date_from:
        sales = sales.filter(
            sale_date__date__gte=date_from
        )

    if date_to:
        sales = sales.filter(
            sale_date__date__lte=date_to
        )


    # Pagination
    paginator = Paginator(
        sales,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )


    return render(
        request,
        "sales/sales_history.html",
        {
            "sales": page_obj,

            "search": search,

            "selected_status": status,

            "selected_payment_method":
                payment_method,

            "status_choices":
                Sale.Status.choices,

            "payment_choices":
                Sale.PAYMENT_METHODS,

            "date_from": date_from,

            "date_to": date_to,
        }
    )
@login_required
def create_return(request, pk):

    sale = get_object_or_404(
        Sale.objects.prefetch_related(
            "items__product"
        ),
        pk=pk,
    )


    if request.method == "POST":

        items = []


        for sale_item in sale.items.all():

            quantity = request.POST.get(
                f"quantity_{sale_item.id}",
                "0",
            )


            try:
                quantity = int(quantity)

            except (TypeError, ValueError):

                quantity = 0


            if quantity > 0:

                items.append(
                    {
                        "sale_item": sale_item,
                        "quantity": quantity,
                    }
                )


        reason = request.POST.get(
            "reason",
            "",
        ).strip()


        try:

            sale_return = create_sale_return(
                sale=sale,
                created_by=request.user,
                items=items,
                reason=reason,
            )

        except ValidationError as e:

            return render(
                request,
                "sales/create_return.html",
                {
                    "sale": sale,
                    "error": e.message,
                },
            )


        return redirect(
            "sales:return_detail",
            pk=sale_return.pk,
        )


    return render(
        request,
        "sales/create_return.html",
        {
            "sale": sale,
        },
    )
def create_refund_view(request, pk):

    sale_return = get_object_or_404(
        SaleReturn.objects.select_related(
            "sale",
        ),
        pk=pk,
    )


    if request.method == "POST":

        payment_method = request.POST.get(
            "payment_method"
        )


        try:

            refund = create_refund(
                sale_return=sale_return,
                refunded_by=request.user,
                payment_method=payment_method,
            )

        except ValidationError as e:

            return render(
                request,
                "sales/create_refund.html",
                {
                    "sale_return": sale_return,
                    "error": e.message,
                    "payment_choices":
                        Sale.PAYMENT_METHODS,
                },
            )


        return redirect(
            "sales:refund_detail",
            pk=refund.pk,
        )


    return render(
        request,
        "sales/create_refund.html",
        {
            "sale_return": sale_return,
            "payment_choices":
                Sale.PAYMENT_METHODS,
        },
    )
@login_required
def return_detail(request, pk):

    sale_return = get_object_or_404(
        SaleReturn.objects.select_related(
            "sale",
            "created_by",
        ).prefetch_related(
            "items__sale_item__product"
        ),
        pk=pk,
    )

    return render(
        request,
        "sales/return_detail.html",
        {
            "sale_return": sale_return,
        },
    )
def return_history(request):

    returns = (
        SaleReturn.objects
        .select_related(
            "sale",
            "created_by",
        )
        .prefetch_related(
            "items__sale_item__product",
        )
        .order_by("-created_at")
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:
        returns = returns.filter(
            Q(return_number__icontains=search)
            |
            Q(sale__invoice_number__icontains=search)
        )

    status = request.GET.get(
        "status",
        ""
    )

    if status:
        returns = returns.filter(
            status=status
        )

    paginator = Paginator(
        returns,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

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
def refund_history(request):

    refunds = (
        Refund.objects
        .select_related(
            "sale_return",
            "sale_return__sale",
            "refunded_by",
        )
        .order_by("-created_at")
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:
        refunds = refunds.filter(
            Q(sale_return__return_number__icontains=search)
            |
            Q(sale_return__sale__invoice_number__icontains=search)
        )

    payment_method = request.GET.get(
        "payment_method",
        ""
    )

    if payment_method:
        refunds = refunds.filter(
            payment_method=payment_method
        )

    status = request.GET.get(
        "status",
        ""
    )

    if status:
        refunds = refunds.filter(
            status=status
        )

    paginator = Paginator(
        refunds,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "sales/refund_history.html",
        {
            "refunds": page_obj,
            "search": search,
            "selected_payment_method": payment_method,
            "selected_status": status,
            "payment_choices": Sale.PAYMENT_METHODS,
            "status_choices": Refund.Status.choices,
        },
    )