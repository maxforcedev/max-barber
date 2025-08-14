from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from core.utils import clean_phone
from . import serializers, models


class LoginView(APIView):
    def post(self, request):
        serializer = serializers.LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SendLoginCodeView(APIView):
    def post(self, request):
        serializer = serializers.SendLoginCodeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientCheckView(APIView):
    def get(self, request):
        raw_phone = request.query_params.get("phone", "")
        phone = clean_phone(raw_phone)
        user = models.User.objects.only("name").filter(phone=phone).first()

        return Response({
            "exists": bool(user),
            "name": user.name if user else None,
            "phone": phone
        })


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = serializers.MeSerializer(request.user).data
        return Response(data, status=200)
