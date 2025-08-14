from django.utils import timezone
from rest_framework import serializers
from .models import Plan, PlanBenefit, PlanSubscription, PlanSubscriptionCredit
from accounts.serializers import UserSerializer


class PlanBenefitSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_price = serializers.DecimalField(source="service.price", read_only=True, max_digits=8, decimal_places=2)

    class Meta:
        model = PlanBenefit
        fields = ["id", "service", "service_name", "service_price", "quantity", "allowed_days"]


class PlanSerializer(serializers.ModelSerializer):
    benefits = PlanBenefitSerializer(many=True)
    price_original = serializers.SerializerMethodField()
    economia = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id", "name", "slug", "price", "price_original", "economia",
            "duration_days", "is_popular", "color", "card_color", "benefits"
        ]

    def get_price_original(self, obj):
        return obj.price_original

    def get_economia(self, obj):
        return obj.economia

    def create(self, validated_data):
        benefits_data = validated_data.pop("benefits", [])
        plan = Plan.objects.create(**validated_data)
        for b in benefits_data:
            PlanBenefit.objects.create(plan=plan, **b)
        return plan

    def update(self, instance, validated_data):
        benefits_data = validated_data.pop("benefits", [])
        instance = super().update(instance, validated_data)
        instance.benefits.all().delete()
        for b in benefits_data:
            PlanBenefit.objects.create(plan=instance, **b)
        return instance



class PlanSubscriptionCreditSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = PlanSubscriptionCredit
        fields = ["id", "service", "service_name", "used", "total", "remaining"]
        read_only_fields = ["remaining"]

    def get_remaining(self, obj):
        return obj.remaining()


class PlanSubscriptionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    credits = PlanSubscriptionCreditSerializer(many=True, read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    price = serializers.DecimalField(source="plan.price", read_only=True, max_digits=8, decimal_places=2)
    price_original = serializers.SerializerMethodField()
    economia = serializers.SerializerMethodField()

    class Meta:
        model = PlanSubscription
        fields = [
            "id", "user", "plan", "plan_name", "price", "price_original", "economia",
            "start_date", "end_date", "status", "credits"
        ]

    def get_price_original(self, obj):
        return obj.plan.price_original

    def get_economia(self, obj):
        return obj.plan.economia


class CreatePlanSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanSubscription
        fields = ["user", "plan"]

    def create(self, validated_data):
        user = validated_data["user"]
        plan = validated_data["plan"]

        sub = PlanSubscription.objects.create(
            user=user,
            plan=plan,
            start_date=validated_data.get("start_date") or timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=plan.duration_days),
            status="active"
        )

        for benefit in plan.benefits.all():
            PlanSubscriptionCredit.objects.create(
                subscription=sub,
                service=benefit.service,
                total=benefit.quantity
            )

        return sub
