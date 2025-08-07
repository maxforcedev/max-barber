from django.urls import path
from .views import LoginView, SendLoginCodeView


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('send-login-code/', SendLoginCodeView.as_view(), name='send-login-code'),
]
