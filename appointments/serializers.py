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
from plans.models import PlanSubscription, PlanSubscriptionCredit
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
    use_plan = serializers.BooleanField(required=False, default=False)

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
            appointment_exists = Appointment.objects.filter(
                client__phone=phone,
                status__in=[AppointmentStatus.PENDING, AppointmentStatus.SCHEDULED]
            ).exists()
        else:
            appointment_exists = Appointment.objects.filter(
                client=request.user,
                status__in=[AppointmentStatus.PENDING, AppointmentStatus.SCHEDULED]
            ).exists()

        if appointment_exists:
            raise serializers.ValidationError("Você possui um agendamento aberto ou pendente.")

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

        user_lookup = None
        if is_public:
            user_lookup = User.objects.filter(phone=attrs["phone"]).first()
        else:
            user_lookup = request.user

        if attrs.get("use_plan"):
            if is_public:
                client = User.objects.filter(phone=attrs["phone"]).first()
            else:
                client = request.user

            if not client:
                raise serializers.ValidationError("Cliente não encontrado para uso do plano.")

            subscription = PlanSubscription.objects.filter(
                user=client,
                status="active",
            ).first()

            if not subscription:
                raise serializers.ValidationError("Nenhum plano ativo encontrado para este cliente.")

            credits = PlanSubscriptionCredit.objects.filter(
                subscription=subscription,
                service_id=service_id,
                used=False
            )

            if not credits.exists():
                raise serializers.ValidationError("Você não possui créditos disponíveis para este serviço.")

            attrs["plan_credit"] = credits.first()

        attrs["can_use_plan"] = False
        attrs["remaining_credits"] = 0
        attrs["plan_name"] = None

        if user_lookup:
            active_plan = PlanSubscription.objects.filter(
                user=user_lookup,
                status="active",
                end_date__gte=timezone.now().date()
            ).first()

            if active_plan:
                credit = PlanSubscriptionCredit.objects.filter(
                    subscription=active_plan,
                    service_id=service_id
                ).first()
                if credit and credit.remaining() > 0:
                    attrs["can_use_plan"] = True
                    attrs["remaining_credits"] = credit.remaining()
                    attrs["plan_name"] = active_plan.plan.name

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
                paid_with_plan=validated_data.get("use_plan", False),
                plan_subscription=validated_data.get("plan_credit").subscription if validated_data.get("plan_credit") else None

            )

            if validated_data.get("plan_credit"):
                credit = validated_data["plan_credit"]
                credit.used += 1
                credit.save()

            return {
                "appointment_id": appointment.id,
                "code_sent": False,
                "can_use_plan": validated_data.get("can_use_plan", False),
                "remaining_credits": validated_data.get("remaining_credits", 0),
                "plan_name": validated_data.get("plan_name")
            }

        name = validated_data.get("name") or ""
        phone = validated_data["phone"]

        # key = f"create_attempts:{phone}"
        # attempts = r.get(key)
        # if attempts and int(attempts) >= 3:
        #     raise serializers.ValidationError("Você atingiu o limite de tentativas. Tente novamente em 1 hora.")
        # r.incr(key)
        # r.expire(key, 3600)

        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={"name": name, "role": UserRole.CLIENT},
        )
        if not created and name:
            user.name = name
            user.save()
        r.setex(f"login_name:{phone}", 300, name or user.name)

        code = generate_code()
        r.setex(f"login_code:{phone}", 300, code)

        return {
            "code_sent": True,
            "can_use_plan": validated_data.get("can_use_plan", False),
            "remaining_credits": validated_data.get("remaining_credits", 0),
            "plan_name": validated_data.get("plan_name")
        }


class AppointmentConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()
    service_id = serializers.IntegerField()
    barber_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    use_plan = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        phone = clean_phone(attrs["phone"])
        attrs["phone"] = phone

        redis_key = f"login_code:{phone}"
        saved_code = r.get(redis_key)
        if saved_code is None or saved_code.decode() != attrs["code"]:
            raise serializers.ValidationError({"code": "Código inválido ou expirado."})

        try:
            service = Service.objects.get(id=attrs["service_id"])
        except Service.DoesNotExist:
            raise serializers.ValidationError("Serviço inválido.")
        attrs["service"] = service

        weekday = attrs["date"].weekday()
        working_hours = WorkingHour.objects.filter(barber_id=attrs["barber_id"], weekday=weekday).first()
        if not working_hours:
            raise serializers.ValidationError("Barbeiro(a) não irá funcionar nesse dia.")

        if not (working_hours.start_time <= attrs["start_time"] < working_hours.end_time):
            raise serializers.ValidationError("Horário fora do expediente do barbeiro.")

        if BlockedTime.objects.filter(
            barber_id=attrs["barber_id"],
            date=attrs["date"],
            start_time__lte=attrs["start_time"],
            end_time__gt=attrs["start_time"],
        ).exists():
            raise serializers.ValidationError("Esse horário não está mais disponível.")

        if attrs["start_time"].strftime("%H:%M") not in get_available_slots(attrs["barber_id"], attrs["date"], service):
            raise serializers.ValidationError("Horário inválido ou indisponível.")

        start_dt = datetime.combine(attrs["date"], attrs["start_time"])
        end_dt = start_dt + timedelta(minutes=service.duration)
        attrs["end_time"] = end_dt.time()

        if Appointment.objects.filter(
            barber_id=attrs["barber_id"],
            date=attrs["date"],
            start_time__lt=end_dt.time(),
            end_time__gt=attrs["start_time"],
        ).exclude(status=AppointmentStatus.CANCELED).exists():
            raise serializers.ValidationError("Esse horário não está mais disponível.")

        attrs["plan_subscription"] = None
        attrs["credit_entry"] = None
        if attrs.get("use_plan"):
            user_lookup = User.objects.filter(phone=phone).first()
            if not user_lookup:
                raise serializers.ValidationError("Usuário não encontrado para uso do plano.")

            subscription = PlanSubscription.objects.filter(
                user=user_lookup,
                status="active",
                end_date__gte=timezone.now().date()
            ).first()
            if not subscription:
                raise serializers.ValidationError("Nenhum plano ativo encontrado.")

            credit_entry = PlanSubscriptionCredit.objects.filter(
                subscription=subscription,
                service_id=service.id
            ).first()

            if not credit_entry or credit_entry.remaining() <= 0:
                raise serializers.ValidationError("Você não possui créditos disponíveis para este serviço.")

            attrs["plan_subscription"] = subscription
            attrs["credit_entry"] = credit_entry
            if not attrs.get("plan_subscription") or not attrs.get("credit_entry"):
                attrs["use_plan"] = False

        return attrs

    def create(self, validated_data):
        phone = validated_data["phone"]

        name = r.get(f"login_name:{phone}")
        name = name.decode() if name else "Usuário"

        user, _ = User.objects.get_or_create(
            phone=phone,
            defaults={"name": name, "role": UserRole.CLIENT},
        )

        appointment = Appointment.objects.create(
            client=user,
            service=validated_data["service"],
            barber_id=validated_data["barber_id"],
            date=validated_data["date"],
            start_time=validated_data["start_time"],
            end_time=validated_data["end_time"],
            status=AppointmentStatus.SCHEDULED,
            paid_with_plan=validated_data.get("use_plan", False),
            plan_subscription=validated_data.get("plan_subscription")
        )

        if validated_data.get("use_plan") and validated_data.get("credit_entry"):
            credit_entry = validated_data["credit_entry"]
            credit_entry.used += 1  # incrementa uso
            credit_entry.save()

        r.delete(f"login_code:{phone}")
        r.delete(f"login_name:{phone}")

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
