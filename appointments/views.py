from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from .models import Appointment
from .serializers import AppointmentCreateSerializer, AppointmentConfirmSerializer, AppointmentCancelSerializer, AppointmentSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication


class AppointmentCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        print(request.data)
        serializer = AppointmentCreateSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            print("Erros de validação:", serializer.errors)
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


class AppointmentCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        serializer = AppointmentCancelSerializer(
            data=request.data,
            context={"request": request, "pk": pk}
        )
        if serializer.is_valid():
            data = serializer.save()
            return Response({"status": "ok", "message": "Agendamento cancelado com sucesso.", "data": data}, status=status.HTTP_200_OK)
        return Response({"status": "error", "message": "Não foi possível cancelar o agendamento.", "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class MyAppointmentsView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return Appointment.objects.filter(client=self.request.user).order_by('-date', '-start_time')
