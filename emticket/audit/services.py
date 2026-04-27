from __future__ import annotations

from typing import Any, Dict, Optional

from .models import AuditEvent


def log_event(
    *,
    organization,
    actor=None,
    event_type: str,
    object_type: str,
    object_id: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request=None,
) -> AuditEvent:
    ip = None
    if request is not None:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            ip = x_forwarded.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

    return AuditEvent.objects.create(
        organization=organization,
        actor=actor,
        event_type=event_type,
        object_type=object_type,
        object_id=str(object_id),
        before=before or {},
        after=after or {},
        metadata=metadata or {},
        ip_address=ip,
    )
