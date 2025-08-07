from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('phone', 'name', 'email', 'role')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('phone', 'name', 'email', 'role', 'is_active', 'is_staff', 'is_superuser')
