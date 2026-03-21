from django.db import models

# Create your models here.
from django.db import models

from organizations.models import Organization, Site


class AssetType(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="asset_types")
    name = models.CharField(max_length=120)  # Printer, Router, ECG, Lab Analyzer

    class Meta:
        unique_together = ("organization", "name")

    def __str__(self) -> str:
        return self.name


class AssetLocation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="asset_locations")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(max_length=255)  # Ward A, Lab Room 2, Admin Block
    details = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("organization", "site", "name")

    def __str__(self) -> str:
        return self.name


class Asset(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="assets")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, null=True, blank=True)

    asset_id = models.CharField(max_length=80, unique=True)  # e.g. BIOMED-ECG-001
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT)

    vendor = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)

    location = models.ForeignKey(AssetLocation, on_delete=models.SET_NULL, null=True, blank=True)
    location_text = models.CharField(max_length=255, blank=True)  # fallback text
    notes = models.TextField(blank=True)

    maintenance_schedule = models.JSONField(default=dict, blank=True)  # future
    in_service = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.asset_id
