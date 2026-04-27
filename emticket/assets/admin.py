from django.contrib import admin

from .models import Asset, AssetLocation, AssetType


@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "organization")
    list_filter = ("organization",)
    search_fields = ("name",)


@admin.register(AssetLocation)
class AssetLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "organization", "details")
    list_filter = ("organization", "site")
    search_fields = ("name",)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_id", "asset_type", "vendor", "model", "site", "location", "in_service", "created_at")
    list_filter = ("organization", "asset_type", "in_service", "site")
    search_fields = ("asset_id", "vendor", "model", "serial_number")
    readonly_fields = ("created_at",)
