from django.db import models
from core.choices import AppointmentStatus


class Appointment(models.Model):
    client = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='appointments')
    barber = models.ForeignKey('barbers.Barber', on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey('services.Service', on_delete=models.PROTECT)

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.SCHEDULED
    )

    created_at = models.DateTimeField(auto_now_add=True)
