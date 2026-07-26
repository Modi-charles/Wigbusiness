from django.contrib import admin
from .models import Inventory, InventoryTransaction
# Register your models here.
admin.site.register(Inventory)
admin.site.register(InventoryTransaction)