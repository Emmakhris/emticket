from django.conf import settings
from django.db import models

from organizations.models import Organization


class SavedView(models.Model):
    """
    Stores user-defined filters for ticket list views.
    filter_json example:
      {"status":["open","in_progress"], "priority":[1,2], "assignee":"me"}
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="saved_views")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_views")

    name = models.CharField(max_length=120)
    filter_json = models.JSONField(default=dict, blank=True)
    is_shared = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "user", "name")
