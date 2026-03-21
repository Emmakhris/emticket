from django.db import models

from organizations.models import Organization, Department, Site
from tickets.models import Priority, TicketCategory, Ticket


class SLAPolicy(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="sla_policies")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="sla_policies")

    # optional scoping
    site = models.ForeignKey(Site, on_delete=models.PROTECT, null=True, blank=True)
    category = models.ForeignKey(TicketCategory, on_delete=models.PROTECT, null=True, blank=True)

    priority = models.IntegerField(choices=Priority.choices)

    first_response_minutes = models.PositiveIntegerField()
    resolution_minutes = models.PositiveIntegerField()

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "department", "site", "category", "priority")


class SLAStatus(models.Model):
    """
    Computed per-ticket SLA timers.
    """
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name="sla")

    first_response_due_at = models.DateTimeField(null=True, blank=True)
    resolution_due_at = models.DateTimeField(null=True, blank=True)

    breached_first_response = models.BooleanField(default=False)
    breached_resolution = models.BooleanField(default=False)

    paused = models.BooleanField(default=False)
    paused_reason = models.CharField(max_length=120, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    total_paused_seconds = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
