from __future__ import annotations

from functools import wraps

from django.http import HttpResponseForbidden


# Roles that can see all tickets and manage the system
STAFF_ROLES = {"agent", "team_lead", "supervisor", "admin"}
MANAGE_ROLES = {"team_lead", "supervisor", "admin"}
ADMIN_ROLES = {"supervisor", "admin"}


def get_user_role(user) -> str | None:
    profile = getattr(user, "profile", None)
    if profile:
        return profile.role
    return None


def can_view_ticket(user, ticket) -> bool:
    if not user.is_authenticated:
        return False

    role = get_user_role(user)
    if role in ADMIN_ROLES:
        return True

    if ticket.requester_id == user.id:
        return True
    if ticket.assignee_id == user.id:
        return True
    if ticket.watchers.filter(id=user.id).exists():
        return True

    profile = getattr(user, "profile", None)
    if profile:
        if role == "team_lead" and ticket.team_id and ticket.team_id == profile.team_id:
            return True
        if profile.team_id and ticket.team_id == profile.team_id:
            return True
        if profile.department_id and ticket.visibility != "confidential":
            return ticket.department_id == profile.department_id

    return False


def require_role(*roles):
    """
    View decorator that restricts access to users whose profile.role is in `roles`.
    Usage:  @require_role("admin", "supervisor")
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role not in roles:
                return HttpResponseForbidden("You do not have permission to perform this action.")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
