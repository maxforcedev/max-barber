import re
import redis
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings
from django.contrib.auth import authenticate
from .models import User
from core.utils import generate_code
from core.choices import UserRole
r = redis.Redis.from_url(settings.REDIS_URL)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'phone']


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField(write_only=True, required=False)
    name = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        phone = attrs.get('phone')
        code = attrs.get('code')

        if not phone:
            raise serializers.ValidationError('O número de telefone é obrigatório.')

        phone = re.sub(r'\D', '', phone)
        if len(phone) != 11:
            raise serializers.ValidationError("O número de telefone está incorreto.")

        if code:
            if len(code) != 6 or not code.isdigit():
                raise serializers.ValidationError("O código deve conter 6 dígitos numéricos.")

            try:
                key = f"login_code:{phone}"
                saved_code = r.get(key)

                if saved_code is None or saved_code.decode() != code:
                    raise serializers.ValidationError('Código informado é inválido ou está expirado.')

                user = User.objects.filter(phone=phone).first()
                if not user:
                    name = attrs.get('name')
                    if not name:
                        raise serializers.ValidationError('Para criar um novo usuario é preciso nome e telefone.')
                    user = User.objects.create(phone=phone, name=name, role=UserRole.CLIENT)

            except redis.RedisError:
                raise serializers.ValidationError('Erro ao acessar o servidor de verificação.')
        else:
            raise serializers.ValidationError('Informe o codigo de verificação.')

        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data
        }


class SendLoginCodeSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate(self, attrs):
        phone = attrs.get('phone')

        if not phone:
            raise serializers.ValidationError('O número de telefone é obrigatório.')

        phone = re.sub(r'\D', '', phone)
        if len(phone) != 11:
            raise serializers.ValidationError("O número de telefone está incorreto.")

        code = generate_code()
        r.setex(f"login_code:{phone}", 300, code)

        return {"code": code}
