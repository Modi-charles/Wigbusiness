from django.shortcuts import render, redirect
from .models import Product
from inventory.models import Inventory
from .forms import ProductForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

# Create your views here.
@login_required
def dashboard_home(request):
    return render(request, "dashboard/home.html")
def add_product(request):
    if request.method == "POST":

        form = ProductForm(
            request.POST,
            request.FILES
        )


        if form.is_valid():

            product = form.save()

            Inventory.objects.create(
                product=product,
                quantity_available=0
            )

            return redirect(
                "view_product"
            )


    else:

        form = ProductForm()

    return render(request, "Products/add_products.html",{"form":form})
     
def view_product(request):
    query = request.GET.get("search")
    products=Product.objects.all().order_by("-created_at")
    if query:
        products = products.filter(
            name__icontains=query
        )
    context={
        "products":products,
        "search": query
        }
    return render(request, "Products/view_products.html",context)

def delete_product(request, id):
    product=get_object_or_404(Product, id=id)
    if request.method =='POST':
        product.delete()
        messages.success(request,"Product Deleted Succesfully") 
        return redirect("view_products")
    return render(request,"Products/delete_product.html",{"product":product})

def product_detail(request,id):
    product = get_object_or_404(Product,id=id)
    return render(request,"products/product_detail.html",{"product":product})

def edit_product(request, id):
    product = get_object_or_404(Product,id=id)


    if request.method == "POST":

        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product
        )


        if form.is_valid():

            form.save()

            return redirect(
                "view_product"
            )


    else:

        form = ProductForm(
            instance=product
        )


    return render(
        request,
        "products/edit_product.html",
        {
            "form": form,
            "product": product
        }
    )