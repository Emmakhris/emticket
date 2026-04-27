from django import template
from django.utils import timezone

register = template.Library()


@register.inclusion_tag("tickets/partials/sla_pill.html")
def sla_pill(ticket):
    """
    Renders a colored SLA status pill for use in ticket list and detail.
    Returns context: {color, label, minutes_remaining}
    Phase 3 wires this fully; stub renders safely with no SLA data.
    """
    sla = getattr(ticket, "sla", None)
    if not sla or not sla.resolution_due_at:
        return {"color": "grey", "label": "—", "minutes_remaining": None}

    if sla.breached_resolution:
        return {"color": "red", "label": "Breached", "minutes_remaining": 0}

    now = timezone.now()
    delta = sla.resolution_due_at - now
    minutes_remaining = int(delta.total_seconds() / 60)

    if minutes_remaining <= 120:
        label = f"Due in {minutes_remaining}m" if minutes_remaining > 0 else "Overdue"
        return {"color": "amber", "label": label, "minutes_remaining": minutes_remaining}

    hours = minutes_remaining // 60
    return {"color": "green", "label": f"{hours}h left", "minutes_remaining": minutes_remaining}


@register.filter
def priority_label(value):
    labels = {1: "P1 - Critical", 2: "P2 - High", 3: "P3 - Medium", 4: "P4 - Low"}
    return labels.get(value, str(value))


@register.filter
def priority_color(value):
    colors = {1: "red", 2: "orange", 3: "blue", 4: "slate"}
    return colors.get(value, "slate")
