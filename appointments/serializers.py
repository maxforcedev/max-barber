from rest_framework import serializers


class AppointmentCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    phone = serializers.CharField()
    service_id = serializers.IntegerField()
    barber_id = serializers.UUIDField()
    date = serializers.DateField()
    start_time = serializers.TimeField()

    def validate(self, attrs):
        name = attrs.get('name')
        phone = attrs.get('phone')
        service_id = attrs.get('service_id')
        barber_id = attrs.get('barber_id')
        date = attrs.get('date')
        start_time = attrs.get('start_time')
