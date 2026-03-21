from django.conf import settings
from django.db import models

from organizations.models import Organization


class AuditEvent(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)

    event_type = models.CharField(max_length=120)   # ticket.created, ticket.status_changed, etc.
    object_type = models.CharField(max_length=120)  # Ticket, SLAStatus, etc.
    object_id = models.CharField(max_length=120)

    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["created_at"]),
        ]
