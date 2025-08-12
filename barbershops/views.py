from rest_framework import viewsets
from .models import BarberShop
from .serializers import BarberShopSerializer


class BarberShopViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BarberShop.objects.all()
    serializer_class = BarberShopSerializer
    pagination_class = None
