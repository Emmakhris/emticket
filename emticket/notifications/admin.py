from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "ticket", "is_read", "created_at")
    list_filter = ("is_read", "organization")
    search_fields = ("user__email", "title")
    readonly_fields = ("organization", "user", "ticket", "title", "body", "created_at")
