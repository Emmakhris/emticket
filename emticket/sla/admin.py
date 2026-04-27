from django.contrib import admin

from .models import SLAPolicy, SLAStatus


@admin.register(SLAPolicy)
class SLAPolicyAdmin(admin.ModelAdmin):
    list_display = ("organization", "department", "priority", "first_response_minutes", "resolution_minutes", "site", "category", "is_active")
    list_filter = ("organization", "department", "priority", "is_active")
    search_fields = ("organization__name", "department__name")


@admin.register(SLAStatus)
class SLAStatusAdmin(admin.ModelAdmin):
    list_display = ("ticket", "first_response_due_at", "resolution_due_at", "breached_first_response", "breached_resolution", "paused")
    list_filter = ("breached_first_response", "breached_resolution", "paused")
    search_fields = ("ticket__ticket_number",)
    readonly_fields = (
        "ticket", "first_response_due_at", "resolution_due_at",
        "breached_first_response", "breached_resolution",
        "paused", "paused_reason", "paused_at", "total_paused_seconds",
        "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
