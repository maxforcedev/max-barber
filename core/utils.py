import re
import secrets
import string
import redis
from django.conf import settings
from rest_framework import serializers
from datetime import datetime, timedelta
from django.utils import timezone
from barbers.models import WorkingHour, BlockedTime
from appointments.models import Appointment, AppointmentStatus

redis_client = redis.Redis.from_url(settings.REDIS_URL)


def clean_phone(phone):
    if not phone:
        raise serializers.ValidationError('O telefone é obrigatório.')

    phone = str(phone).strip()
    phone = re.sub(r'\D', '', phone)

    if len(phone) != 11 or phone[2] != '9':
        raise serializers.ValidationError('O telefone informado está incorreto.')

    return phone


def generate_code(phone, key, r=None, length=6):
    phone = clean_phone(phone)
    code = ''.join(secrets.choice(string.digits) for _ in range(length))

    r = r or redis_client
    r.setex(key, 300, code)
    return code


def validate_code(code, key, phone, r=None):
    phone = clean_phone(phone)

    if not code:
        raise serializers.ValidationError("O código é obrigatório.")
    if len(code) != 6 or not code.isdigit():
        raise serializers.ValidationError("O código deve conter 6 dígitos numéricos.")
    if not key:
        raise serializers.ValidationError("Ocorreu um erro ao verificar o código.")

    r = r or redis_client

    attempts_key = f"login_attempts:{phone}"
    attempts = r.get(attempts_key)
    if attempts and int(attempts) >= 3:
        raise serializers.ValidationError("Muitas tentativas inválidas. Tente novamente em alguns minutos.")

    r_code = r.get(key)
    if r_code is None or r_code.decode() != code:
        r.incr(attempts_key)
        r.expire(attempts_key, 300)
        raise serializers.ValidationError("O código informado está incorreto ou expirado.")

    r.delete(attempts_key)
    return True


def get_available_slots(barber_id, date, service):

    weekday = date.weekday()
    working_hours = WorkingHour.objects.filter(barber_id=barber_id, weekday=weekday).first()
    if not working_hours:
        return []

    duration_min = int(service.duration)
    start_exp = working_hours.start_time
    end_exp = working_hours.end_time

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
            if timezone.make_aware(datetime.combine(date, slot_start)) < now + timedelta(minutes=30):
                invalid = True

        if not invalid:
            slots.append(slot_start.strftime("%H:%M"))

        t0 += step

    return slots
