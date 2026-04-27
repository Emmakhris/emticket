from django.contrib import admin

from .models import AutomationRule, AutomationRun


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "trigger", "enabled", "priority", "updated_at")
    list_filter = ("organization", "trigger", "enabled")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(AutomationRun)
class AutomationRunAdmin(admin.ModelAdmin):
    list_display = ("rule", "object_type", "object_id", "matched", "ran_at", "error")
    list_filter = ("matched", "object_type", "organization")
    search_fields = ("object_id", "rule__name")
    readonly_fields = (
        "organization", "rule", "object_type", "object_id",
        "ran_at", "matched", "actions_executed", "error",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
