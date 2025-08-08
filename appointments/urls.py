from django.urls import path
from .views import AppointmentCreateView, AppointmentConfirmView

urlpatterns = [
    path("initiate/", AppointmentCreateView.as_view(), name="appointment-initiate"),
    path("confirm/", AppointmentConfirmView.as_view(), name="appointment-confirm"),
]
