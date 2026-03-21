from __future__ import annotations

from typing import Any, Dict, Tuple, Optional

from django.db import transaction

from tickets.models import Ticket
from .conditions import EvalContext
from .engine import AutomationEngine


def run_ticket_automations(
    *,
    ticket: Ticket,
    trigger: str,
    actor=None,
    changes: Optional[Dict[str, Tuple[Any, Any]]] = None,
    extra: Optional[Dict[str, Any]] = None,
):
    """
    Runs automations for a ticket in a deterministic way.
    Use in:
      - ticket created
      - ticket updated (pass changes)
      - ticket commented (pass extra about internal/public)
      - SLA breached
    """
    if not ticket.organization_id:
        return []

    ctx = EvalContext(
        obj=ticket,
        actor=actor,
        trigger=trigger,
        changes=changes or {},
        extra=extra or {},
    )

    engine = AutomationEngine(organization_id=ticket.organization_id, trigger=trigger)
    return engine.run(ctx)
