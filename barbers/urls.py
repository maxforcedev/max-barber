from rest_framework.routers import DefaultRouter
from .views import BarberViewSet

router = DefaultRouter()
router.register(r'barbers', BarberViewSet, basename='barber')

urlpatterns = router.urls
