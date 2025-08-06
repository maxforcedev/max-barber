from django.db import models


class Barber(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='barber')
    photo = models.ImageField(blank=True, null=True)
    services = models.ManyToManyField('services.Service', related_name='barbers')
