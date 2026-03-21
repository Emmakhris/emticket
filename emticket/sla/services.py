from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from organizations.models import WorkingCalendar
from tickets.models import Ticket, TicketStatus
from .models import SLAPolicy, SLAStatus
from organizations.calendar_utils import add_working_minutes


@dataclass(frozen=True)
class ResolvedPolicy:
    policy: SLAPolicy
    calendar: WorkingCalendar


def _get_calendar_for_ticket(ticket: Ticket) -> WorkingCalendar:
    """
    Calendar is per site. If no site or missing calendar, provide a fallback 24/7 calendar.
    """
    if ticket.site_id and hasattr(ticket.site, "calendar"):
        return ticket.site.calendar

    # fallback 24/7 calendar
    # Weekly: every day 00:00-23:59
    from organizations.models import WorkingCalendar, Site
    wc = WorkingCalendar(
        site=ticket.site if ticket.site_id else Site(id=1),  # dummy site; not saved
        timezone=getattr(settings, "TIME_ZONE", "UTC"),
        weekly_hours={k: [["00:00", "23:59"]] for k in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]},
        holidays=[],
    )
    return wc


def resolve_sla_policy(ticket: Ticket) -> Optional[ResolvedPolicy]:
    """
    Precedence:
      1) category + site + priority
      2) category + priority
      3) department + priority
      4) org default (department + priority with category/site null can serve as default)
    """
    if not ticket.organization_id or not ticket.department_id:
        return None

    base = SLAPolicy.objects.filter(
        organization_id=ticket.organization_id,
        department_id=ticket.department_id,
        priority=ticket.priority,
        is_active=True,
    )

    # 1) category + site
    if ticket.category_id and ticket.site_id:
        p = base.filter(category_id=ticket.category_id, site_id=ticket.site_id).first()
        if p:
            return ResolvedPolicy(policy=p, calendar=_get_calendar_for_ticket(ticket))

    # 2) category only
    if ticket.category_id:
        p = base.filter(category_id=ticket.category_id, site__isnull=True).first()
        if p:
            return ResolvedPolicy(policy=p, calendar=_get_calendar_for_ticket(ticket))

    # 3) department only
    p = base.filter(category__isnull=True, site__isnull=True).first()
    if p:
        return ResolvedPolicy(policy=p, calendar=_get_calendar_for_ticket(ticket))

    return None


def _now_utc() -> datetime:
    return timezone.now().astimezone(timezone.utc)


def _should_pause(status: str) -> bool:
    pause_statuses = getattr(settings, "SLA_PAUSE_STATUSES", {"on_hold", "waiting_requester"})
    return status in pause_statuses


def initialize_or_recompute_sla(ticket: Ticket) -> SLAStatus:
    """
    Ensures SLAStatus exists and computes due dates if missing.
    Should be called on ticket creation and when priority/category/site changes.
    """
    resolved = resolve_sla_policy(ticket)
    if not resolved:
        # Create SLAStatus but leave due times null (no policy found)
        sla, _ = SLAStatus.objects.get_or_create(ticket=ticket)
        return sla

    now = _now_utc()
    sla, _ = SLAStatus.objects.get_or_create(ticket=ticket)

    # If first response already happened, we don't need to compute first-response due
    if not ticket.first_response_at and not sla.first_response_due_at:
        sla.first_response_due_at = add_working_minutes(resolved.calendar, now, resolved.policy.first_response_minutes)

    # If ticket already resolved, no need to compute resolution due
    if not ticket.resolved_at and not sla.resolution_due_at:
        sla.resolution_due_at = add_working_minutes(resolved.calendar, now, resolved.policy.resolution_minutes)

    # pause state based on ticket current status
    if _should_pause(ticket.status):
        if not sla.paused:
            sla.paused = True
            sla.paused_reason = f"Paused due to status={ticket.status}"
            sla.paused_at = now
    else:
        if sla.paused:
            _resume_sla_clock(sla, now)

    sla.save()
    return sla


def mark_first_response(ticket: Ticket, at: Optional[datetime] = None) -> None:
    """
    Call this when an agent posts a public reply for first time.
    """
    at = (at or _now_utc())
    if ticket.first_response_at:
        return

    ticket.first_response_at = at
    if ticket.status == TicketStatus.NEW:
        ticket.status = TicketStatus.OPEN
    ticket.save(update_fields=["first_response_at", "status", "updated_at"])

    # SLAStatus: if breached flag should be updated in scanner; due_at can remain
    SLAStatus.objects.get_or_create(ticket=ticket)


def on_ticket_status_change(ticket: Ticket, old_status: str, new_status: str) -> None:
    """
    Handles pause/resume + resolution timestamps. Call from a service layer or signal.
    """
    now = _now_utc()
    sla, _ = SLAStatus.objects.get_or_create(ticket=ticket)

    # status timestamps
    if new_status == TicketStatus.RESOLVED and not ticket.resolved_at:
        ticket.resolved_at = now
        ticket.save(update_fields=["resolved_at", "updated_at"])

    if new_status == TicketStatus.CLOSED and not ticket.closed_at:
        ticket.closed_at = now
        ticket.save(update_fields=["closed_at", "updated_at"])

    # pause / resume
    if _should_pause(new_status) and not sla.paused:
        sla.paused = True
        sla.paused_reason = f"Paused due to status={new_status}"
        sla.paused_at = now
        sla.save(update_fields=["paused", "paused_reason", "paused_at", "updated_at"])
        return

    if (not _should_pause(new_status)) and sla.paused:
        _resume_sla_clock(sla, now)
        sla.save(update_fields=[
            "paused", "paused_reason", "paused_at",
            "first_response_due_at", "resolution_due_at",
            "total_paused_seconds", "updated_at"
        ])


def _resume_sla_clock(sla: SLAStatus, now: datetime) -> None:
    if not sla.paused or not sla.paused_at:
        sla.paused = False
        sla.paused_reason = ""
        sla.paused_at = None
        return

    paused_seconds = int((now - sla.paused_at).total_seconds())
    sla.total_paused_seconds += max(paused_seconds, 0)

    # Shift due times forward by paused duration (in real time).
    # This is correct because pause is outside business time.
    if sla.first_response_due_at and not sla.ticket.first_response_at:
        sla.first_response_due_at = sla.first_response_due_at + timezone.timedelta(seconds=paused_seconds)
    if sla.resolution_due_at and not sla.ticket.resolved_at:
        sla.resolution_due_at = sla.resolution_due_at + timezone.timedelta(seconds=paused_seconds)

    sla.paused = False
    sla.paused_reason = ""
    sla.paused_at = None


@transaction.atomic
def get_or_create_sla(ticket_id) -> SLAStatus:
    ticket = Ticket.objects.select_for_update().select_related("site").get(id=ticket_id)
    return initialize_or_recompute_sla(ticket)
