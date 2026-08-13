from django.urls import path
from . import views
app_name="purchase"

urlpatterns = [
    path("", views.view_purchase, name="view_purchase"),
    path("add/", views.add_purchase, name="add_purchase"),
    path("<int:id>/", views.purchase_details, name="purchase_details"),
    #path("<int:id>/update/",views.update_purchase,name="update_purchase"),
    path("<int:id>/delete/",views.delete_purchase,name="delete_purchase"),
    path("<int:id>/receive/",views.receive_purchase,name="receive_purchase"),
    path("<int:id>/payment/add/",views.add_purchase_payment,name="add_purchase_payment"),
    path("<int:id>/invoice/",views.purchase_invoice,name="purchase_invoice",),
    path("reports/",views.purchase_reports,name="purchase_reports",),
]