from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration', 'price', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
