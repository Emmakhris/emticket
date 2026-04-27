from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "object_type", "object_id", "actor", "ip_address", "created_at")
    list_filter = ("event_type", "object_type", "organization")
    search_fields = ("object_id", "event_type", "actor__email")
    readonly_fields = (
        "organization", "actor", "event_type", "object_type", "object_id",
        "before", "after", "metadata", "ip_address", "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
