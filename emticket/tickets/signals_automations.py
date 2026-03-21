from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from tickets.models import Ticket
from automations.services import run_ticket_automations


@receiver(pre_save, sender=Ticket)
def ticket_capture_changes(sender, instance: Ticket, **kwargs):
    if not instance.pk:
        instance._automation_changes = {}
        return

    try:
        old = Ticket.objects.get(pk=instance.pk)
    except Ticket.DoesNotExist:
        instance._automation_changes = {}
        return

    # Track relevant fields that rules may check via "changed"/"changed_to"
    watched_fields = [
        "status", "priority", "impact", "urgency",
        "team_id", "assignee_id",
        "category_id", "subcategory_id",
        "site_id", "department_id",
        "visibility",
    ]

    changes = {}
    for f in watched_fields:
        old_v = getattr(old, f)
        new_v = getattr(instance, f)
        if old_v != new_v:
            changes[f] = (old_v, new_v)

    instance._automation_changes = changes


@receiver(post_save, sender=Ticket)
def ticket_run_automations(sender, instance: Ticket, created: bool, **kwargs):
    if created:
        run_ticket_automations(ticket=instance, trigger="ticket_created", actor=instance.requester)
        return

    changes = getattr(instance, "_automation_changes", {}) or {}
    if changes:
        run_ticket_automations(ticket=instance, trigger="ticket_updated", actor=None, changes=changes)
