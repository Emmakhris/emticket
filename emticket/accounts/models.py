from django.conf import settings
from django.db import models

from organizations.models import Organization, Site, Department, Team


class Role(models.TextChoices):
    REQUESTER = "requester", "Requester"
    AGENT = "agent", "Agent"
    SUPERVISOR = "supervisor", "Supervisor"
    TEAM_LEAD = "team_lead", "Team Lead"
    ADMIN = "admin", "Admin"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="user_profiles")

    site = models.ForeignKey(Site, on_delete=models.PROTECT, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.PROTECT, null=True, blank=True)

    role = models.CharField(max_length=32, choices=Role.choices, default=Role.REQUESTER)
    is_vip = models.BooleanField(default=False)

    # Notification settings:
    # {"email":{"ticket_assigned":true}, "in_app":{"mentions":true}}
    notification_prefs = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user} ({self.role})"
