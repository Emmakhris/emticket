from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import require_role
from tickets.models import Ticket
from .forms import AssetForm, AssetLocationForm, AssetTypeForm
from .models import Asset, AssetLocation, AssetType


def _get_org(request):
    profile = getattr(request.user, "profile", None)
    return profile.organization if profile else None


@login_required
def asset_list(request):
    org = _get_org(request)
    qs = Asset.objects.select_related("asset_type", "site", "location").filter(organization=org).order_by("asset_id")

    q = (request.GET.get("q") or "").strip()
    asset_type_id = request.GET.get("asset_type", "")
    in_service = request.GET.get("in_service", "")

    if q:
        qs = qs.filter(Q(asset_id__icontains=q) | Q(vendor__icontains=q) | Q(model__icontains=q) | Q(serial_number__icontains=q))
    if asset_type_id:
        qs = qs.filter(asset_type_id=asset_type_id)
    if in_service == "1":
        qs = qs.filter(in_service=True)
    elif in_service == "0":
        qs = qs.filter(in_service=False)

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    asset_types = AssetType.objects.filter(organization=org)

    context = {"page_obj": page_obj, "assets": page_obj.object_list, "asset_types": asset_types}

    if request.headers.get("HX-Request") == "true":
        return render(request, "assets/partials/asset_table.html", context)

    return render(request, "assets/asset_list.html", context)


@login_required
def asset_detail(request, asset_id):
    org = _get_org(request)
    asset = get_object_or_404(Asset, pk=asset_id, organization=org)
    linked_tickets = Ticket.objects.filter(related_asset=asset).select_related("department", "assignee").order_by("-created_at")[:20]
    return render(request, "assets/asset_detail.html", {"asset": asset, "linked_tickets": linked_tickets})


@login_required
@require_role("admin", "supervisor", "team_lead")
def asset_create(request):
    org = _get_org(request)
    if request.method == "POST":
        form = AssetForm(request.POST, organization=org)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.organization = org
            asset.save()
            return redirect("assets:asset_detail", asset_id=asset.pk)
    else:
        form = AssetForm(organization=org)
    return render(request, "assets/asset_form.html", {"form": form, "title": "New Asset"})


@login_required
@require_role("admin", "supervisor", "team_lead")
def asset_edit(request, asset_id):
    org = _get_org(request)
    asset = get_object_or_404(Asset, pk=asset_id, organization=org)
    if request.method == "POST":
        form = AssetForm(request.POST, instance=asset, organization=org)
        if form.is_valid():
            form.save()
            return redirect("assets:asset_detail", asset_id=asset.pk)
    else:
        form = AssetForm(instance=asset, organization=org)
    return render(request, "assets/asset_form.html", {"form": form, "title": f"Edit {asset.asset_id}", "asset": asset})
