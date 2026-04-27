from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Notification


def _user_notifs(user):
    return Notification.objects.filter(user=user).select_related("ticket").order_by("-created_at")


@login_required
def notification_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    if request.headers.get("HX-Request") == "true":
        return render(request, "notifications/partials/bell_count.html", {"count": count})
    return JsonResponse({"count": count})


@login_required
def notification_list(request):
    notifications = _user_notifs(request.user)[:30]
    return render(request, "notifications/partials/bell_dropdown.html", {
        "notifications": notifications,
    })


@login_required
@require_POST
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    return notification_count(request)


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get("HX-Request") == "true":
        return render(request, "notifications/partials/bell_dropdown.html", {"notifications": []})
    return JsonResponse({"ok": True})
