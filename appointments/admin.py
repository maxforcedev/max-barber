from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'client_name',
        'barber_name',
        'service',
        'date',
        'start_time',
        'end_time',
        'status',
    )
    list_filter = ('status', 'date', 'barber')
    search_fields = ('client__name', 'barber__user__name')
    ordering = ('-date', 'start_time')

    def client_name(self, obj):
        return obj.client.name

    def barber_name(self, obj):
        return obj.barber.user.name
