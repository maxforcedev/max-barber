import re
from rest_framework import serializers
from django.contrib.auth import authenticate



class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        phone = attrs.get('phone')
        code = attrs.get('code')
        password = attrs.get('password')

        if not phone:
            raise serializers.ValidationError('O Numero de telefone é obrigatorio.')

        phone = re.sub(r'\D', '', phone)
        if len(phone) != 11:
            raise serializers.ValidationError("O número de telefone está incorreto.")

        if password:
            user = authenticate(request=self.context.get('request'), phone=phone, password=password)

            if not user:
                raise serializers.ValidationError("As credencias fornecidas são invalidas.")

        elif code:
            if len(code) != 6 or not code.isdigit():
                raise serializers.ValidationError("O código deve conter 6 dígitos numéricos.")

            try:
                pass