from rest_framework import serializers
from django.utils import timezone
from core.utils import get_available_slots
from services.serializers import ServiceSerializer
from services.models import Service
from barbers.models import Barber


class BarberSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = Barber
        fields = ["id", "name", "phone", "photo", "services"]


class BarberAvailabilitySerializer(serializers.Serializer):
    date = serializers.DateField(required=True)
    service_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        barber_id = self.context.get("barber_id")
        if not barber_id:
            raise serializers.ValidationError({"barber_id": "Barbeiro não informado no contexto."})

        date = attrs["date"]
        service_id = attrs["service_id"]

        if date < timezone.localdate():
            raise serializers.ValidationError({"date": "Data no passado não é permitida."})

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError({"service_id": "Serviço inválido."})

        slots = get_available_slots(barber_id, date, service)
        attrs.update({
            "service": service,
            "available_slots": slots,
        })
        if not slots:
            attrs["message"] = "Nenhum horário disponível para este dia."
        return attrs

    def to_representation(self, instance):
        barber_id = self.context.get("barber_id")
        data = self.validated_data
        return {
            "barber_id": barber_id,
            "date": data["date"].strftime("%Y-%m-%d"),
            "service_id": data["service_id"],
            "service_duration": int(data["service"].duration),
            "available_slots": data.get("available_slots", []),
            **({"message": data["message"]} if "message" in data else {})
        }
