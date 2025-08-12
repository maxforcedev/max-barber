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


class ClientCheckView(APIView):

    def get(self, request):
        raw_phone = request.query_params.get("phone", "")
        phone = clean_phone(raw_phone)

        user = User.objects.filter(phone=phone).first()

        return Response({
            "exists": bool(user),
            "name": user.name if user else None,
            "phone": phone
        })
