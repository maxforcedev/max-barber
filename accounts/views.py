from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import LoginSerializer, SendLoginCodeSerializer
from .models import User
from core.utils import clean_phone


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SendLoginCodeView(APIView):
    def post(self, request):
        serializer = SendLoginCodeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckClientView(APIView):
    def get(self, request):
        phone = request.GET.get("phone")
        phone = clean_phone(phone)

        if not phone:
            return Response({"exists": False}, status=400)

        client = User.objects.filter(phone=phone, role="client").first()
        if client:
            return Response({"exists": True, "nome": client.name})
        return Response({"exists": False})
