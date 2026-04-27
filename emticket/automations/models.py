from django.db import models
from organizations.models import Organization


class AutomationRule(models.Model):
    """
    conditions example:
      {"all":[{"field":"category","op":"eq","value":"Network"}]}
    actions example:
      [{"type":"assign_team","value":123},{"type":"set_priority","value":2}]
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="automation_rules")
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=100)  # lower runs first

    trigger = models.CharField(
        max_length=50,
        default="ticket_created",
        choices=[
            ("ticket_created", "Ticket Created"),
            ("ticket_updated", "Ticket Updated"),
            ("ticket_commented", "Ticket Commented"),
            ("sla_breached", "SLA Breached"),
        ],
    )

    conditions = models.JSONField(default=dict, blank=True)
    actions = models.JSONField(default=list, blank=True)

    # If False, the rule may fire more than once for the same ticket (e.g. sla_breached on each scan).
    # If True (default), the engine skips rules that already have an AutomationRun record for this ticket.
    run_once = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class AutomationRun(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="automation_runs")
    rule = models.ForeignKey(AutomationRule, on_delete=models.PROTECT, related_name="runs")

    object_type = models.CharField(max_length=120)  # "Ticket"
    object_id = models.CharField(max_length=120)    # ticket UUID as string

    ran_at = models.DateTimeField(auto_now_add=True)
    matched = models.BooleanField(default=False)
    actions_executed = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True)
