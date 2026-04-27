import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import require_role
from tickets.models import Ticket
from .conditions import EvalContext
from .engine import AutomationEngine
from .forms import AutomationRuleForm
from .models import AutomationRule, AutomationRun


def _get_org(request):
    profile = getattr(request.user, "profile", None)
    return profile.organization if profile else None


@login_required
@require_role("admin", "supervisor")
def rule_list(request):
    org = _get_org(request)
    rules = AutomationRule.objects.filter(organization=org).order_by("priority", "name")
    return render(request, "automations/rule_list.html", {"rules": rules})


@login_required
@require_role("admin", "supervisor")
def rule_create(request):
    org = _get_org(request)
    if request.method == "POST":
        form = AutomationRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.organization = org
            rule.save()
            return redirect("automations:rule_detail", rule_id=rule.pk)
    else:
        form = AutomationRuleForm()
    return render(request, "automations/rule_form.html", {"form": form, "title": "New Rule"})


@login_required
@require_role("admin", "supervisor")
def rule_detail(request, rule_id):
    org = _get_org(request)
    rule = get_object_or_404(AutomationRule, pk=rule_id, organization=org)
    recent_runs = AutomationRun.objects.filter(rule=rule).order_by("-ran_at")[:20]
    form = AutomationRuleForm(instance=rule)
    return render(request, "automations/rule_detail.html", {
        "rule": rule, "form": form, "recent_runs": recent_runs
    })


@login_required
@require_role("admin", "supervisor")
def rule_edit(request, rule_id):
    org = _get_org(request)
    rule = get_object_or_404(AutomationRule, pk=rule_id, organization=org)
    if request.method == "POST":
        form = AutomationRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            return redirect("automations:rule_detail", rule_id=rule.pk)
    else:
        form = AutomationRuleForm(instance=rule)
    return render(request, "automations/rule_form.html", {"form": form, "title": f"Edit: {rule.name}", "rule": rule})


@login_required
@require_role("admin", "supervisor")
def rule_toggle(request, rule_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    org = _get_org(request)
    rule = get_object_or_404(AutomationRule, pk=rule_id, organization=org)
    rule.enabled = not rule.enabled
    rule.save(update_fields=["enabled", "updated_at"])
    return render(request, "automations/partials/rule_row.html", {"rule": rule})


@login_required
@require_role("admin", "supervisor")
def rule_test(request, rule_id):
    """Dry-run a rule against a selected ticket and return results as JSON."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    org = _get_org(request)
    rule = get_object_or_404(AutomationRule, pk=rule_id, organization=org)
    ticket_id = request.POST.get("ticket_id", "").strip()
    if not ticket_id:
        return JsonResponse({"error": "ticket_id required"}, status=400)
    try:
        ticket = Ticket.objects.get(pk=ticket_id, organization=org)
    except (Ticket.DoesNotExist, Exception):
        return JsonResponse({"error": "Ticket not found"}, status=404)

    ctx = EvalContext(obj=ticket, actor=request.user, trigger=rule.trigger, changes={}, extra={})
    engine = AutomationEngine(organization_id=org.pk, trigger=rule.trigger, dry_run=True)
    results = engine.run(ctx)
    return JsonResponse({"results": [
        {"rule_id": r.rule_id, "matched": r.matched, "actions": r.actions_executed, "error": r.error}
        for r in results
    ]})
