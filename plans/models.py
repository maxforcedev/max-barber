from django.db import models


class Plan(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=30)
    is_popular = models.BooleanField(default=False)
    color = models.CharField(max_length=50, blank=True, null=True)
    card_color = models.CharField(max_length=50, blank=True, null=True)

    @property
    def price_original(self):
        """Soma do valor dos serviços no plano."""
        total = 0
        for benefit in self.benefits.select_related("service").all():
            total += benefit.service.price * benefit.quantity
        return total

    @property
    def economia(self):
        return float(self.price_original - self.price) if self.price_original else 0

    def __str__(self):
        return self.name


class PlanBenefit(models.Model):
    DAYS_OF_WEEK = [
        ("mon", "Segunda"),
        ("tue", "Terça"),
        ("wed", "Quarta"),
        ("thu", "Quinta"),
        ("fri", "Sexta"),
        ("sat", "Sábado"),
        ("sun", "Domingo"),
    ]

    plan = models.ForeignKey(Plan, related_name="benefits", on_delete=models.CASCADE)
    service = models.ForeignKey("services.Service", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    allowed_days = models.JSONField(default=list, blank=True)  # ["mon","tue","wed"]

    def __str__(self):
        return f"{self.quantity}x {self.service.name} ({self.plan.name})"
