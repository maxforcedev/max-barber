from rest_framework import serializers
from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    duration_min = serializers.IntegerField(source='duration')
    price = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['id', 'name', 'duration_min', 'price', 'detail', 'is_popular', 'photo']

    def get_price(self, obj):
        return float(obj.price)

    def get_photo(self, obj):
        request = self.context.get('request')
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url)
        return None
