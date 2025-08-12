from django.urls import path
from . import views


urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/send-login-code/', views.SendLoginCodeView.as_view(), name='send-login-code'),
    path("clients/check", views.ClientCheckView.as_view(), name="check-client"),
]
