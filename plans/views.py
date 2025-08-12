from rest_framework import viewsets, permissions
from .models import Plan
from .serializers import PlanSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from accounts.models import User
from plans.models import PlanSubscription, PlanBenefit
from core.utils import clean_phone


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.prefetch_related("benefits__service").all()
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        is_popular = self.request.query_params.get("popular")
        if is_popular:
            queryset = queryset.filter(is_popular=True)
        return queryset


class CheckActivePlanView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        raw_phone = request.query_params.get("phone", "").strip()
        raw_service_id = request.query_params.get("service_id", "").strip()

        if not raw_phone or not raw_service_id:
            return Response({"detail": "Parâmetros obrigatórios ausentes."}, status=400)

        phone = clean_phone(raw_phone)
        try:
            service_id = int(raw_service_id)
        except ValueError:
            return Response({"detail": "service_id inválido."}, status=400)

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response({"has_plan": False})

        today = timezone.now().date()
        subscription = PlanSubscription.objects.filter(
            user=user,
            status="active",
            start_date__lte=today,
            end_date__gte=today
        ).first()

        if not subscription:
            return Response({"has_plan": False})

        benefit = PlanBenefit.objects.filter(
            plan=subscription.plan,
            service_id=service_id
        ).first()

        if not benefit:
            return Response({"has_plan": False})

        used_count = subscription.appointments.filter(
            service_id=service_id,
            paid_with_plan=True,
            status__in=["pending", "scheduled", "completed"]
        ).count()

        remaining = benefit.quantity - used_count

        return Response({
            "has_plan": True,
            "plan_name": subscription.plan.name,
            "remaining": remaining,
            "total": benefit.quantity,
            "can_use": remaining > 0
        })
