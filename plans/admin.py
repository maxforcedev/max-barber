from django.contrib import admin
from .models import Plan, PlanBenefit


class PlanBenefitInline(admin.TabularInline):
    model = PlanBenefit
    extra = 1
    fields = ("service", "quantity", "allowed_days")
    autocomplete_fields = ["service"]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "price_original", "economia", "duration_days", "is_popular")
    search_fields = ("name", "slug")
    list_filter = ("is_popular",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [PlanBenefitInline]

    def economia(self, obj):
        return obj.economia
    economia.short_description = "Economia (R$)"


@admin.register(PlanBenefit)
class PlanBenefitAdmin(admin.ModelAdmin):
    list_display = ("plan", "service", "quantity", "get_allowed_days")
    search_fields = ("plan__name", "service__name")
    list_filter = ("allowed_days",)

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
