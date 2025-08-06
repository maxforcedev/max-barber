from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('id', 'phone', 'name', 'email', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('phone', 'email', 'name')
    ordering = ('date_joined',)

    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Informações pessoais', {'fields': ('name', 'email', 'role')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'name', 'email', 'password1', 'password2', 'role', 'is_active', 'is_staff', 'is_superuser')}
        )
    )
