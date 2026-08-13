from django.urls import path

from . import views


app_name = "reports"


urlpatterns = [

    path(
        "",
        views.reports_dashboard,
        name="dashboard"
    ),

    path(
        "sales/",
        views.sales_report,
        name="sales_report"
    ),

    path(
        "purchases/",
        views.purchase_report,
        name="purchase_report"
    ),

    path(
        "inventory/",
        views.inventory_report,
        name="inventory_report"
    ),

    path(
        "suppliers/",
        views.supplier_report,
        name="supplier_report"
    ),

    path(
        "customers/",
        views.customer_report,
        name="customer_report"
    ),

    path(
        "profit/",
        views.profit_report,
        name="profit_report"
    ),

    path(
        "financial/",
        views.financial_summary,
        name="financial_summary"
    ),
]