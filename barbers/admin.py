from django.contrib import admin
from .models import Barber, WorkingHour, BlockedTime


class WorkingHourInline(admin.TabularInline):
    model = WorkingHour
    extra = 1
    fields = ("weekday", "start_time", "end_time")
    ordering = ("weekday", "start_time")


class BlockedTimeInline(admin.TabularInline):
    model = BlockedTime
    extra = 0
    fields = ("date", "start_time", "end_time", "reason")
    ordering = ("-date", "start_time")


@admin.register(Barber)
class BarberAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "services_count")
    search_fields = ("user__name", "user__phone", "user__email")
    filter_horizontal = ("services",)
    inlines = [WorkingHourInline, BlockedTimeInline]

    def services_count(self, obj):
        return obj.services.count()
    services_count.short_description = "Serviços"


@admin.register(WorkingHour)
class WorkingHourAdmin(admin.ModelAdmin):
    list_display = ("barber", "weekday", "start_time", "end_time")
    list_filter = ("weekday", "barber")
    search_fields = ("barber__user__name",)
    ordering = ("barber", "weekday", "start_time")


@admin.register(BlockedTime)
class BlockedTimeAdmin(admin.ModelAdmin):
    list_display = ("barber", "date", "start_time", "end_time", "reason")
    list_filter = ("barber", "date")
    search_fields = ("barber__user__name", "reason")
    ordering = ("-date", "start_time")
