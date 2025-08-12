from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PlanSubscription, PlanSubscriptionCredit, PlanBenefit

@receiver(post_save, sender=PlanSubscription)
def create_plan_subscription_credits(sender, instance, created, **kwargs):

    if created:
        if instance.credits.exists():
            return
        
        benefits = PlanBenefit.objects.filter(plan=instance.plan)
        for benefit in benefits:
            PlanSubscriptionCredit.objects.create(
                subscription=instance,
                service=benefit.service,
                total=benefit.quantity,
                used=0
            )
