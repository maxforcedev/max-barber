from django.urls import path
from .views import AppointmentCreateView, AppointmentConfirmView, MyAppointmentsView, AppointmentCancelView

urlpatterns = [
    path("appointments/create/", AppointmentCreateView.as_view(), name="appointment-initiate"),
    path("appointments/confirm/", AppointmentConfirmView.as_view(), name="appointment-confirm"),
    path("appointments/<int:pk>/cancel/", AppointmentCancelView.as_view(), name="appointment-confirm"),
    path("appointments/me/", MyAppointmentsView.as_view(), name="my-appointments"),
]
