from django.urls import path
from . import views

app_name='expenses'

urlpatterns = [
    path("create/",views.create_expense,name="create_expense"),
    path("",views.expense_list,name="expense_list"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("categories/<int:pk>/toggle/", views.category_toggle, name="category_toggle"),
    path("<int:pk>/", views.expense_detail, name="expense_detail"),
    path("<int:pk>/approve/", views.expense_approve, name="expense_approve"),
    path("<int:pk>/reject/", views.expense_reject, name="expense_reject"),
    path("<int:pk>/delete/", views.expense_delete, name="expense_delete"),
]
