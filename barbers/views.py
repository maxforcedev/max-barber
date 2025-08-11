from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets, status
from .models import Barber
from .serializers import BarberSerializer, BarberAvailabilitySerializer


class BarberViewSet(viewsets.ModelViewSet):
    queryset = Barber.objects.all()
    serializer_class = BarberSerializer
    pagination_class = None

    @action(detail=True, methods=["get"], url_path="availability")
    def availability(self, request, pk=None):
        serializer = BarberAvailabilitySerializer(
            data=request.query_params,
            context={"barber_id": pk}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
