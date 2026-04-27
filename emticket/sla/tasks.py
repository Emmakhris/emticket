from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import SLAStatus
from automations.services import run_ticket_automations

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return timezone.now().astimezone(timezone.utc)


def _progress_ratio(start: datetime, due: datetime, now: datetime) -> float:
    total = max((due - start).total_seconds(), 1.0)
    spent = (now - start).total_seconds()
    return max(0.0, min(spent / total, 10.0))


@shared_task
def sla_scan_and_escalate():
    """
    Runs every 60 s via Celery beat to mark SLA breach flags and fire escalation hooks.
    """
    now = _now()
    thresholds: List[float] = getattr(settings, "SLA_ESCALATION_THRESHOLDS", [0.7, 0.9, 1.0])

    qs = (
        SLAStatus.objects
        .select_related("ticket")
        .filter(ticket__status__in=[
            "new", "open", "in_progress", "on_hold", "waiting_requester", "escalated", "reopened"
        ])
    )

    for sla in qs.iterator(chunk_size=500):
        ticket = sla.ticket

        if sla.paused:
            continue

        # First response breach check
        if sla.first_response_due_at and not ticket.first_response_at:
            if now > sla.first_response_due_at and not sla.breached_first_response:
                sla.breached_first_response = True
                sla.save(update_fields=["breached_first_response", "updated_at"])
                _notify_escalation(ticket=ticket, kind="first_response_breached", ratio=1.0)
                run_ticket_automations(
                    ticket=ticket,
                    trigger="sla_breached",
                    actor=None,
                    extra={"breach_type": "first_response"},
                )
            else:
                ratio = _progress_ratio(ticket.created_at.astimezone(timezone.utc), sla.first_response_due_at, now)
                _threshold_escalate(ticket=ticket, kind="first_response", ratio=ratio, thresholds=thresholds)

        # Resolution breach check
        if sla.resolution_due_at and not ticket.resolved_at:
            if now > sla.resolution_due_at and not sla.breached_resolution:
                sla.breached_resolution = True
                sla.save(update_fields=["breached_resolution", "updated_at"])
                _notify_escalation(ticket=ticket, kind="resolution_breached", ratio=1.0)
                run_ticket_automations(
                    ticket=ticket,
                    trigger="sla_breached",
                    actor=None,
                    extra={"breach_type": "resolution"},
                )
            else:
                ratio = _progress_ratio(ticket.created_at.astimezone(timezone.utc), sla.resolution_due_at, now)
                _threshold_escalate(ticket=ticket, kind="resolution", ratio=ratio, thresholds=thresholds)


def _threshold_escalate(ticket, kind: str, ratio: float, thresholds: List[float]) -> None:
    for t in thresholds:
        if ratio >= t and t < 1.0:
            _notify_escalation(ticket=ticket, kind=f"{kind}_at_{int(t * 100)}", ratio=ratio)


def _notify_escalation(ticket, kind: str, ratio: float) -> None:
    logger.warning("[SLA] ticket=%s event=%s ratio=%.2f", ticket.id, kind, ratio)

    if ratio < 1.0:
        return

    from notifications.models import Notification
    from notifications.tasks import send_notification_email

    event_type = (
        "sla.first_response_breached" if "first_response" in kind else "sla.resolution_breached"
    )
    title = f"SLA breach: {ticket.ticket_number or ticket.id}"

    targets = []
    if ticket.assignee:
        targets.append(ticket.assignee)
    if ticket.requester and ticket.requester != ticket.assignee:
        targets.append(ticket.requester)

    for user in targets:
        notif = Notification.objects.create(
            organization=ticket.organization,
            user=user,
            ticket=ticket,
            title=title[:255],
            body=f"SLA breach event: {kind}",
        )
        send_notification_email.delay(notif.pk, event_type)





