import redis
from datetime import datetime, timedelta
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from core.utils import clean_phone, generate_code
from core.choices import AppointmentStatus
from barbers.models import WorkingHour, BlockedTime
from accounts.models import User
from services.models import Service
from .models import Appointment

from django.conf import settings
r = redis.Redis.from_url(settings.REDIS_URL)


class AppointmentCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    phone = serializers.CharField()
    service_id = serializers.IntegerField()
    barber_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField()

    def validate(self, attrs):
        phone = attrs.get('phone')
        service_id = attrs.get('service_id')
        barber_id = attrs.get('barber_id')
        date = attrs.get('date')
        start_time = attrs.get('start_time')

        if not phone:
            raise serializers.ValidationError({"phone": "Este campo é obrigatório."})

        phone = clean_phone(phone)
        weekday = date.weekday()

        working_hours = WorkingHour.objects.filter(barber_id=barber_id, weekday=weekday).first()

        if not working_hours:
            raise serializers.ValidationError('Barbeiro(a) não irá funcionar nesse dia.')

        if not (working_hours.start_time <= start_time < working_hours.end_time):
            raise serializers.ValidationError('Horário fora do expediente do barbeiro.')

        is_blocked = BlockedTime.objects.filter(barber_id=barber_id, date=date,
                                                start_time__lte=start_time,
                                                end_time__gt=start_time
                                                ).exists()
        if is_blocked:
            raise serializers.ValidationError('Esse horario não esta mais disponivel.')

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError('Serviço inválido.')

        duration = service.duration
        start_dt = datetime.combine(date, start_time)
        end_dt = start_dt + timedelta(minutes=duration)
        end_time = end_dt.time()

        '''if end_time > working_hours.end_time:
            raise serializers.ValidationError('O serviço ultrapassa o horario de trabalho, tente marcar mais cedo.')'''

        conflict = Appointment.objects.filter(
            barber_id=barber_id,
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(status=AppointmentStatus.CANCELED).exists()

        if conflict:
            raise serializers.ValidationError('Esse horario não esta mais disponivel.')

        attrs['phone'] = phone
        attrs['service'] = service
        attrs['end_time'] = end_time
        return attrs

    def create(self, validated_data):
        name = validated_data.get('name')
        phone = validated_data.get('phone')
        service = validated_data.get('service')
        barber = validated_data.get('barber_id')
        date = validated_data.get('date')
        start_time = validated_data.get('start_time')
        end_time = validated_data.get('end_time')

        user, created = User.objects.get_or_create(
        phone=phone,
        defaults={'name': name, 'role': 'client'}
        )

        appointment = Appointment.objects.create(client=user, service=service, barber_id=barber, date=date, start_time=start_time, end_time=end_time, status=AppointmentStatus.PENDING)

        code = generate_code()
        r.setex(f'login_code:{phone}', 300, code)

        return {
            'appointment_id': appointment.id,
            'code_sent': True
        }


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
