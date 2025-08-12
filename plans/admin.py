from django.contrib import admin
from .models import Plan, PlanBenefit, PlanSubscription, PlanSubscriptionCredit


class PlanBenefitInline(admin.TabularInline):
    model = PlanBenefit
    extra = 1
    fields = ("service", "quantity", "allowed_days")
    autocomplete_fields = ["service"]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "price_original_display", "economia_display", "duration_days", "is_popular")
    search_fields = ("name", "slug")
    list_filter = ("is_popular",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [PlanBenefitInline]

    def price_original_display(self, obj):
        return f"R$ {obj.price_original:.2f}"
    price_original_display.short_description = "Preço Original"

    def economia_display(self, obj):
        return f"R$ {obj.economia:.2f}"
    economia_display.short_description = "Economia"


@admin.register(PlanBenefit)
class PlanBenefitAdmin(admin.ModelAdmin):
    list_display = ("plan", "service", "quantity", "get_allowed_days")
    search_fields = ("plan__name", "service__name")
    list_filter = ("allowed_days",)
    autocomplete_fields = ["plan", "service"]

    def get_allowed_days(self, obj):
        dias = {
            "mon": "Seg",
            "tue": "Ter",
            "wed": "Qua",
            "thu": "Qui",
            "fri": "Sex",
            "sat": "Sáb",
            "sun": "Dom",
        }
        return ", ".join(dias.get(d, d) for d in obj.allowed_days)
    get_allowed_days.short_description = "Dias Permitidos"


class PlanSubscriptionCreditInline(admin.TabularInline):
    model = PlanSubscriptionCredit
    extra = 0
    readonly_fields = ("used",)
    autocomplete_fields = ["service"]


@admin.register(PlanSubscription)
class PlanSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "start_date", "end_date")
    list_filter = ("status", "plan")
    search_fields = ("user__name", "user__phone", "plan__name")
    autocomplete_fields = ["user", "plan"]
    inlines = [PlanSubscriptionCreditInline]


@admin.register(PlanSubscriptionCredit)
class PlanSubscriptionCreditAdmin(admin.ModelAdmin):
    list_display = ("subscription", "service", "used", "total")
    list_filter = ("service",)
    search_fields = ("subscription__user__name", "subscription__plan__name")
    autocomplete_fields = ["subscription", "service"]
