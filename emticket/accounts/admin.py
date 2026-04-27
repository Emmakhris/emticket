from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import UserProfile

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = ("organization", "site", "department", "team", "role", "is_vip", "notification_prefs")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "organization", "department", "team", "is_vip", "created_at")
    list_filter = ("role", "organization", "is_vip")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    raw_id_fields = ("user", "organization", "site", "department", "team")
    readonly_fields = ("created_at",)
