from django.contrib import admin
from .models import Barber


class BarberAdmin(admin.ModelAdmin):
    model = Barber
    list_display = ['user__name', ]