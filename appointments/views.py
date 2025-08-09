from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.choices import AppointmentStatus
from .models import Appointment
from .serializers import AppointmentCreateSerializer, AppointmentConfirmSerializer, AppointmentCancelSerializer


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


class AppointmentCancelView(APIView):
    def post(self, request, pk):
        serializer = AppointmentCancelSerializer
        if serializer.is_valid():
            return Response({'message': 'Parametros Invalidos'}, status=status.HTTP_400_BAD_REQUEST)
        reason = serializer.validated_data.get('reason', '')

        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            return Response({'message': 'Agendamento não encontrado'}, status=status.HTTP_404_NOT_FOUND)

        if appointment.status not in [AppointmentStatus.PENDING, AppointmentStatus.SCHEDULED]:
            return Response({"message": "Agendamento já está cancelado ou finalizado."}, status=status.HTTP_409_CONFLICT)

        tz = timezone.get_current_timezone()
        start_dt = datetime.combine(appointment.date, appointment.start_time)
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(hours=2)
        now = timezone.now()

        if start_dt - now < timedelta(hours=2):
            return Response({"message": "Cancelamento não permitido (menos de 2h de antecedência)."}, status=status.HTTP_400_BAD_REQUEST)

        appointment.status = AppointmentStatus.CANCELED