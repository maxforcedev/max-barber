from datetime import datetime, timedelta
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from core.utils import clean_phone, generate_code, get_available_slots, validate_code, delete_key_redis
from core.choices import AppointmentStatus, UserRole
from barbers.models import WorkingHour, BlockedTime
from accounts.models import User
from services.models import Service
from .models import Appointment
from django.utils import timezone
from plans.models import PlanSubscription, PlanSubscriptionCredit, PlanBenefit


class AppointmentSerializer(serializers.ModelSerializer):
    barber = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    canceled_by = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ['id', 'status', 'date', 'start_time', 'end_time', 'barber', 'service', 'cancel_reason', 'canceled_at', 'canceled_by']

    def get_barber(self, obj):
        return {
            'id': obj.barber.id,
            'name': obj.barber.user.name,
            'phone': obj.barber.user.phone,
            'photo': obj.barber.photo.url if obj.barber.photo else None
        }

    def get_service(self, obj):
        return {
            'id': obj.service.id,
            'name': obj.service.name,
            'price': float(obj.service.price),
            'duration_min': obj.service.duration
        }

    def get_canceled_by(self, obj):
        mapping = {
            'client': 'Cliente',
            'barber': 'Barbeiro',
            'admin': 'Administrador'
        }
        return mapping.get(obj.canceled_by, obj.canceled_by or '—')


class AppointmentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    service_id = serializers.IntegerField()
    barber_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    use_plan = serializers.BooleanField(required=False, default=False)

    def _validate_phone(self, attrs, is_public):
        if is_public:
            attrs['phone'] = clean_phone(attrs.get('phone'))
        return attrs

    def _check_existing_appointment(self, attrs, request, phone, is_public):
        status = [AppointmentStatus.PENDING, AppointmentStatus.SCHEDULED]
        if is_public:
            phone = attrs.get('phone')
            exists = Appointment.objects.filter(client__phone=phone, status__in=status).exists()
        else:
            exists = Appointment.objects.filter(client=request.user, status__in=status).exists()
        if exists:
            raise serializers.ValidationError('Você já tem agendamento aberto ou pendente.')
        return attrs

    def _validate_availability(self, attrs):
        date = attrs.get('date')
        barber_id = attrs.get('barber_id')
        start_time = attrs.get('start_time')
        weekday = date.weekday()
        working_hours = WorkingHour.objects.only('start_time', 'end_time').filter(barber_id=barber_id, weekday=weekday).first()

        if not working_hours:
            raise serializers.ValidationError('Barbeiro(a) não irá funcionar nesse dia.')
        if not (working_hours.start_time <= start_time < working_hours.end_time):
            raise serializers.ValidationError('Horário fora do expediente do barbeiro.')

        is_blocked = BlockedTime.objects.filter(barber_id=barber_id, date=date, start_time__lte=start_time, end_time__gt=start_time).exists()
        if is_blocked:
            raise serializers.ValidationError('Esse horário não está mais disponível.')
        return attrs

    def _validate_service(self, attrs):
        try:
            service_id = attrs.get('service_id')
            attrs['service'] = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError('Serviço inválido ou indisponível.')
        return attrs

    def _validate_slot(self, attrs):
        barber_id = attrs.get('barber_id')
        date = attrs.get('date')
        start_time = attrs.get('start_time')
        service = attrs.get('service')

        slots = get_available_slots(barber_id, date, service)
        if start_time.strftime('%H:%M') not in slots:
            raise serializers.ValidationError('Horário inválido ou indisponível.')

        start_dt = datetime.combine(date, start_time)
        end_dt = start_dt + timedelta(minutes=service.duration)
        end_time = end_dt.time()

        conflict = Appointment.objects.filter(
            barber_id=barber_id, date=date, start_time__lt=end_time, end_time__gt=start_time
        ).exclude(status=AppointmentStatus.CANCELED).exists()

        if conflict:
            raise serializers.ValidationError('Esse horário não está mais disponível.')
        attrs['end_time'] = end_time
        return attrs

    def _validate_allowed_days(self, attrs, subscription):

        if not attrs.get("use_plan"):
            return attrs

        service = attrs.get("service")
        appointment_date = attrs.get("date")

        if not service or not appointment_date:
            return attrs

        benefit = PlanBenefit.objects.filter(plan=subscription.plan, service=service).first()
        if not benefit:
            raise serializers.ValidationError("Este serviço não faz parte do seu plano.")

        allowed_days = benefit.allowed_days or []
        if not allowed_days:
            return attrs

        day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        pt_map = {"mon": "Segunda", "tue": "Terça", "wed": "Quarta", "thu": "Quinta", "fri": "Sexta", "sat": "Sábado", "sun": "Domingo"}

        weekday_code = day_map[appointment_date.weekday()]

        if weekday_code not in allowed_days:
            dias_permitidos = [pt_map[d] for d in allowed_days]
            dias_fmt = ", ".join(dias_permitidos)
            raise serializers.ValidationError(
                f"Este benefício só pode ser usado em: {dias_fmt}."
            )

        return attrs

    def _validate_plan(self, attrs, request, is_public):
        if attrs.get('use_plan'):
            client = User.objects.filter(phone=attrs.get("phone")).first() if is_public else request.user
            if not client:
                raise serializers.ValidationError('Cliente não encontrado para o uso do plano.')

            subscription = PlanSubscription.objects.filter(user=client, status='active', start_date__lte=attrs['date'], end_date__gte=attrs['date']).first()
            if not subscription:
                raise serializers.ValidationError('O cliente não possui plano ativo para esta data.')

            attrs = self._validate_allowed_days(attrs, subscription)
            service_id = attrs["service"].id
            credits = PlanSubscriptionCredit.objects.filter(subscription=subscription, service_id=service_id).first()

            if not credits or credits.remaining() <= 0:
                raise serializers.ValidationError("Você não possui créditos disponíveis para este serviço.")
            attrs["plan_credit"] = credits
            attrs["plan_subscription"] = subscription
        return attrs

    def _set_plan_info(self, attrs, user_lookup):
        attrs["can_use_plan"] = False
        attrs["remaining_credits"] = 0
        attrs["plan_name"] = None

        if not user_lookup:
            return attrs

        appointment_date = attrs.get("date") or timezone.localdate()
        service = attrs.get("service")
        if not service:
            return attrs

        active_plan = PlanSubscription.objects.filter(
            user=user_lookup,
            status="active",
            start_date__lte=appointment_date,
            end_date__gte=appointment_date,
        ).first()
        if not active_plan:
            return attrs

        attrs["plan_name"] = active_plan.plan.name

        benefit = PlanBenefit.objects.filter(
            plan=active_plan.plan, service=service
        ).first()
        if not benefit:
            return attrs

        allowed_days = benefit.allowed_days or []
        if allowed_days:
            day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
            weekday_code = day_map[appointment_date.weekday()]
            if weekday_code not in allowed_days:
                return attrs

        credit = PlanSubscriptionCredit.objects.filter(
            subscription=active_plan, service=service
        ).first()

        if credit and credit.remaining() > 0:
            attrs["can_use_plan"] = True
            attrs["remaining_credits"] = credit.remaining()

        return attrs

    def validate(self, attrs):
        request = self.context.get("request")
        is_public = not request.user.is_authenticated

        attrs = self._validate_phone(attrs, is_public)
        attrs = self._check_existing_appointment(attrs, request, attrs.get("phone"), is_public)

        attrs = self._validate_service(attrs)
        attrs = self._validate_availability(attrs)
        attrs = self._validate_slot(attrs)
        attrs = self._validate_plan(attrs, request, is_public)

        user_lookup = User.objects.filter(phone=attrs["phone"]).first() if is_public else request.user
        attrs = self._set_plan_info(attrs, user_lookup)

        return attrs

    def _create_authenticaded_appointment(self, validated_data, request):
        user = request.user
        service = validated_data["service"]
        barber = validated_data["barber_id"]
        date = validated_data["date"]
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]
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

    def _create_public_appointment(self, validated_data):
        name = validated_data.get("name")
        phone = validated_data["phone"]

        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={"name": name, "role": UserRole.CLIENT},
        )

        generate_code(phone, f"login_code:{phone}")

        return {
            "code_sent": True,
            "can_use_plan": validated_data.get("can_use_plan", False),
            "remaining_credits": validated_data.get("remaining_credits", 0),
            "plan_name": validated_data.get("plan_name")
        }

    def create(self, validated_data):
        request = self.context.get("request")
        if request.user.is_authenticated:
            return self._create_authenticaded_appointment(validated_data, request)
        else:
            return self._create_public_appointment(validated_data)


class AppointmentConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()
    service_id = serializers.IntegerField()
    barber_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    use_plan = serializers.BooleanField(required=False, default=False)

    def _validate_phone(self, attrs):
        attrs['phone'] = clean_phone(attrs.get('phone'))
        return attrs

    def _check_existing_appointment(self, attrs, request, phone, is_public):
        status = [AppointmentStatus.PENDING, AppointmentStatus.SCHEDULED]
        if is_public:
            phone = attrs.get('phone')
            exists = Appointment.objects.filter(client__phone=phone, status__in=status).exists()
        else:
            exists = Appointment.objects.filter(client=request.user, status__in=status).exists()
        if exists:
            raise serializers.ValidationError('Você já tem agendamento aberto ou pendente.')
        return attrs

    def _validate_code(self, attrs):
        code = attrs['code']
        phone = attrs['phone']
        validate_code(code, f'login_code:{phone}', phone)
        return attrs

    def _validate_service(self, attrs):
        try:
            attrs['service'] = Service.objects.get(id=attrs['service_id'])
        except Service.DoesNotExist:
            raise serializers.ValidationError('Serviço inválido ou não disponivel.')
        return attrs

    def _validate_availability(self, attrs):
        date = attrs.get('date')
        barber_id = attrs.get('barber_id')
        start_time = attrs.get('start_time')
        weekday = date.weekday()
        working_hours = WorkingHour.objects.only('start_time', 'end_time').filter(barber_id=barber_id, weekday=weekday).first()

        if not working_hours:
            raise serializers.ValidationError('Barbeiro(a) não irá funcionar nesse dia.')
        if not (working_hours.start_time <= start_time < working_hours.end_time):
            raise serializers.ValidationError('Horário fora do expediente do barbeiro.')

        is_blocked = BlockedTime.objects.filter(barber_id=barber_id, date=date, start_time__lte=start_time, end_time__gt=start_time).exists()
        if is_blocked:
            raise serializers.ValidationError('Esse horário não está mais disponível.')
        return attrs

    def _validate_slot(self, attrs):
        barber_id = attrs.get('barber_id')
        date = attrs.get('date')
        start_time = attrs.get('start_time')
        service = attrs.get('service')

        slots = get_available_slots(barber_id, date, service)
        if start_time.strftime('%H:%M') not in slots:
            raise serializers.ValidationError('Horário inválido ou indisponível.')

        start_dt = datetime.combine(date, start_time)
        end_dt = start_dt + timedelta(minutes=service.duration)
        end_time = end_dt.time()

        conflict = Appointment.objects.filter(
            barber_id=barber_id, date=date, start_time__lt=end_time, end_time__gt=start_time
        ).exclude(status=AppointmentStatus.CANCELED).exists()

        if conflict:
            raise serializers.ValidationError('Esse horário não está mais disponível.')
        attrs['end_time'] = end_time
        return attrs

    def _validate_allowed_days(self, attrs, subscription):

        if not attrs.get("use_plan"):
            return attrs

        service = attrs.get("service")
        appointment_date = attrs.get("date")

        if not service or not appointment_date:
            return attrs

        benefit = PlanBenefit.objects.filter(plan=subscription.plan, service=service).first()
        if not benefit:
            raise serializers.ValidationError("Este serviço não faz parte do seu plano.")

        allowed_days = benefit.allowed_days or []
        if not allowed_days:
            return attrs

        day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        pt_map = {"mon": "Segunda", "tue": "Terça", "wed": "Quarta", "thu": "Quinta", "fri": "Sexta", "sat": "Sábado", "sun": "Domingo"}

        weekday_code = day_map[appointment_date.weekday()]

        if weekday_code not in allowed_days:
            dias_permitidos = [pt_map[d] for d in allowed_days]
            dias_fmt = ", ".join(dias_permitidos)
            raise serializers.ValidationError(
                f"Este benefício só pode ser usado em: {dias_fmt}."
            )

        return attrs

    def _validate_plan(self, attrs, request, is_public):
        if attrs.get('use_plan'):
            client = User.objects.filter(phone=attrs.get("phone")).first() if is_public else request.user
            if not client:
                raise serializers.ValidationError('Cliente não encontrado para o uso do plano.')
            attrs['name'] = client.name or 'Usuario'

            subscription = PlanSubscription.objects.filter(user=client, status='active', start_date__lte=attrs['date'], end_date__gte=attrs['date']).first()

            if not subscription:
                raise serializers.ValidationError('O cliente não possui plano ativo.')

            attrs = self._validate_allowed_days(attrs, subscription)

            service_id = attrs["service"].id
            credits = PlanSubscriptionCredit.objects.filter(subscription=subscription, service_id=service_id).first()
            if not credits or credits.remaining() <= 0:
                raise serializers.ValidationError("Você não possui créditos disponíveis para este serviço.")

            attrs["plan_credit"] = credits
            attrs["plan_subscription"] = subscription
        return attrs

    def validate(self, attrs):
        request = self.context.get("request")
        is_public = not request.user.is_authenticated

        attrs = self._validate_phone(attrs)
        attrs = self._check_existing_appointment(attrs, request, attrs.get("phone"), is_public)
        attrs = self._validate_code(attrs)
        attrs = self._validate_service(attrs)

        attrs = self._validate_availability(attrs)
        attrs = self._validate_slot(attrs)
        attrs = self._validate_plan(attrs, request, is_public)

        return attrs

    def create(self, validated_data):
        phone = validated_data['phone']
        name = validated_data.get('name') or 'Usuario'

        user, _ = User.objects.get_or_create(phone=phone, defaults={'name': name, 'role': UserRole.CLIENT})

        appointment = Appointment.objects.create(
            client=user,
            service=validated_data['service'],
            barber_id=validated_data['barber_id'],
            date=validated_data['date'],
            start_time=validated_data['start_time'],
            end_time=validated_data['end_time'],
            status=AppointmentStatus.SCHEDULED,
            paid_with_plan=validated_data.get('use_plan', False),
            plan_subscription=validated_data.get('plan_subscription')
        )

        if validated_data.get('use_plan') and validated_data.get('plan_credit'):
            credit_entry = validated_data['plan_credit']
            credit_entry.used += 1
            credit_entry.save()

        delete_key_redis(phone)
        refresh = RefreshToken.for_user(user)
        return {
            'status': 'ok',
            'appointment_id': appointment.id,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }


class AppointmentCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context.get('request')
        pk = self.context.get('pk')
        reason = attrs.get('reason', '')

        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError({'message': 'Agendamento não encontrado.'})

        if request.user.role == 'client' and appointment.client != request.user:
            raise serializers.ValidationError({'message': 'Você não tem permissão para cancelar este agendamento.'})

        if appointment.status not in [AppointmentStatus.PENDING, AppointmentStatus.SCHEDULED]:
            raise serializers.ValidationError({'message': 'Agendamento já está cancelado ou finalizado.'})

        start_dt = datetime.combine(appointment.date, appointment.start_time)
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt)
        now = timezone.now()
        if start_dt - now < timedelta(hours=2):
            raise serializers.ValidationError({'message': 'Cancelamento não permitido (menos de 2h de antecedência).'})

        attrs['appointment'] = appointment
        attrs['reason'] = reason
        return attrs

    def save(self):
        request = self.context.get('request')
        appointment = self.validated_data['appointment']
        reason = self.validated_data['reason']

        canceled_by = 'client'
        if request.user.role in ['barber', 'admin']:
            canceled_by = request.user.role

        appointment.cancel(reason=reason, canceled_by=canceled_by)
        return {
            'appointment_id': appointment.id,
            'canceled_by': canceled_by,
            'reason': reason
        }
