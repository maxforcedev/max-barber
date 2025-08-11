import redis
from datetime import datetime, timedelta
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from core.utils import clean_phone, generate_code, get_available_slots
from core.choices import AppointmentStatus, UserRole
from barbers.models import WorkingHour, BlockedTime
from accounts.models import User
from services.models import Service
from .models import Appointment
from django.utils import timezone
from django.conf import settings
r = redis.Redis.from_url(settings.REDIS_URL)


class AppointmentSerializer(serializers.ModelSerializer):
    barber = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    canceled_by = serializers.SerializerMethodField()

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

    def get_canceled_by(self, obj):
        mapping = {
            "client": "Cliente",
            "barber": "Barbeiro",
            "admin": "Administrador"
        }
        return mapping.get(obj.canceled_by, obj.canceled_by or "—")


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

        if is_public:
            if not phone:
                raise serializers.ValidationError({"phone": "Este campo é obrigatório."})
            phone = clean_phone(phone)
            attrs["phone"] = phone
            appointment_exists = Appointment.objects.filter(client__phone=phone, status__in=[AppointmentStatus.PENDING, AppointmentStatus.SCHEDULED]).exists()
        else:
            appointment_exists = Appointment.objects.filter(client=request.user, status__in=[AppointmentStatus.PENDING, AppointmentStatus.SCHEDULED]).exists()

        if appointment_exists:
            raise serializers.ValidationError("Você possui um agendamento pendente.")

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
            # cria direto
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

        # fluxo público → só enviar código, não criar
        name = validated_data.get("name") or ""
        phone = validated_data["phone"]

        key = f"create_attempts:{phone}"
        attempts = r.get(key)
        if attempts and int(attempts) >= 3:
            raise serializers.ValidationError("Você atingiu o limite de tentativas. Tente novamente em 1 hora.")
        r.incr(key)
        r.expire(key, 3600)

        # garante que o usuário existe, mas sem criar agendamento ainda
        User.objects.get_or_create(
            phone=phone,
            defaults={"name": name, "role": UserRole.CLIENT},
        )
        r.setex(f"login_name:{phone}", 300, name)

        code = generate_code()
        r.setex(f"login_code:{phone}", 300, code)

        return {"code_sent": True}


class AppointmentConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()
    service_id = serializers.IntegerField()
    barber_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField()

    def validate(self, attrs):
        phone = clean_phone(attrs["phone"])
        attrs["phone"] = phone

        # validar código
        redis_key = f"login_code:{phone}"
        saved_code = r.get(redis_key)
        if saved_code is None or saved_code.decode() != attrs["code"]:
            raise serializers.ValidationError({"code": "Código inválido ou expirado."})

        # reaproveitar validações do AppointmentCreateSerializer
        service_id = attrs["service_id"]
        barber_id = attrs["barber_id"]
        date = attrs["date"]
        start_time = attrs["start_time"]

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError("Serviço inválido.")

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
        phone = validated_data["phone"]

        name = validated_data.get("name")
        if not name:
            name = r.get(f"login_name:{phone}")
            name = name.decode() if name else "Usuário"

        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={"name": name, "role": UserRole.CLIENT}
        )
        if not created and not user.name and name:
            user.name = name
            user.save()

        appointment = Appointment.objects.create(
            client=user,
            service=validated_data["service"],
            barber_id=validated_data["barber_id"],
            date=validated_data["date"],
            start_time=validated_data["start_time"],
            end_time=validated_data["end_time"],
            status=AppointmentStatus.SCHEDULED
        )

        # Limpa dados temporários
        r.delete(f"login_code:{phone}")
        r.delete(f"login_name:{phone}")

        # Gera tokens de acesso
        refresh = RefreshToken.for_user(user)

        return {
            "status": "ok",
            "appointment_id": appointment.id,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }

class AppointmentCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context.get("request")
        pk = self.context.get("pk")
        reason = attrs.get("reason", "")

        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError({"message": "Agendamento não encontrado."})

        if request.user.role == "client" and appointment.client != request.user:
            raise serializers.ValidationError({"message": "Você não tem permissão para cancelar este agendamento."})

        if appointment.status not in [AppointmentStatus.PENDING, AppointmentStatus.SCHEDULED]:
            raise serializers.ValidationError({"message": "Agendamento já está cancelado ou finalizado."})

        start_dt = datetime.combine(appointment.date, appointment.start_time)
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt)
        now = timezone.now()
        if start_dt - now < timedelta(hours=2):
            raise serializers.ValidationError({"message": "Cancelamento não permitido (menos de 2h de antecedência)."})

        attrs["appointment"] = appointment
        attrs["reason"] = reason
        return attrs

    def save(self):
        request = self.context.get("request")
        appointment = self.validated_data["appointment"]
        reason = self.validated_data["reason"]

        canceled_by = "client"
        if request.user.role in ["barber", "admin"]:
            canceled_by = request.user.role

        appointment.cancel(reason=reason, canceled_by=canceled_by)
        return {
            "appointment_id": appointment.id,
            "canceled_by": canceled_by,
            "reason": reason
        }
