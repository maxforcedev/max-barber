from django.db import models


class BarberShop(models.Model):
    name = models.CharField(max_length=100, default='Max Barber')
    description = models.TextField(null=True, blank=True, default="Experiência em cortes e barbas. Tradição, qualidade e estilo em cada atendimento. Agende online e viva uma nova experiência.")
    open_since = models.PositiveIntegerField(default=2025)
    address = models.CharField(max_length=200, default='Duque de Caxias')
    phone = models.CharField(max_length=100, default='21987825934')
    coordenation = models.CharField(max_length=100, default='-22.787954, -43.310263')
