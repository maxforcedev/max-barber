from django.urls import path
from .views import LoginView, SendLoginCodeView


urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/send-login-code/', SendLoginCodeView.as_view(), name='send-login-code'),
]
