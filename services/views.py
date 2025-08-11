from rest_framework import viewsets
from .models import Service
from .serializers import ServiceSerializer


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    pagination_class = None
