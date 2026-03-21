from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models

from organizations.models import Organization
from tickets.models import Ticket


class Notification(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="notifications")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")

    ticket = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
