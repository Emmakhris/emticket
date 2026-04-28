from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.permissions import can_view_ticket as _user_can_view_ticket  # noqa: F401
from audit.services import log_event
from automations.services import run_ticket_automations
from notifications.models import Notification
from sla.services import mark_first_response
from .services import calculate_priority

from .forms import (
    TicketAttachmentForm,
    TicketCommentForm,
    TicketCreateForm,
    TicketStatusForm,
)
from .models import Ticket, TicketComment, TicketStatus

User = get_user_model()


def _sidebar_ctx(ticket, request):
    """Build the context dict needed to re-render the sidebar partial."""
    profile = getattr(request.user, "profile", None)
    assignee_options = User.objects.all().order_by("email")[:200]
    if profile and profile.organization_id:
        assignee_options = User.objects.filter(
            profile__organization_id=profile.organization_id
        ).order_by("email")[:200]
    return {
        "ticket": ticket,
        "status_choices": TicketStatus.choices,
        "assignee_options": assignee_options,
    }


@login_required
def ticket_list(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    my = (request.GET.get("my") or "").strip()

    qs = Ticket.objects.select_related(
        "department", "team", "category", "site", "assignee", "requester", "sla"
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

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page_obj": page_obj,
        "tickets": page_obj.object_list,
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
            ticket.priority = calculate_priority(ticket.impact, ticket.urgency)
            ticket.save()
            ticket.watchers.add(request.user)

            log_event(
                organization=ticket.organization,
                actor=request.user,
                event_type="ticket.created",
                object_type="Ticket",
                object_id=ticket.id,
                after={"ticket_number": ticket.ticket_number, "title": ticket.title},
                request=request,
            )

            from notifications.tasks import send_notification_email
            notif = Notification.objects.create(
                organization=ticket.organization,
                user=ticket.requester,
                ticket=ticket,
                title=f"Ticket {ticket.ticket_number or ticket.id} opened",
                body=ticket.title,
            )
            send_notification_email.delay(notif.pk, "ticket.created")

            return redirect("tickets:detail", ticket_id=ticket.id)
    else:
        form = TicketCreateForm()

    return render(request, "tickets/create.html", {"form": form})


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "department", "team", "category", "site", "assignee", "requester", "related_asset", "sla"
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

    log_event(
        organization=ticket.organization,
        actor=request.user,
        event_type="ticket.commented",
        object_type="Ticket",
        object_id=ticket.id,
        after={"is_internal": c.is_internal},
        request=request,
    )

    run_ticket_automations(
        ticket=ticket,
        trigger="ticket_commented",
        actor=request.user,
        extra={"comment_is_internal": c.is_internal},
    )

    if not c.is_internal and request.user != ticket.requester and not ticket.first_response_at:
        mark_first_response(ticket)

    if not c.is_internal:
        from notifications.tasks import send_notification_email
        notify_user = ticket.requester if request.user != ticket.requester else ticket.assignee
        if notify_user:
            notif = Notification.objects.create(
                organization=ticket.organization,
                user=notify_user,
                ticket=ticket,
                title=f"New comment on {ticket.ticket_number or ticket.id}",
                body=c.body[:500],
            )
            send_notification_email.delay(notif.pk, "ticket.commented")

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

    old_status = ticket.status
    new_status = form.cleaned_data["status"]
    ticket.status = new_status

    if new_status == TicketStatus.RESOLVED and not ticket.resolved_at:
        ticket.resolved_at = timezone.now()
    if new_status == TicketStatus.CLOSED and not ticket.closed_at:
        ticket.closed_at = timezone.now()

    ticket.save(update_fields=["status", "resolved_at", "closed_at", "updated_at"])

    log_event(
        organization=ticket.organization,
        actor=request.user,
        event_type="ticket.status_changed",
        object_type="Ticket",
        object_id=ticket.id,
        before={"status": old_status},
        after={"status": new_status},
        request=request,
    )

    return render(request, "tickets/partials/sidebar.html", _sidebar_ctx(ticket, request))


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

    log_event(
        organization=ticket.organization,
        actor=request.user,
        event_type="ticket.assigned",
        object_type="Ticket",
        object_id=ticket.id,
        after={"assignee": assignee.email},
        request=request,
    )

    from notifications.tasks import send_notification_email
    notif = Notification.objects.create(
        organization=ticket.organization,
        user=assignee,
        ticket=ticket,
        title=f"Ticket assigned to you: {ticket.ticket_number or ticket.id}",
        body=ticket.title,
    )
    send_notification_email.delay(notif.pk, "ticket.assigned")

    return render(request, "tickets/partials/sidebar.html", _sidebar_ctx(ticket, request))


@login_required
def ticket_unassign(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if not _user_can_view_ticket(request.user, ticket):
        return HttpResponseForbidden("No access")

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    old_assignee = ticket.assignee.email if ticket.assignee else None
    ticket.assignee = None
    ticket.save(update_fields=["assignee", "updated_at"])

    log_event(
        organization=ticket.organization,
        actor=request.user,
        event_type="ticket.unassigned",
        object_type="Ticket",
        object_id=ticket.id,
        before={"assignee": old_assignee},
        after={"assignee": None},
        request=request,
    )

    return render(request, "tickets/partials/sidebar.html", _sidebar_ctx(ticket, request))


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

    log_event(
        organization=ticket.organization,
        actor=request.user,
        event_type="ticket.attachment_added",
        object_type="Ticket",
        object_id=ticket.id,
        after={"filename": att.filename, "size_bytes": att.size_bytes},
        request=request,
    )

    ticket = Ticket.objects.prefetch_related("attachments").get(id=ticket_id)
    return render(request, "tickets/partials/attachments.html", {"ticket": ticket})


@login_required
def canned_response_picker(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    from .models import CannedResponse
    profile = getattr(request.user, "profile", None)
    org = profile.organization if profile else None
    responses = CannedResponse.objects.filter(organization=org, is_active=True).order_by("name")
    return render(request, "tickets/partials/canned_response_picker.html", {
        "responses": responses, "ticket": ticket,
    })


@login_required
def ticket_bulk_action(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    from accounts.permissions import require_role as _require_role
    role = getattr(getattr(request.user, "profile", None), "role", "")
    if role not in ("admin", "supervisor", "team_lead", "agent"):
        return HttpResponseForbidden("Not allowed")

    ids_raw = request.POST.get("ids", "")
    action = request.POST.get("action", "")
    value = request.POST.get("value", "")

    ticket_ids = [i.strip() for i in ids_raw.split(",") if i.strip()]
    if not ticket_ids or not action:
        return HttpResponseBadRequest("ids and action required")

    profile = getattr(request.user, "profile", None)
    org = profile.organization if profile else None
    tickets_qs = Ticket.objects.filter(id__in=ticket_ids, organization=org)

    from automations.actions import action_set_status, action_set_priority
    from audit.services import log_event as _log

    changed = 0
    for ticket in tickets_qs:
        if action == "set_status":
            result = action_set_status(ticket, value)
        elif action == "set_priority":
            result = action_set_priority(ticket, int(value))
        else:
            continue
        if result.changed:
            changed += 1
            _log(
                organization=ticket.organization,
                actor=request.user,
                event_type=f"ticket.bulk_{action}",
                object_type="Ticket",
                object_id=ticket.id,
                after={"action": action, "value": value},
                request=request,
            )

    from django.contrib import messages
    messages.success(request, f"Updated {changed} ticket(s).")
    return redirect(request.META.get("HTTP_REFERER", "tickets:list"))


@login_required
def ticket_export_csv(request):
    import csv
    from django.http import StreamingHttpResponse

    role = getattr(getattr(request.user, "profile", None), "role", "")
    if role not in ("admin", "supervisor", "team_lead", "agent"):
        return HttpResponseForbidden("Not allowed")

    profile = getattr(request.user, "profile", None)
    org = profile.organization if profile else None

    qs = Ticket.objects.select_related(
        "department", "category", "assignee", "requester", "sla"
    ).filter(organization=org).order_by("-created_at")[:5000]

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    if q:
        qs = qs.filter(Q(ticket_number__icontains=q) | Q(title__icontains=q))
    if status:
        qs = qs.filter(status=status)

    def rows():
        yield ["ticket_number", "title", "status", "priority", "department",
               "category", "assignee", "requester", "created_at", "resolved_at",
               "sla_due", "sla_breached"]
        for t in qs:
            sla = getattr(t, "sla", None)
            yield [
                t.ticket_number or str(t.id),
                t.title,
                t.status,
                t.get_priority_display(),
                t.department.name,
                t.category.name if t.category else "",
                t.assignee.email if t.assignee else "",
                t.requester.email if t.requester else "",
                t.created_at.isoformat() if t.created_at else "",
                t.resolved_at.isoformat() if t.resolved_at else "",
                (sla.resolution_due_at.isoformat() if sla and sla.resolution_due_at else ""),
                (str(sla.breached_resolution) if sla else ""),
            ]

    class EchoWriter:
        def write(self, value):
            return value

    pseudo_buffer = EchoWriter()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse(
        (writer.writerow(row) for row in rows()),
        content_type="text/csv",
    )
    response["Content-Disposition"] = 'attachment; filename="tickets.csv"'
    return response
