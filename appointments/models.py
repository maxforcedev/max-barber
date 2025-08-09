from django.db import models
from django.utils import timezone
from core.choices import AppointmentStatus, UserRole


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
        default=AppointmentStatus.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)

    cancel_reason = models.TextField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    canceled_by = models.CharField(max_length=20, choices=UserRole.choices, blank=True, null=True)

    def cancel(self, reason="", canceled_by="client"):
        self.status = AppointmentStatus.CANCELED
        self.cancel_reason = reason
        self.canceled_at = timezone.now()
        self.canceled_by = canceled_by
        self.save()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['barber', 'date', 'start_time'],
                name='unique_appointment_slot'
            )
        ]
