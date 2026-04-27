import logging

from emticket.celery import app

logger = logging.getLogger(__name__)

_TEMPLATE_MAP = {
    "ticket.created": "notifications/email/ticket_created",
    "ticket.commented": "notifications/email/ticket_commented",
    "ticket.assigned": "notifications/email/ticket_assigned",
    "sla.first_response_breached": "notifications/email/sla_breached",
    "sla.resolution_breached": "notifications/email/sla_breached",
}


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email(self, notification_id: int, event_type: str = ""):
    from .models import Notification
    from .email import send_ticket_notification

    try:
        notification = Notification.objects.select_related("user", "ticket").get(pk=notification_id)
    except Notification.DoesNotExist:
        return

    if notification.emailed_at:
        return

    template_prefix = _TEMPLATE_MAP.get(event_type, "notifications/email/generic")
    try:
        send_ticket_notification(notification, template_prefix)
    except Exception as exc:
        logger.exception("send_notification_email failed for notification %s", notification_id)
        raise self.retry(exc=exc)
