from __future__ import annotations

from datetime import datetime
from typing import List

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import SLAStatus
from tickets.models import TicketStatus
from automations.services import run_ticket_automations


def _now() -> datetime:
    return timezone.now().astimezone(timezone.utc)


def _progress_ratio(start: datetime, due: datetime, now: datetime) -> float:
    total = max((due - start).total_seconds(), 1.0)
    spent = (now - start).total_seconds()
    return max(0.0, min(spent / total, 10.0))


@shared_task
def sla_scan_and_escalate():
    """
    Runs frequently (e.g., every 60s) to:
    - mark breach flags
    
    - call escalation hooks at thresholds
    """
    run_ticket_automations(
    ticket=ticket,
    trigger="sla_breached",
    actor=None,
    extra={"breach_type": "resolution"}  # or "first_response"
)

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

        # Skip paused; breaches shouldn't accrue while paused
        if sla.paused:
            continue

        # First response breach check
        if sla.first_response_due_at and not ticket.first_response_at:
            if now > sla.first_response_due_at and not sla.breached_first_response:
                sla.breached_first_response = True
                sla.save(update_fields=["breached_first_response", "updated_at"])
                _notify_escalation(ticket_id=str(ticket.id), kind="first_response_breached", ratio=1.0)

            else:
                ratio = _progress_ratio(ticket.created_at.astimezone(timezone.utc), sla.first_response_due_at, now)
                _threshold_escalate(ticket_id=str(ticket.id), kind="first_response", ratio=ratio, thresholds=thresholds)

        # Resolution breach check
        if sla.resolution_due_at and not ticket.resolved_at:
            if now > sla.resolution_due_at and not sla.breached_resolution:
                sla.breached_resolution = True
                sla.save(update_fields=["breached_resolution", "updated_at"])
                _notify_escalation(ticket_id=str(ticket.id), kind="resolution_breached", ratio=1.0)

            else:
                ratio = _progress_ratio(ticket.created_at.astimezone(timezone.utc), sla.resolution_due_at, now)
                _threshold_escalate(ticket_id=str(ticket.id), kind="resolution", ratio=ratio, thresholds=thresholds)


def _threshold_escalate(ticket_id: str, kind: str, ratio: float, thresholds: List[float]) -> None:
    """
    Hook: at thresholds, emit notifications/actions.
    To keep this stateless, we do simple notifications; to avoid duplicates,
    you can record escalation events in AuditEvent / AutomationRun later.
    """
    for t in thresholds:
        if ratio >= t and t < 1.0:
            _notify_escalation(ticket_id=ticket_id, kind=f"{kind}_at_{int(t*100)}", ratio=ratio)


def _notify_escalation(ticket_id: str, kind: str, ratio: float) -> None:
    """
    Replace this with:
    - notifications app (in-app + email)
    - audit log event
    - automation triggers (e.g., auto reassign)
    """
    # For now we just print; swap to logger / Notification model.
    # IMPORTANT: do not spam in production; implement dedupe in AuditEvent or a cache key.
    print(f"[SLA] ticket={ticket_id} event={kind} ratio={ratio:.2f}")





