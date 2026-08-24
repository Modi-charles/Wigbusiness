from django.urls import path
from . import views


urlpatterns = [
    path(
        "create/",
        views.create_expense,
        name="create_expense"
    ),
     path(
        "",
        views.expense_list,
        name="expense_list"
    ),

]
