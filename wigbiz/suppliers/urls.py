from django.urls import path
from . import views


app_name = "suppliers"


urlpatterns = [

    path(
        "",
        views.supplier_list,
        name="supplier_list"
    ),

    path(
        "add/",
        views.supplier_create,
        name="supplier_create"
    ),

    path(
        "<int:pk>/",
        views.supplier_detail,
        name="supplier_detail"
    ),

    path(
        "<int:pk>/edit/",
        views.supplier_update,
        name="supplier_update"
    ),

    path(
        "<int:pk>/deactivate/",
        views.supplier_deactivate,
        name="supplier_deactivate"
    ),

    path(
        "<int:pk>/activate/",
        views.supplier_activate,
        name="supplier_activate"
    ),

    path(
        "<int:pk>/payment/",
        views.supplier_payment,
        name="supplier_payment"
    ),
    path(
    "<int:pk>/ledger/",
    views.supplier_ledger,
    name="supplier_ledger"
),
path(
    "<int:pk>/statement/",
    views.supplier_statement,
    name="supplier_statement"
),
]