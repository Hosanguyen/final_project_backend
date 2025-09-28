from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "phone", "is_staff", "is_active")
    search_fields = ("username", "email", "phone")
    list_filter = ("is_staff", "is_active")

    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("phone",)}),
    )
