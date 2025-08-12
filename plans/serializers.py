from rest_framework import serializers
from .models import Plan, PlanBenefit
from services.models import Service


class PlanBenefitSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = PlanBenefit
        fields = ["id", "service", "service_name", "quantity", "allowed_days"]


class PlanSerializer(serializers.ModelSerializer):
    economia = serializers.SerializerMethodField()
    benefits = PlanBenefitSerializer(many=True)

    class Meta:
        model = Plan
        fields = ["id", "name", "slug", "price", "price_original", "economia",
                  "duration_days", "is_popular", "color", "card_color", "benefits"]

    def get_economia(self, obj):
        return obj.economia

    def create(self, validated_data):
        benefits_data = validated_data.pop("benefits", [])
        plan = Plan.objects.create(**validated_data)
        for benefit in benefits_data:
            PlanBenefit.objects.create(plan=plan, **benefit)
        return plan

    def update(self, instance, validated_data):
        benefits_data = validated_data.pop("benefits", [])
        instance = super().update(instance, validated_data)
        instance.benefits.all().delete()
        for benefit in benefits_data:
            PlanBenefit.objects.create(plan=instance, **benefit)
        return instance
