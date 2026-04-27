from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from tickets.models import CSAT, Ticket


@login_required
def my_tickets(request):
    qs = Ticket.objects.filter(requester=request.user).select_related(
        "department", "category"
    ).order_by("-updated_at")
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    return render(request, "portal/my_tickets.html", {
        "tickets": page_obj.object_list,
        "page_obj": page_obj,
    })


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related("department", "category", "assignee").prefetch_related(
            "comments__author"
        ),
        id=ticket_id,
        requester=request.user,
    )
    comments = [c for c in ticket.comments.all() if not c.is_internal]
    return render(request, "portal/ticket_detail.html", {
        "ticket": ticket,
        "comments": comments,
    })


@login_required
@require_POST
def submit_csat(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, requester=request.user)
    rating = request.POST.get("rating")
    if rating and rating.isdigit() and 1 <= int(rating) <= 5:
        CSAT.objects.get_or_create(
            ticket=ticket,
            defaults={"user": request.user, "rating": int(rating)},
        )
    return redirect("portal:ticket_detail", ticket_id=ticket_id)
