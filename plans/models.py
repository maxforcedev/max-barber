from django.db import models
from django.utils import timezone
from accounts.models import User
from services.models import Service


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


class PlanSubscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Ativo"),
        ("expired", "Vencido"),
        ("canceled", "Cancelado"),
        ("paused", "Pausado"),
    ]

    user = models.ForeignKey(User, related_name="subscriptions", on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, related_name="subscriptions", on_delete=models.CASCADE)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return f"{self.user.name} - {self.plan.name}"

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timezone.timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)


class PlanSubscriptionCredit(models.Model):
    subscription = models.ForeignKey(PlanSubscription, related_name="credits", on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    used = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)

    def remaining(self):
        return self.total - self.used

    def __str__(self):
        return f"{self.service.name}: {self.used}/{self.total}"
