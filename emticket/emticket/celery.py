import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "emticket.settings")



app = Celery("emticket")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "sla-scan-every-minute": {
        "task": "sla.tasks.sla_scan_and_escalate",
        "schedule": 60.0,
    },
}
