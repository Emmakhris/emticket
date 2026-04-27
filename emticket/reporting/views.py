from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from accounts.permissions import require_role
from .models import SavedView
from .services import get_dashboard_stats, get_volume_by_day, get_sla_compliance, get_agent_workload, get_category_breakdown


def _get_org(request):
    profile = getattr(request.user, "profile", None)
    return profile.organization if profile else None


@login_required
def dashboard(request):
    org = _get_org(request)
    stats = get_dashboard_stats(request.user, org)
    ctx = {"stats": stats}

    if request.headers.get("HX-Request") == "true":
        section = request.GET.get("section", "stats")
        if section == "my_queue":
            return render(request, "reporting/partials/my_queue_widget.html", ctx)
        if section == "breaching":
            return render(request, "reporting/partials/sla_breach_table.html", ctx)
        return render(request, "reporting/partials/stats_cards.html", ctx)

    return render(request, "reporting/dashboard.html", ctx)


@login_required
@require_role("admin", "supervisor")
def analytics(request):
    import json
    from django.core.serializers.json import DjangoJSONEncoder

    org = _get_org(request)
    days = int(request.GET.get("days", 30))

    volume_raw = get_volume_by_day(org, days)
    workload_raw = get_agent_workload(org)
    categories_raw = get_category_breakdown(org, days)
    sla = get_sla_compliance(org, days)

    volume_json = json.dumps(
        [{"day": str(r["day"])[:10], "count": r["count"]} for r in volume_raw],
        cls=DjangoJSONEncoder,
    )
    workload_json = json.dumps(
        [{"email": r["assignee__email"] or "Unassigned", "count": r["count"]} for r in workload_raw],
        cls=DjangoJSONEncoder,
    )
    categories_json = json.dumps(
        [{"name": r["category__name"] or "—", "count": r["count"]} for r in categories_raw],
        cls=DjangoJSONEncoder,
    )

    ctx = {
        "days": days,
        "volume_json": volume_json,
        "workload_json": workload_json,
        "categories_json": categories_json,
        "sla": sla,
    }
    return render(request, "reporting/analytics.html", ctx)


@login_required
@require_POST
def saved_view_create(request):
    org = _get_org(request)
    name = request.POST.get("name", "").strip()
    filter_json = {}
    for key in ("q", "status", "my", "priority"):
        val = request.POST.get(key, "")
        if val:
            filter_json[key] = val

    if not name or not org:
        return JsonResponse({"error": "name required"}, status=400)

    obj, _ = SavedView.objects.update_or_create(
        organization=org, user=request.user, name=name,
        defaults={"filter_json": filter_json},
    )
    return render(request, "reporting/partials/saved_views.html", {
        "saved_views": SavedView.objects.filter(organization=org, user=request.user).order_by("name"),
    })


@login_required
@require_POST
def saved_view_delete(request, pk):
    org = _get_org(request)
    sv = get_object_or_404(SavedView, pk=pk, user=request.user, organization=org)
    sv.delete()
    return render(request, "reporting/partials/saved_views.html", {
        "saved_views": SavedView.objects.filter(organization=org, user=request.user).order_by("name"),
    })


@login_required
def saved_views_list(request):
    org = _get_org(request)
    saved_views = SavedView.objects.filter(organization=org, user=request.user).order_by("name")
    return render(request, "reporting/partials/saved_views.html", {"saved_views": saved_views})
