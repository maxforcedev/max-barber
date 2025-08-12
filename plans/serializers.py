from rest_framework import serializers
from .models import Plan, PlanBenefit


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
