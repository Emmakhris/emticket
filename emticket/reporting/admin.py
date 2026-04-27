from django.contrib import admin

from .models import SavedView


@admin.register(SavedView)
class SavedViewAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "organization", "is_shared", "created_at")
    list_filter = ("organization", "is_shared")
    search_fields = ("name", "user__email")
    readonly_fields = ("created_at",)
