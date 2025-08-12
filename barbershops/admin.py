from django.contrib import admin
from .models import BarberShop


@admin.register(BarberShop)
class BarberShopAdmin(admin.ModelAdmin):
    list_display = ("name", "open_since", "phone")
    search_fields = ("name", "address", "phone")
    list_filter = ("open_since",)
    ordering = ("name",)
