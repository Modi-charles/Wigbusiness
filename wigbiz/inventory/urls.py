from django.urls import path
from .import views
app_name="inventory"
urlpatterns=[
path("",views.view_inventory, name="view_inventory"),
path("<int:id>/update", views.update_inventory, name="update_inventory"),
path("<int:id>/delete", views.delete_inventory, name="delete_inventory"),
path("history/",views.inventory_history,name="inventory_history"),
]