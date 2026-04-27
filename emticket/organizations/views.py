from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import require_role
from .forms import DepartmentForm, OrganizationForm, SiteForm, TeamForm, WorkingCalendarForm
from .models import Department, Organization, Site, Team, WorkingCalendar


@login_required
@require_role("admin", "supervisor")
def org_list(request):
    profile = getattr(request.user, "profile", None)
    orgs = Organization.objects.prefetch_related("sites", "departments").order_by("name")
    if profile and not request.user.is_superuser:
        orgs = orgs.filter(id=profile.organization_id)
    return render(request, "organizations/org_list.html", {"orgs": orgs})


@login_required
@require_role("admin")
def org_create(request):
    if request.method == "POST":
        form = OrganizationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("organizations:org_list")
    else:
        form = OrganizationForm()
    return render(request, "organizations/org_form.html", {"form": form, "title": "New Organization"})


@login_required
@require_role("admin")
def org_edit(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    if request.method == "POST":
        form = OrganizationForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            return redirect("organizations:org_list")
    else:
        form = OrganizationForm(instance=org)
    return render(request, "organizations/org_form.html", {"form": form, "title": f"Edit {org.name}", "org": org})


# --- Sites ---

@login_required
@require_role("admin", "supervisor")
def site_list(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    sites = org.sites.all().order_by("name")
    return render(request, "organizations/partials/site_list.html", {"org": org, "sites": sites})


@login_required
@require_role("admin")
def site_create(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    if request.method == "POST":
        form = SiteForm(request.POST)
        if form.is_valid():
            site = form.save(commit=False)
            site.organization = org
            site.save()
            return redirect("organizations:site_list", org_id=org.pk)
    else:
        form = SiteForm()
    return render(request, "organizations/partials/site_form.html", {"form": form, "org": org})


@login_required
@require_role("admin")
def site_edit(request, org_id, site_id):
    org = get_object_or_404(Organization, pk=org_id)
    site = get_object_or_404(Site, pk=site_id, organization=org)
    if request.method == "POST":
        form = SiteForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            return redirect("organizations:site_list", org_id=org.pk)
    else:
        form = SiteForm(instance=site)
    return render(request, "organizations/partials/site_form.html", {"form": form, "org": org, "site": site})


# --- Departments ---

@login_required
@require_role("admin", "supervisor")
def department_list(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    departments = org.departments.prefetch_related("teams").order_by("name")
    return render(request, "organizations/partials/department_list.html", {"org": org, "departments": departments})


@login_required
@require_role("admin")
def department_create(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save(commit=False)
            dept.organization = org
            dept.save()
            return redirect("organizations:department_list", org_id=org.pk)
    else:
        form = DepartmentForm()
    return render(request, "organizations/partials/department_form.html", {"form": form, "org": org})


@login_required
@require_role("admin")
def department_edit(request, org_id, dept_id):
    org = get_object_or_404(Organization, pk=org_id)
    dept = get_object_or_404(Department, pk=dept_id, organization=org)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            return redirect("organizations:department_list", org_id=org.pk)
    else:
        form = DepartmentForm(instance=dept)
    return render(request, "organizations/partials/department_form.html", {"form": form, "org": org, "dept": dept})


# --- Teams ---

@login_required
@require_role("admin", "supervisor", "team_lead")
def team_list(request, org_id, dept_id):
    org = get_object_or_404(Organization, pk=org_id)
    dept = get_object_or_404(Department, pk=dept_id, organization=org)
    teams = dept.teams.order_by("name")
    return render(request, "organizations/partials/team_list.html", {"org": org, "dept": dept, "teams": teams})


@login_required
@require_role("admin")
def team_create(request, org_id, dept_id):
    org = get_object_or_404(Organization, pk=org_id)
    dept = get_object_or_404(Department, pk=dept_id, organization=org)
    if request.method == "POST":
        form = TeamForm(request.POST, organization=org)
        if form.is_valid():
            team = form.save(commit=False)
            team.organization = org
            team.save()
            return redirect("organizations:team_list", org_id=org.pk, dept_id=dept.pk)
    else:
        form = TeamForm(organization=org, initial={"department": dept})
    return render(request, "organizations/partials/team_form.html", {"form": form, "org": org, "dept": dept})


# --- Working Calendar ---

@login_required
@require_role("admin", "supervisor")
def calendar_edit(request, org_id, site_id):
    org = get_object_or_404(Organization, pk=org_id)
    site = get_object_or_404(Site, pk=site_id, organization=org)
    calendar, _ = WorkingCalendar.objects.get_or_create(
        site=site,
        defaults={
            "timezone": "Africa/Accra",
            "weekly_hours": {
                "mon": [["08:00", "17:00"]], "tue": [["08:00", "17:00"]],
                "wed": [["08:00", "17:00"]], "thu": [["08:00", "17:00"]],
                "fri": [["08:00", "17:00"]], "sat": [], "sun": [],
            },
            "holidays": [],
        }
    )
    if request.method == "POST":
        form = WorkingCalendarForm(request.POST, instance=calendar)
        if form.is_valid():
            form.save()
            return redirect("organizations:org_list")
    else:
        form = WorkingCalendarForm(instance=calendar)
    return render(request, "organizations/calendar_edit.html", {
        "form": form, "org": org, "site": site, "calendar": calendar
    })
