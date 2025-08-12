import redis
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings
from .models import User
from core.utils import generate_code, clean_phone
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
    role_desejado = serializers.ChoiceField(choices=["client", "barber", "admin"])

    def validate(self, attrs):
        phone = clean_phone(attrs.get('phone'))
        code = attrs.get('code')
        role_desejado = attrs.get('role_desejado')

        if not phone:
            raise serializers.ValidationError("O número de telefone é obrigatório.")
        if len(phone) != 11:
            raise serializers.ValidationError("O número de telefone está incorreto.")

        if not code:
            raise serializers.ValidationError("Informe o código de verificação.")
        if len(code) != 6 or not code.isdigit():
            raise serializers.ValidationError("O código deve conter 6 dígitos numéricos.")

        key = f"login_code:{phone}"
        saved_code = r.get(key)
        if saved_code is None or saved_code.decode() != code:
            raise serializers.ValidationError("Código informado é inválido ou está expirado.")

        user = User.objects.filter(phone=phone).first()
        if not user:
            raise serializers.ValidationError("Usuário não encontrado.")

        # Mesma regra de compatibilidade do SendLoginCode
        if role_desejado == "admin" and not user.is_admin:
            raise serializers.ValidationError("Você não tem permissão para acessar a área administrativa.")
        if role_desejado == "barber" and user.role not in [UserRole.BARBER] and not user.is_admin:
            raise serializers.ValidationError("Apenas barbeiros ou administradores podem acessar esta área.")
        if role_desejado == "client" and user.role not in [UserRole.CLIENT, UserRole.BARBER] and not user.is_admin:
            raise serializers.ValidationError("Não é possível acessar como cliente.")

        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data
        }


class SendLoginCodeSerializer(serializers.Serializer):
    phone = serializers.CharField()
    role_desejado = serializers.ChoiceField(choices=["client", "barber", "admin"])

    def validate(self, attrs):
        phone = clean_phone(attrs.get('phone'))
        role_desejado = attrs.get('role_desejado')

        if not phone:
            raise serializers.ValidationError("O número de telefone é obrigatório.")
        if len(phone) != 11:
            raise serializers.ValidationError("O número de telefone está incorreto.")

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError("O número de telefone não está vinculado a nenhuma conta.")

        if user.role == UserRole.CLIENT:
            role_real = "client"
        elif user.role == UserRole.BARBER:
            role_real = "barber"
        else:
            role_real = "admin" if user.is_admin else None

        if role_desejado == "admin" and not user.is_admin:
            raise serializers.ValidationError("Você não tem permissão para acessar a área administrativa.")
        if role_desejado == "barber" and role_real not in ["barber", "admin"]:
            raise serializers.ValidationError("Apenas barbeiros ou administradores podem acessar esta área.")
        if role_desejado == "client" and role_real not in ["client", "barber", "admin"]:
            raise serializers.ValidationError("Não é possível acessar como cliente.")

        code = generate_code()
        r.setex(f"login_code:{phone}", 300, code)

        return {"code": code, "role": role_real, "is_admin": user.is_admin}
