from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from sla.services import mark_first_response
from automations.services import run_ticket_automations


from .forms import (
    TicketCreateForm,
    TicketCommentForm,
    TicketStatusForm,
    TicketAttachmentForm,
)
from .models import Ticket, TicketComment, TicketStatus
from organizations.models import Team
from django.contrib.auth import get_user_model

User = get_user_model()


def _user_can_view_ticket(user, ticket: Ticket) -> bool:
    """
    Minimal access rules (expand later):
    - requester OR assignee OR watcher
    - OR user role is admin/team lead/supervisor (not implemented here)
    - OR user in same team (via profile.team)
    - confidential tickets: only requester/assignee/same team/admin
    """
    if not user.is_authenticated:
        return False

    if ticket.requester_id == user.id:
        return True
    if ticket.assignee_id == user.id:
        return True
    if ticket.watchers.filter(id=user.id).exists():
        return True

    profile = getattr(user, "profile", None)
    if profile and profile.team_id and ticket.team_id == profile.team_id:
        return True

    # fallback: allow same department (non-confidential)
    if profile and profile.department_id and not (ticket.visibility == "confidential"):
        return ticket.department_id == profile.department_id

    return False


@login_required
def ticket_list(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    my = (request.GET.get("my") or "").strip()

    qs = Ticket.objects.select_related(
        "department", "team", "category", "site", "assignee", "requester"
    ).order_by("-updated_at")

    # Basic scoping: show "my" tickets by default if requester role, otherwise show broader.
    # You can refine later using RBAC.
    if my == "1":
        qs = qs.filter(Q(requester=request.user) | Q(assignee=request.user) | Q(watchers=request.user))

    if q:
        qs = qs.filter(
            Q(ticket_number__icontains=q)
            | Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(tags__contains=[q])  # works if tags are stored as list
        )

    if status:
        qs = qs.filter(status=status)

    # Render partial table if HTMX
    context = {
        "tickets": qs[:200],  # keep simple; add pagination later
        "status_choices": TicketStatus.choices,
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, "tickets/partials/table.html", context)

    return render(request, "tickets/list.html", context)


@login_required
def ticket_create(request):
    if request.method == "POST":
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            # set org from user profile if available
            profile = getattr(request.user, "profile", None)
            if profile and profile.organization_id:
                ticket.organization_id = profile.organization_id
            else:
                return HttpResponseBadRequest("User has no organization profile.")

            ticket.requester = request.user

            # minimal auto: if team not set, infer from category.department teams later
            ticket.save()
            ticket.watchers.add(request.user)

            return redirect("tickets:detail", ticket_id=ticket.id)
    else:
        form = TicketCreateForm()

    return render(request, "tickets/create.html", {"form": form})


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "department", "team", "category", "site", "assignee", "requester", "related_asset"
        ).prefetch_related("comments__author", "attachments", "watchers"),
        id=ticket_id,
    )

    if not _user_can_view_ticket(request.user, ticket):
        return HttpResponseForbidden("You do not have access to this ticket.")

    comment_form = TicketCommentForm()
    status_form = TicketStatusForm(initial={"status": ticket.status})

    # Assignment dropdown: show users in same org (simple)
    profile = getattr(request.user, "profile", None)
    assignee_options = User.objects.all().order_by("email")[:200]
    if profile and profile.organization_id:
        # If you store org in profile only, you can filter by profile.organization
        assignee_options = User.objects.filter(profile__organization_id=profile.organization_id).order_by("email")[:200]

    context = {
        "ticket": ticket,
        "comment_form": comment_form,
        "status_form": status_form,
        "assignee_options": assignee_options,
        "status_choices": TicketStatus.choices,
    }
    return render(request, "tickets/detail.html", context)


@login_required
def ticket_add_comment(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if not _user_can_view_ticket(request.user, ticket):
        return HttpResponseForbidden("No access")

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    form = TicketCommentForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "tickets/partials/comment_form.html",
            {"ticket": ticket, "comment_form": form},
            status=400,
        )

    c: TicketComment = form.save(commit=False)
    c.ticket = ticket
    c.author = request.user
    c.save()


    # extra info helps rules like: if comment_is_internal == false then notify requester
    run_ticket_automations(
        ticket=ticket,
        trigger="ticket_commented",
        actor=request.user,
        extra={"comment_is_internal": c.is_internal}
    )
    {"all":[{"field":"status","op":"eq","value":"waiting_requester"}]}


    
    # ...
    if not c.is_internal and request.user != ticket.requester and not ticket.first_response_at:
        mark_first_response(ticket)




    # mark first response if agent replied publicly
    if not c.is_internal and not ticket.first_response_at and request.user != ticket.requester:
        ticket.first_response_at = timezone.now()
        ticket.status = TicketStatus.OPEN if ticket.status == TicketStatus.NEW else ticket.status
        ticket.save(update_fields=["first_response_at", "status", "updated_at"])

    # return updated thread partial
    ticket = Ticket.objects.prefetch_related("comments__author").get(id=ticket_id)
    return render(request, "tickets/partials/thread.html", {"ticket": ticket})


@login_required
def ticket_set_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if not _user_can_view_ticket(request.user, ticket):
        return HttpResponseForbidden("No access")

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    form = TicketStatusForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Invalid status")

    new_status = form.cleaned_data["status"]
    ticket.status = new_status

    if new_status == TicketStatus.RESOLVED and not ticket.resolved_at:
        ticket.resolved_at = timezone.now()
    if new_status == TicketStatus.CLOSED and not ticket.closed_at:
        ticket.closed_at = timezone.now()

    ticket.save(update_fields=["status", "resolved_at", "closed_at", "updated_at"])
    return render(request, "tickets/partials/sidebar.html", {"ticket": ticket, "status_choices": TicketStatus.choices})


@login_required
def ticket_assign(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if not _user_can_view_ticket(request.user, ticket):
        return HttpResponseForbidden("No access")

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    assignee_id = request.POST.get("assignee_id")
    if not assignee_id:
        return HttpResponseBadRequest("assignee_id required")

    try:
        assignee = User.objects.get(id=int(assignee_id))
    except (ValueError, User.DoesNotExist):
        return HttpResponseBadRequest("Invalid assignee")

    ticket.assignee = assignee
    if ticket.status == TicketStatus.NEW:
        ticket.status = TicketStatus.OPEN
    ticket.save(update_fields=["assignee", "status", "updated_at"])

    return render(request, "tickets/partials/sidebar.html", {"ticket": ticket, "status_choices": TicketStatus.choices})


@login_required
def ticket_unassign(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if not _user_can_view_ticket(request.user, ticket):
        return HttpResponseForbidden("No access")

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    ticket.assignee = None
    ticket.save(update_fields=["assignee", "updated_at"])
    return render(request, "tickets/partials/sidebar.html", {"ticket": ticket, "status_choices": TicketStatus.choices})


@login_required
def ticket_add_attachment(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if not _user_can_view_ticket(request.user, ticket):
        return HttpResponseForbidden("No access")

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    form = TicketAttachmentForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest("Invalid file")

    att = form.save(commit=False)
    att.ticket = ticket
    att.uploaded_by = request.user
    att.filename = getattr(att.file, "name", "")[:255]
    att.content_type = getattr(att.file.file, "content_type", "")[:120] if hasattr(att.file, "file") else ""
    try:
        att.size_bytes = att.file.size
    except Exception:
        att.size_bytes = 0
    att.save()

    ticket = Ticket.objects.prefetch_related("attachments").get(id=ticket_id)
    return render(request, "tickets/partials/attachments.html", {"ticket": ticket})
