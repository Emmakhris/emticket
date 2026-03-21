from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Ticket
from sla.services import initialize_or_recompute_sla, on_ticket_status_change


@receiver(pre_save, sender=Ticket)
def ticket_pre_save(sender, instance: Ticket, **kwargs):
    if not instance.pk:
        instance._old_status = None
    else:
        try:
            old = Ticket.objects.only("status").get(pk=instance.pk)
            instance._old_status = old.status
        except Ticket.DoesNotExist:
            instance._old_status = None


@receiver(post_save, sender=Ticket)
def ticket_post_save(sender, instance: Ticket, created: bool, **kwargs):
    if created:
        initialize_or_recompute_sla(instance)
        return

    old_status = getattr(instance, "_old_status", None)
    if old_status and old_status != instance.status:
        on_ticket_status_change(instance, old_status, instance.status)
