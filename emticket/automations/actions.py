from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.utils import timezone

from organizations.models import Team
from tickets.models import Ticket, TicketStatus
from notifications.models import Notification

User = get_user_model()


@dataclass
class ActionResult:
    ok: bool
    detail: str
    changed: bool = False


def _ensure_ticket(obj: Any) -> Ticket:
    if not isinstance(obj, Ticket):
        raise ValueError("Automation actions currently support Ticket objects only.")
    return obj


def action_set_status(ticket: Ticket, status: str) -> ActionResult:
    if status not in dict(TicketStatus.choices):
        return ActionResult(False, f"Invalid status: {status}")

    if ticket.status == status:
        return ActionResult(True, "No change (status already set).", changed=False)

    ticket.status = status
    if status == TicketStatus.RESOLVED and not ticket.resolved_at:
        ticket.resolved_at = timezone.now()
    if status == TicketStatus.CLOSED and not ticket.closed_at:
        ticket.closed_at = timezone.now()

    ticket.save(update_fields=["status", "resolved_at", "closed_at", "updated_at"])
    return ActionResult(True, f"Status set to {status}.", changed=True)


def action_set_priority(ticket: Ticket, priority: int) -> ActionResult:
    if ticket.priority == priority:
        return ActionResult(True, "No change (priority already set).", changed=False)

    ticket.priority = priority
    ticket.save(update_fields=["priority", "updated_at"])
    return ActionResult(True, f"Priority set to {priority}.", changed=True)


def action_assign_team(ticket: Ticket, team_id: int) -> ActionResult:
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return ActionResult(False, f"Team not found: {team_id}")

    if ticket.team_id == team.id:
        return ActionResult(True, "No change (team already set).", changed=False)

    ticket.team = team
    if ticket.status == TicketStatus.NEW:
        ticket.status = TicketStatus.OPEN

    ticket.save(update_fields=["team", "status", "updated_at"])
    return ActionResult(True, f"Assigned team {team_id}.", changed=True)


def action_assign_user(ticket: Ticket, user_id: int) -> ActionResult:
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return ActionResult(False, f"User not found: {user_id}")

    if ticket.assignee_id == user.id:
        return ActionResult(True, "No change (assignee already set).", changed=False)

    ticket.assignee = user
    if ticket.status == TicketStatus.NEW:
        ticket.status = TicketStatus.OPEN

    ticket.save(update_fields=["assignee", "status", "updated_at"])
    return ActionResult(True, f"Assigned user {user_id}.", changed=True)


def action_unassign(ticket: Ticket) -> ActionResult:
    if ticket.assignee_id is None:
        return ActionResult(True, "No change (already unassigned).", changed=False)

    ticket.assignee = None
    ticket.save(update_fields=["assignee", "updated_at"])
    return ActionResult(True, "Assignee cleared.", changed=True)


def action_add_tags(ticket: Ticket, tags: List[str]) -> ActionResult:
    tags = [t.strip() for t in (tags or []) if t and t.strip()]
    if not tags:
        return ActionResult(True, "No tags provided.", changed=False)

    current = list(ticket.tags or [])
    new_tags = current[:]
    changed = False

    for tag in tags:
        if tag not in new_tags:
            new_tags.append(tag)
            changed = True

    if not changed:
        return ActionResult(True, "No change (tags already present).", changed=False)

    ticket.tags = new_tags
    ticket.save(update_fields=["tags", "updated_at"])
    return ActionResult(True, f"Added tags: {tags}", changed=True)


def action_remove_tags(ticket: Ticket, tags: List[str]) -> ActionResult:
    tags = [t.strip() for t in (tags or []) if t and t.strip()]
    if not tags:
        return ActionResult(True, "No tags provided.", changed=False)

    current = list(ticket.tags or [])
    new_tags = [t for t in current if t not in tags]

    if new_tags == current:
        return ActionResult(True, "No change (tags not present).", changed=False)

    ticket.tags = new_tags
    ticket.save(update_fields=["tags", "updated_at"])
    return ActionResult(True, f"Removed tags: {tags}", changed=True)


def action_add_watcher(ticket: Ticket, user_id: int) -> ActionResult:
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return ActionResult(False, f"User not found: {user_id}")

    if ticket.watchers.filter(id=user.id).exists():
        return ActionResult(True, "No change (already watching).", changed=False)

    ticket.watchers.add(user)
    return ActionResult(True, f"Added watcher {user_id}.", changed=True)


def action_set_visibility(ticket: Ticket, visibility: str) -> ActionResult:
    if visibility not in ("normal", "confidential"):
        return ActionResult(False, f"Invalid visibility: {visibility}")

    if ticket.visibility == visibility:
        return ActionResult(True, "No change (visibility already set).", changed=False)

    ticket.visibility = visibility
    ticket.save(update_fields=["visibility", "updated_at"])
    return ActionResult(True, f"Visibility set to {visibility}.", changed=True)


def action_notify(ticket: Ticket, payload: Dict[str, Any]) -> ActionResult:
    payload = payload or {}
    title = payload.get("title") or "Notification"
    body = payload.get("body") or ""

    to = payload.get("to")
    user_id = payload.get("user_id")

    user = None
    if user_id:
        try:
            user = User.objects.get(id=int(user_id))
        except Exception:
            return ActionResult(False, f"notify: invalid user_id={user_id}")
    elif to == "assignee":
        user = ticket.assignee
    elif to == "requester":
        user = ticket.requester

    if not user:
        return ActionResult(False, "notify: no target user resolved")

    Notification.objects.create(
        organization=ticket.organization,
        user=user,
        ticket=ticket,
        title=str(title)[:255],
        body=str(body),
    )
    return ActionResult(True, f"Notified user {user.id}.", changed=True)


def action_create_subtask(ticket: Ticket, payload: Dict[str, Any]) -> ActionResult:
    payload = payload or {}

    title = payload.get("title") or f"Subtask for {ticket.ticket_number or ticket.id}"
    description = payload.get("description") or ""
    team_id = payload.get("team_id")
    priority = payload.get("priority", ticket.priority)

    subtask = Ticket.objects.create(
        organization=ticket.organization,
        site=ticket.site,
        requester=ticket.requester,
        department=ticket.department,
        team_id=team_id,
        category=ticket.category,
        subcategory=ticket.subcategory,
        title=str(title)[:255],
        description=str(description),
        impact=ticket.impact,
        urgency=ticket.urgency,
        priority=int(priority),
        status=TicketStatus.NEW,
        parent_ticket=ticket,
        visibility=ticket.visibility,
        location_detail=ticket.location_detail,
        related_asset=ticket.related_asset,
        tags=list(ticket.tags or []),
    )
    subtask.watchers.add(ticket.requester)
    return ActionResult(True, f"Created subtask {subtask.id}.", changed=True)


ACTION_REGISTRY = {
    "set_status": action_set_status,
    "set_priority": action_set_priority,
    "assign_team": action_assign_team,
    "assign_user": action_assign_user,
    "unassign": lambda ticket: action_unassign(ticket),
    "add_tags": action_add_tags,
    "remove_tags": action_remove_tags,
    "add_watcher": action_add_watcher,
    "set_visibility": action_set_visibility,
    "notify": action_notify,
    "create_subtask": action_create_subtask,
}