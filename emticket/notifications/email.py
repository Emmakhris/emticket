import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_ticket_notification(notification, template_prefix: str) -> bool:
    """
    Render and send an email for a Notification object.
    template_prefix: e.g. "notifications/email/ticket_created"
    Checks user's email opt-out pref before sending.
    Returns True if the email was dispatched.
    """
    user = notification.user

    prefs = getattr(getattr(user, "profile", None), "notification_prefs", {}) or {}
    if not prefs.get("email", True):
        return False

    to_email = user.email
    if not to_email:
        return False

    ctx = {
        "notification": notification,
        "ticket": notification.ticket,
        "user": user,
    }

    try:
        subject_tpl = f"{template_prefix}_subject.txt"
        body_txt_tpl = f"{template_prefix}.txt"
        body_html_tpl = f"{template_prefix}.html"

        subject = render_to_string(subject_tpl, ctx).strip()
        body_txt = render_to_string(body_txt_tpl, ctx)
        body_html = render_to_string(body_html_tpl, ctx)
    except Exception as exc:
        logger.warning("Email template rendering failed for %s: %s", template_prefix, exc)
        return False

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@hospitaldesk.local")

    msg = EmailMultiAlternatives(subject=subject, body=body_txt, from_email=from_email, to=[to_email])
    msg.attach_alternative(body_html, "text/html")

    try:
        msg.send(fail_silently=False)
        notification.emailed_at = timezone.now()
        notification.save(update_fields=["emailed_at"])
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return False
