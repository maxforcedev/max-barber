from rest_framework.routers import DefaultRouter
from .views import PlanViewSet, PlanSubscriptionViewSet

router = DefaultRouter()
router.register(r'plans', PlanViewSet, basename='plan')
router.register(r'subscriptions', PlanSubscriptionViewSet, basename='subscription')

urlpatterns = router.urls
