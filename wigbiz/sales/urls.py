from django.urls import path
from .import views

app_name = "sales"

urlpatterns = [
    path("create/", views.create_sale_view, name="create_sale",),
    path("<int:pk>/",views.sale_detail,name="sale_detail",),
]