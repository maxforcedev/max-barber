from rest_framework import viewsets, permissions
from .models import Plan
from .serializers import PlanSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from accounts.models import User
from datetime import datetime
from plans.models import PlanSubscription, PlanSubscriptionCredit, PlanBenefit
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
        raw_date = request.query_params.get("date", "").strip()

        # 1) parâmetros obrigatórios
        if not raw_phone or not raw_service_id or not raw_date:
            return Response({"detail": "Parâmetros obrigatórios: phone, service_id, date (YYYY-MM-DD)."}, status=400)

        # 2) validações básicas
        phone = raw_phone
        try:
            service_id = int(raw_service_id)
        except ValueError:
            return Response({"detail": "service_id inválido."}, status=400)

        try:
            appointment_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "date deve estar no formato YYYY-MM-DD."}, status=400)

        # 3) usuário
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response({"has_plan": False})

        # 4) assinatura válida NA DATA DO AGENDAMENTO
        subscription = PlanSubscription.objects.filter(
            user=user,
            status="active",
            start_date__lte=appointment_date,
            end_date__gte=appointment_date
        ).first()

        if not subscription:
            return Response({"has_plan": False})

        # 5) benefício configurado para o serviço
        benefit = PlanBenefit.objects.filter(
            plan=subscription.plan,
            service_id=service_id
        ).first()

        if not benefit:
            return Response({"has_plan": False})

        # 6) crédito (semeado pela assinatura)
        credit = PlanSubscriptionCredit.objects.filter(
            subscription=subscription,
            service_id=service_id
        ).first()

        # 7) cálculo de usados
        if credit:
            used = credit.used
            total = credit.total or benefit.quantity
            remaining = credit.remaining()
        else:
            # fallback: conta agendamentos com plano
            used = subscription.appointments.filter(
                service_id=service_id,
                paid_with_plan=True,
                status__in=["pending", "scheduled", "completed"]
            ).count()
            total = benefit.quantity
            remaining = max(total - used, 0)

        return Response({
            "has_plan": True,
            "plan_name": subscription.plan.name,
            "remaining": remaining,
            "total": total,
            "can_use": remaining > 0
        })
