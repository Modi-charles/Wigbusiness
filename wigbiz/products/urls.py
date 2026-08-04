from django.urls import path
from . import views
urlpatterns=[
    path("",views.view_product,name="view_product"),
    path("add/",views.add_product,name="add_product"),
    path("<int:id>/",views.product_detail,name="product-detail"),
    path("<int:id>/edit/",views.edit_product,name="product-edit" ),
    path("<int:id>/delete/",views.delete_product,name="product-delete")
    ]