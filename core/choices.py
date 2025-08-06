from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    CLIENT = "client", "Client"
    BARBER = "barber", "Barber"


class AppointmentStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Agendado'
    COMPLETED = 'completed', 'Concluído'
    CANCELED = 'canceled', 'Cancelado'
    NO_SHOW = 'no_show', 'Não compareceu'
