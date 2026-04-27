from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import get_dashboard_stats


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
