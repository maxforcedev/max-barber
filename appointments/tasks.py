from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Appointment, AppointmentStatus


@shared_task
def clear_pending_appointments():
    cutoff = timezone.now() - timedelta(minutes=5)
    deleted_count, _ = Appointment.objects.filter(
        status=AppointmentStatus.PENDING,
        created_at__lt=cutoff
    ).delete()
    return f"{deleted_count} agendamentos pendentes excluidos."
