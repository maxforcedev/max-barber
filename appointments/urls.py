from django.urls import path
from .views import AppointmentCreateView, AppointmentConfirmView

urlpatterns = [
    path("appointments/create/", AppointmentCreateView.as_view(), name="appointment-initiate"),
    path("appointments/confirm/", AppointmentConfirmView.as_view(), name="appointment-confirm"),
]
