from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from core.utils import generate_code, clean_phone, validate_code
from core.choices import UserRole
from .models import User


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

        validate_code(code, f"login_code:{phone}", phone)

        user = User.objects.filter(phone=phone).first()
        if not user:
            raise serializers.ValidationError("Usuário não encontrado.")

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
        role_in = attrs.get('role_desejado')

        user = User.objects.filter(phone=phone).first()
        if not user:
            raise serializers.ValidationError("O número de telefone não está vinculado a nenhuma conta.")

        user_role = (
            'client' if user.role == UserRole.CLIENT else
            'barber' if user.role == UserRole.BARBER else
            'admin' if user.is_admin else None

        )

        if role_in == "admin" and not user.is_admin:
            raise serializers.ValidationError("Você não tem permissão para acessar a área administrativa.")
        if role_in == "barber" and user_role not in ["barber", "admin"]:
            raise serializers.ValidationError("Apenas barbeiros ou administradores podem acessar esta área.")
        if role_in == "client" and user_role not in ["client", "barber", "admin"]:
            raise serializers.ValidationError("Não é possível acessar como cliente.")

        generate_code(phone, f"login_code:{phone}",)

        return {"role": user_role, "is_admin": user.is_admin}


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name", "phone", "email")
