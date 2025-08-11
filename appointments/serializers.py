import redis
from datetime import datetime, timedelta
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from core.utils import clean_phone, generate_code, get_available_slots
from core.choices import AppointmentStatus
from barbers.models import WorkingHour, BlockedTime
from accounts.models import User
from services.models import Service
from .models import Appointment

from django.conf import settings
r = redis.Redis.from_url(settings.REDIS_URL)


class AppointmentSerializer(serializers.ModelSerializer):
    barber = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ["id", "status", "date", "start_time", "end_time", "barber", "service", "cancel_reason", "canceled_at", "canceled_by"]

    def get_barber(self, obj):
        return {
            "id": obj.barber.id,
            "name": obj.barber.user.name,
            "phone": obj.barber.user.phone,
            "photo": obj.barber.photo.url if obj.barber.photo else None
        }

    def get_service(self, obj):
        return {
            "id": obj.service.id,
            "name": obj.service.name,
            "price": float(obj.service.price),
            "duration_min": obj.service.duration
        }


class AppointmentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    service_id = serializers.IntegerField()
    barber_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField()

    def validate(self, attrs):
        request = self.context.get("request")
        is_public = not (request and request.user and request.user.is_authenticated)

        phone = attrs.get("phone")
        service_id = attrs.get("service_id")
        barber_id = attrs.get("barber_id")
        date = attrs.get("date")
        start_time = attrs.get("start_time")

        # 1) Público precisa fornecer phone (e opcionalmente name)
        if is_public:
            if not phone:
                raise serializers.ValidationError({"phone": "Este campo é obrigatório."})
            phone = clean_phone(phone)
            attrs["phone"] = phone  # só anexa no fluxo público

        # 2) Regras de agenda
        weekday = date.weekday()

        working_hours = WorkingHour.objects.filter(barber_id=barber_id, weekday=weekday).first()
        if not working_hours:
            raise serializers.ValidationError("Barbeiro(a) não irá funcionar nesse dia.")

        if not (working_hours.start_time <= start_time < working_hours.end_time):
            raise serializers.ValidationError("Horário fora do expediente do barbeiro.")

        is_blocked = BlockedTime.objects.filter(
            barber_id=barber_id,
            date=date,
            start_time__lte=start_time,
            end_time__gt=start_time,
        ).exists()
        if is_blocked:
            raise serializers.ValidationError("Esse horário não está mais disponível.")

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError("Serviço inválido.")

        slots = get_available_slots(barber_id, date, service)
        if start_time.strftime("%H:%M") not in slots:
            raise serializers.ValidationError("Horário inválido ou indisponível.")

        duration = service.duration
        start_dt = datetime.combine(date, start_time)
        end_dt = start_dt + timedelta(minutes=duration)
        end_time = end_dt.time()

        conflict = Appointment.objects.filter(
            barber_id=barber_id,
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exclude(status=AppointmentStatus.CANCELED).exists()
        if conflict:
            raise serializers.ValidationError("Esse horário não está mais disponível.")

        attrs["service"] = service
        attrs["end_time"] = end_time
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        service = validated_data["service"]
        barber = validated_data["barber_id"]
        date = validated_data["date"]
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]

        if request and request.user and request.user.is_authenticated:
            user = request.user
            appointment = Appointment.objects.create(
                client=user,
                service=service,
                barber_id=barber,
                date=date,
                start_time=start_time,
                end_time=end_time,
                status=AppointmentStatus.SCHEDULED,
            )
            return {"appointment_id": appointment.id, "code_sent": False}

        # fluxo público
        name = validated_data.get("name") or ""
        phone = validated_data["phone"]
        user, _ = User.objects.get_or_create(
            phone=phone,
            defaults={"name": name, "role": "client"},
        )

        appointment = Appointment.objects.create(
            client=user,
            service=service,
            barber_id=barber,
            date=date,
            start_time=start_time,
            end_time=end_time,
            status=AppointmentStatus.PENDING,
        )

        code = generate_code()
        r.setex(f"login_code:{phone}", 300, code)

        return {"appointment_id": appointment.id, "code_sent": True}


class AppointmentConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()

    def validate(self, attrs):
        phone = attrs.get('phone')
        code = attrs.get("code")

        if not phone:
            raise serializers.ValidationError({"phone": "Este campo é obrigatório."})
        phone = clean_phone(phone)

        if not code:
            raise serializers.ValidationError({"code": "O código de verificação é obrigatório."})

        redis_key = f"login_code:{phone}"
        saved_code = r.get(redis_key)
        user = User.objects.filter(phone=phone).first()

        if saved_code is None or saved_code.decode() != code:
            if user:
                Appointment.objects.filter(client=user, status=AppointmentStatus.PENDING).delete()
                raise serializers.ValidationError({"code": "Código inválido ou expirado."})

        if not user:
            raise serializers.ValidationError({"phone": "Usuário não encontrado."})

        appointment = Appointment.objects.filter(client=user, status=AppointmentStatus.PENDING).order_by("-created_at").first()

        if appointment:
            appointment.status = AppointmentStatus.SCHEDULED
            appointment.save()
            r.delete(redis_key)
        else:
            raise serializers.ValidationError({"appointment": "Nenhum agendamento pendente encontrado."})

        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "name": user.name,
                "phone": user.phone,
            },
            "appointment_id": appointment.id if appointment else None
        }


class AppointmentCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
