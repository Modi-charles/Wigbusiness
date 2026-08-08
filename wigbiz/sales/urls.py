from django.urls import path
from .import views

app_name = "sales"

urlpatterns = [
    path("create/", views.create_sale_view, name="create_sale",),
    path("<int:pk>/",views.sale_detail,name="sale_detail",),
    path("product-by-barcode/",views.product_by_barcode,name="product_by_barcode",),
    path("history/",views.sales_history,name="sales_history",),
    path("<int:pk>/return/",views.create_return,name="create_return",),
    path("returns/<int:pk>/refund/",views.create_refund_view,name="create_refund",),
    path("returns/<int:pk>/",views.return_detail,name="return_detail",),
    path("returns/",views.return_history,name="return_history",),
    path("refunds/",views.refund_history,name="refund_history",),
]