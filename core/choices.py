from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    CLIENT = "client", "Client"
    BARBER = "barber", "Barber"


class StatusBarber(models.TextChoices):
    ACTIVE = 'active', 'Ativo'
    INACTIVE = 'inactive', 'Inativo'
