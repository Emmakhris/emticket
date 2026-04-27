from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from accounts.permissions import require_role
from organizations.models import Department
from tickets.models import Priority

from .forms import SLAPolicyForm
from .models import SLAPolicy


def _get_org(request):
    profile = getattr(request.user, "profile", None)
    return profile.organization if profile else None


@login_required
@require_role("admin", "supervisor")
def policy_list(request):
    org = _get_org(request)
    departments = Department.objects.filter(organization=org).order_by("name")
    priority_choices = Priority.choices

    existing = {
        (p.department_id, p.priority): p
        for p in SLAPolicy.objects.filter(
            organization=org, site=None, category=None
        ).select_related("department")
    }

    matrix = [
        {
            "dept": dept,
            "cells": [
                {
                    "priority": pval,
                    "priority_label": plabel,
                    "policy": existing.get((dept.pk, pval)),
                }
                for pval, plabel in priority_choices
            ],
        }
        for dept in departments
    ]

    return render(request, "sla/policy_list.html", {
        "matrix": matrix,
        "priority_choices": priority_choices,
    })


@login_required
@require_role("admin", "supervisor")
def policy_create(request):
    org = _get_org(request)
    department_id = request.GET.get("department") or request.POST.get("department")
    priority_val = request.GET.get("priority") or request.POST.get("priority")

    if request.method == "POST":
        form = SLAPolicyForm(request.POST, organization=org)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.organization = org
            policy.save()
            return _cell_response(request, policy)
    else:
        initial = {}
        if department_id:
            initial["department"] = department_id
        if priority_val:
            initial["priority"] = priority_val
        form = SLAPolicyForm(initial=initial, organization=org)

    qs = "?" + request.GET.urlencode() if request.GET else ""
    cancel_url = (
        reverse("sla:policy_cell") + f"?department={department_id}&priority={priority_val}"
        if department_id and priority_val else ""
    )
    return render(request, "sla/partials/policy_form.html", {
        "form": form,
        "action_url": request.path + qs,
        "cell_id": f"cell-{department_id}-{priority_val}",
        "cancel_url": cancel_url,
    })


@login_required
@require_role("admin", "supervisor")
def policy_edit(request, pk):
    org = _get_org(request)
    policy = get_object_or_404(SLAPolicy, pk=pk, organization=org)

    if request.method == "POST":
        form = SLAPolicyForm(request.POST, instance=policy, organization=org)
        if form.is_valid():
            form.save()
            return _cell_response(request, policy)
    else:
        form = SLAPolicyForm(instance=policy, organization=org)

    cell_id = f"cell-{policy.department_id}-{policy.priority}"
    cancel_url = (
        reverse("sla:policy_cell")
        + f"?department={policy.department_id}&priority={policy.priority}"
    )
    return render(request, "sla/partials/policy_form.html", {
        "form": form,
        "action_url": request.path,
        "policy": policy,
        "cell_id": cell_id,
        "cancel_url": cancel_url,
    })


@login_required
@require_role("admin", "supervisor")
def policy_cell(request):
    org = _get_org(request)
    dept_id = request.GET.get("department")
    priority_val = request.GET.get("priority")
    dept = get_object_or_404(Department, pk=dept_id, organization=org)
    pval = int(priority_val)
    policy = SLAPolicy.objects.filter(
        organization=org, department=dept, priority=pval, site=None, category=None
    ).first()
    priority_label = dict(Priority.choices).get(pval, "")
    return render(request, "sla/partials/policy_cell.html", {
        "dept": dept,
        "cell": {"priority": pval, "priority_label": priority_label, "policy": policy},
    })


def _cell_response(request, policy):
    priority_label = dict(Priority.choices).get(policy.priority, "")
    return render(request, "sla/partials/policy_cell.html", {
        "dept": policy.department,
        "cell": {
            "priority": policy.priority,
            "priority_label": priority_label,
            "policy": policy,
        },
    })
