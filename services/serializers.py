from rest_framework import serializers
from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    duration_min = serializers.IntegerField(source="duration")
    price = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ["id", "name", "duration_min", "price"]

    def get_price(self, obj):
        return float(obj.price)
