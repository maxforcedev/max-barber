from rest_framework import serializers
from .models import BarberShop


class BarberShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarberShop
        fields = "__all__"

    def get_queryset(self):
        return BarberShop.objects.all()[:1]
