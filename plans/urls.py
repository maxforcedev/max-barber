from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PlanViewSet, CheckActivePlanView

router = DefaultRouter()
router.register(r'plans', PlanViewSet, basename='plan')
urlpatterns = [
    path("clients/check-plan", CheckActivePlanView.as_view(), name="check_active_plan"),
]

urlpatterns += router.urls
