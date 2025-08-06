from django.db import models


class Barber(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='barber')
    photo = models.ImageField(blank=True, null=True)
    services = models.ManyToManyField('services.Service', related_name='barbers')


class WorkingHour(models.Model):
    barber = models.ForeignKey('barbers.Barber', on_delete=models.CASCADE, related_name='working_hours')
    weekday = models.IntegerField(choices=[(i, day) for i, day in enumerate(['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'])])
    start_time = models.TimeField()
    end_time = models.TimeField()


class BlockedTime(models.Model):
    barber = models.ForeignKey('barbers.Barber', on_delete=models.CASCADE, related_name='blocked_times')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=100, blank=True, null=True)
