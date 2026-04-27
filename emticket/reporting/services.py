from dataclasses import dataclass, field
from datetime import timedelta
from typing import List

from django.db.models import Q
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
