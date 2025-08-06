from django.db import models
from core import choices


class Barber(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='barber')
    status = models.CharField(choices= choices.StatusBarber.choices)
    photo = models.ImageField(blank=True, null=True)
