from datetime import datetime, timedelta
from rest_framework import serializers
from django.utils import timezone

from services.serializers import ServiceSerializer
from services.models import Service
from barbers.models import WorkingHour, BlockedTime, Barber
from appointments.models import Appointment, AppointmentStatus


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

        weekday = date.weekday()
        working_hours = WorkingHour.objects.filter(barber_id=barber_id, weekday=weekday).first()
        if not working_hours:
            raise serializers.ValidationError({"availability": "Barbeiro(a) não atende neste dia."})

        duration_min = int(service.duration)
        start_exp = working_hours.start_time
        end_exp = working_hours.end_time

        if (datetime.combine(date, start_exp) + timedelta(minutes=duration_min)).time() > end_exp:
            attrs.update({
                "service": service,
                "available_slots": [],
                "message": "Nenhum horário disponível no expediente para a duração do serviço."
            })
            return attrs

        blocked = list(BlockedTime.objects.filter(
            barber_id=barber_id,
            date=date
        ).values_list("start_time", "end_time"))

        busy_appointments = list(Appointment.objects.filter(
            barber_id=barber_id,
            date=date
        ).exclude(status=AppointmentStatus.CANCELED).values_list("start_time", "end_time"))

        def overlaps(a_start, a_end, b_start, b_end):
            return a_start < b_end and a_end > b_start

        slots = []
        t0 = datetime.combine(date, start_exp)
        end_boundary = datetime.combine(date, end_exp)

        step = timedelta(minutes=duration_min)
        while True:
            t1 = t0 + step
            if t1 > end_boundary:
                break
            slot_start = t0.time()
            slot_end = t1.time()

            invalid = False

            for b_start, b_end in blocked:
                if overlaps(slot_start, slot_end, b_start, b_end):
                    invalid = True
                    break

            if not invalid:
                for a_start, a_end in busy_appointments:
                    if overlaps(slot_start, slot_end, a_start, a_end):
                        invalid = True
                        break

            now = timezone.localtime()
            if not invalid and date == now.date():
                if datetime.combine(date, slot_start) < now + timedelta(minutes=30):
                    invalid = True

            if not invalid:
                slots.append(slot_start.strftime("%H:%M"))

            t0 += step

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
