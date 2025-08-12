from rest_framework.routers import DefaultRouter
from barbershops.views import BarberShopViewSet

router = DefaultRouter()
router.register(r'barbershops', BarberShopViewSet, basename='barbershop')
urlpatterns = router.urls
