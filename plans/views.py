from rest_framework import viewsets, permissions
from .models import Plan
from .serializers import PlanSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from accounts.models import User
from datetime import datetime
from plans.models import PlanSubscription, PlanSubscriptionCredit, PlanBenefit
from appointments.models import Appointment


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

        phone = raw_phone
        try:
            service_id = int(raw_service_id)
        except ValueError:
            return Response({"detail": "service_id inválido."}, status=400)

        try:
            appointment_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "date deve estar no formato YYYY-MM-DD."}, status=400)

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response({"has_plan": False, "reason": "no_plan"})

        subscription = PlanSubscription.objects.filter(
            user=user,
            status="active",
            start_date__lte=appointment_date,
            end_date__gte=appointment_date
        ).first()

        if not subscription:
            return Response({"has_plan": False, "reason": "no_plan"})

        benefit = PlanBenefit.objects.filter(
            plan=subscription.plan,
            service_id=service_id
        ).first()

        if not benefit:
            return Response({
                "has_plan": True,
                "plan_name": subscription.plan.name,
                "remaining": 0,
                "total": 0,
                "can_use": False,
                "reason": "no_benefit",
            })

        credit = PlanSubscriptionCredit.objects.filter(
            subscription=subscription,
            service_id=service_id
        ).first()

        if credit:
            used = int(credit.used)
            total = int(credit.total or benefit.quantity)
            remaining = int(max(total - used, 0))
        else:
            usable_status = ["pending", "scheduled", "completed"]
            used = Appointment.objects.filter(
                plan_subscription=subscription,
                service_id=service_id,
                paid_with_plan=True,
                status__in=usable_status
            ).count()
            total = int(benefit.quantity or 0)
            remaining = int(max(total - used, 0))

        allowed_days = benefit.allowed_days or []
        if allowed_days:
            day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
            pt_map = {"mon": "Segunda", "tue": "Terça", "wed": "Quarta", "thu": "Quinta", "fri": "Sexta", "sat": "Sábado", "sun": "Domingo"}
            weekday_code = day_map[appointment_date.weekday()]
            if weekday_code not in allowed_days:
                allowed_days_pt = ", ".join(pt_map[d] for d in allowed_days if d in pt_map)
                return Response({
                    "has_plan": True,
                    "plan_name": subscription.plan.name,
                    "remaining": remaining,
                    "total": total,
                    "can_use": False,
                    "reason": "not_allowed_day",
                    "allowed_days_pt": allowed_days_pt,
                    "weekday_pt": pt_map.get(weekday_code, ""),
                })

        if remaining <= 0:
            return Response({
                "has_plan": True,
                "plan_name": subscription.plan.name,
                "remaining": remaining,
                "total": total,
                "can_use": False,
                "reason": "no_credits",
            })

        return Response({
            "has_plan": True,
            "plan_name": subscription.plan.name,
            "remaining": remaining,
            "total": total,
            "can_use": True,
            "reason": "ok",
        })
