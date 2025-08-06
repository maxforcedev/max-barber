from django.db import models


class Service(models.Model):
    name = models.CharField(max_length=80)
    detail = models.TextField(max_length=150, blank=True, null=True)
    photo = models.ImageField(upload_to='services/', blank=True, null=True)
    duration = models.PositiveIntegerField(help_text='Duração em minutos')
    is_active = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
