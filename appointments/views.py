from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import AppointmentCreateSerializer, AppointmentConfirmSerializer


class AppointmentCreateView(APIView):
    def post(self, request):
        serializer = AppointmentCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.save()
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AppointmentConfirmView(APIView):
    def post(self, request):
        serializer = AppointmentConfirmSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
