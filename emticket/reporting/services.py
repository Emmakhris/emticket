from dataclasses import dataclass, field
from datetime import timedelta
from typing import List

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDay
from django.utils import timezone

from tickets.models import Ticket, TicketStatus

_ACTIVE = [
    TicketStatus.NEW,
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.ON_HOLD,
    TicketStatus.WAITING_REQUESTER,
    TicketStatus.ESCALATED,
    TicketStatus.REOPENED,
]


@dataclass
class DashboardStats:
    open_count: int = 0
    sla_breached_count: int = 0
    unassigned_count: int = 0
    resolved_today_count: int = 0
    my_queue: List = field(default_factory=list)
    breaching_soon: List = field(default_factory=list)


def get_dashboard_stats(user, org) -> DashboardStats:
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    soon = now + timedelta(hours=2)

    base = Ticket.objects.filter(organization=org)
    active = base.filter(status__in=_ACTIVE)

    open_count = active.count()
    unassigned_count = active.filter(assignee=None).count()

    resolved_today_count = base.filter(
        status__in=[TicketStatus.RESOLVED, TicketStatus.CLOSED],
        resolved_at__gte=today_start,
    ).count()

    try:
        sla_breached_count = active.filter(
            Q(sla__breached_first_response=True) | Q(sla__breached_resolution=True)
        ).count()
    except Exception:
        sla_breached_count = 0

    my_queue = list(
        active.filter(assignee=user)
        .select_related("department", "category", "sla")
        .order_by("priority", "-updated_at")[:20]
    )

    try:
        breaching_soon = list(
            active.filter(
                sla__breached_resolution=False,
                sla__paused=False,
                sla__resolution_due_at__gt=now,
                sla__resolution_due_at__lte=soon,
            ).select_related("sla", "department", "assignee")
            .order_by("sla__resolution_due_at")[:10]
        )
    except Exception:
        breaching_soon = []

    return DashboardStats(
        open_count=open_count,
        sla_breached_count=sla_breached_count,
        unassigned_count=unassigned_count,
        resolved_today_count=resolved_today_count,
        my_queue=my_queue,
        breaching_soon=breaching_soon,
    )


def get_volume_by_day(org, days: int = 30):
    since = timezone.now() - timedelta(days=days)
    return list(
        Ticket.objects.filter(organization=org, created_at__gte=since)
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )


def get_sla_compliance(org, days: int = 30):
    since = timezone.now() - timedelta(days=days)
    try:
        from sla.models import SLAStatus
        total = SLAStatus.objects.filter(ticket__organization=org, created_at__gte=since).count()
        breached = SLAStatus.objects.filter(
            ticket__organization=org, created_at__gte=since
        ).filter(Q(breached_first_response=True) | Q(breached_resolution=True)).count()
        compliant = total - breached
        rate = round((compliant / total * 100), 1) if total else 100.0
        return {"total": total, "breached": breached, "compliant": compliant, "rate": rate}
    except Exception:
        return {"total": 0, "breached": 0, "compliant": 0, "rate": 100.0}


def get_agent_workload(org):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    active_statuses = [
        TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.IN_PROGRESS,
        TicketStatus.ON_HOLD, TicketStatus.WAITING_REQUESTER, TicketStatus.ESCALATED,
    ]
    return list(
        Ticket.objects.filter(organization=org, status__in=active_statuses, assignee__isnull=False)
        .values("assignee__email")
        .annotate(count=Count("id"))
        .order_by("-count")[:15]
    )


def get_category_breakdown(org, days: int = 30):
    since = timezone.now() - timedelta(days=days)
    return list(
        Ticket.objects.filter(organization=org, created_at__gte=since, category__isnull=False)
        .values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
