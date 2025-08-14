from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from .models import Appointment
from .serializers import AppointmentCreateSerializer, AppointmentConfirmSerializer, AppointmentCancelSerializer, AppointmentSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import models
from core.choices import AppointmentStatus


class AppointmentCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AppointmentCreateSerializer(data=request.data, context={"request": request})
        print(request.data)
        if serializer.is_valid():
            data = serializer.save()
            return Response(data, status=status.HTTP_201_CREATED)
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AppointmentConfirmView(APIView):
    def post(self, request):
        serializer = AppointmentConfirmSerializer(data=request.data, context={"request": request})
        print(request.data)
        if serializer.is_valid():
            data = serializer.save()
            return Response(data, status=status.HTTP_200_OK)
        print(serializer.errors)
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

# ALTERAR FUTURAMENTE
class AppointmentsListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.all()

        if user.role == "client":
            qs = qs.filter(client=user).order_by(
                models.Case(
                    models.When(status=AppointmentStatus.PENDING, then=0),
                    models.When(status=AppointmentStatus.SCHEDULED, then=1),
                    default=2,
                    output_field=models.IntegerField(),
                ),
                '-date',
                '-start_time'
            )
            return qs

        elif user.role == "barber":
            qs = qs.filter(barber=user.barber)

        date = self.request.query_params.get("date")

        if date:
            qs = qs.filter(date=date)

        barber_id = self.request.query_params.get("barber_id")

        if barber_id:
            qs = qs.filter(barber_id=barber_id)

        status_param = self.request.query_params.get("status")

        if status_param:
            qs = qs.filter(status=status_param)

        return qs.order_by("-date", "-start_time")
