import re
import secrets
import string
from rest_framework import serializers


def clean_phone(phone):
    phone = re.sub(r'\D', '', phone)
    if len(phone) != 11:
        raise serializers.ValidationError('O telefone informado esta incorreto.')
    return phone


def generate_code(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))
