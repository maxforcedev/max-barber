from django.contrib import admin
from .models import Barber


@admin.register(Barber)
class BarberAdmin(admin.ModelAdmin):
    model = Barber
    list_display = ['get_name', 'get_phone']

    def get_name(self, obj):
        return obj.user.name

    def get_phone(self, obj):
        return obj.user.phone
