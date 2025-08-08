from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "admin", "Dono(a)"
    CLIENT = "client", "Cliente"
    BARBER = "barber", "Barbeiro(a)"


class AppointmentStatus(models.TextChoices):
    PENDING = 'pendent', 'Pendente'
    SCHEDULED = 'scheduled', 'Agendado'
    COMPLETED = 'completed', 'Concluído'
    CANCELED = 'canceled', 'Cancelado'
    NO_SHOW = 'no_show', 'Não compareceu'
