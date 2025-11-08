from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Datos adicionales",
            {"fields": ("dni", "phone", "role", "created_at", "updated_at")},
        ),
    )
    readonly_fields = ("created_at", "updated_at")
    list_display = ("id", "username", "first_name", "last_name", "email", "phone", "dni", "role", "is_active")
    search_fields = ("username", "first_name", "last_name", "email", "dni", "phone")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")

