from django.shortcuts import render
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from .forms import SaleForm, SaleItemFormSet
from .services import create_sale
from django.contrib.auth.decorators import login_required
from .models import Sale
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

    sale = (
        Sale.objects
        .select_related("customer", "created_by")
        .prefetch_related(
            "items__product",
            "payments",
        )
        .get(pk=pk)
    )

    return render(
        request,
        "sales/sale_detail.html",
        {
            "sale": sale,
        },
    )