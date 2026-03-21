import uuid
from django.conf import settings
from django.db import models

from organizations.models import Organization, Site, Department, Team
from assets.models import Asset


class TicketStatus(models.TextChoices):
    NEW = "new", "New"
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In Progress"
    ON_HOLD = "on_hold", "On Hold"
    WAITING_REQUESTER = "waiting_requester", "Waiting for Requester"
    ESCALATED = "escalated", "Escalated"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"
    REOPENED = "reopened", "Reopened"


class Visibility(models.TextChoices):
    NORMAL = "normal", "Normal"
    CONFIDENTIAL = "confidential", "Confidential"


class Impact(models.IntegerChoices):
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"
    CRITICAL = 4, "Critical"


class Urgency(models.IntegerChoices):
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"
    IMMEDIATE = 4, "Immediate"


class Priority(models.IntegerChoices):
    P1 = 1, "P1 - Critical"
    P2 = 2, "P2 - High"
    P3 = 3, "P3 - Medium"
    P4 = 4, "P4 - Low"


class TicketCategory(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="ticket_categories")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="ticket_categories")
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "department", "name")

    def __str__(self) -> str:
        return f"{self.department.code}: {self.name}"


class TicketSubcategory(models.Model):
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("category", "name")

    def __str__(self) -> str:
        return f"{self.category.name} > {self.name}"


class TicketSequence(models.Model):
    """
    Collision-free ticket numbering support.
    Use SELECT FOR UPDATE to increment safely.
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    year = models.PositiveIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("organization", "department", "year")


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="tickets")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, null=True, blank=True)

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_tickets"
    )

    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="tickets")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, null=True, blank=True, related_name="tickets")

    category = models.ForeignKey(TicketCategory, on_delete=models.PROTECT)
    subcategory = models.ForeignKey(TicketSubcategory, on_delete=models.PROTECT, null=True, blank=True)

    title = models.CharField(max_length=255)
    description = models.TextField()

    impact = models.IntegerField(choices=Impact.choices, default=Impact.MEDIUM)
    urgency = models.IntegerField(choices=Urgency.choices, default=Urgency.MEDIUM)
    priority = models.IntegerField(choices=Priority.choices, default=Priority.P3)

    status = models.CharField(max_length=32, choices=TicketStatus.choices, default=TicketStatus.NEW)
    visibility = models.CharField(max_length=32, choices=Visibility.choices, default=Visibility.NORMAL)

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="assigned_tickets"
    )

    location_detail = models.CharField(max_length=255, blank=True)  # Ward, room, unit
    tags = models.JSONField(default=list, blank=True)

    related_asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets")

    ticket_number = models.CharField(max_length=40, unique=True, blank=True)  # generated via sequence
    merged_into = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="merged_children")

    parent_ticket = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="subtasks")

    watchers = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="watched_tickets")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.ticket_number or str(self.id)


class TicketDependency(models.Model):
    """
    blocked_ticket is blocked by depends_on_ticket
    """
    blocked_ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="blocked_by_links")
    depends_on_ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="blocking_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("blocked_ticket", "depends_on_ticket")


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file = models.FileField(upload_to="ticket_attachments/%Y/%m/")
    filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class TicketLink(models.Model):
    """
    Link related tickets (related/duplicate/parent/child/incident/etc).
    """
    from_ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="links_out")
    to_ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="links_in")
    relation = models.CharField(max_length=50, default="related")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_ticket", "to_ticket", "relation")


class CSAT(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name="csat")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    rating = models.PositiveSmallIntegerField()  # 1..5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
