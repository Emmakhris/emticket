from __future__ import annotations

from django.db.models import Q

from .models import ArticleVisibility, KBArticle


def get_suggested_articles(ticket, limit: int = 5):
    """
    Return KB articles relevant to the given ticket based on category and title keywords.
    Only returns active articles visible to agents (internal + public).
    """
    qs = KBArticle.objects.filter(
        organization=ticket.organization,
        is_active=True,
    ).select_related("category", "department")

    q = Q()
    if ticket.category:
        q |= Q(department=ticket.department)
    words = [w for w in ticket.title.split() if len(w) > 3][:6]
    if words:
        title_q = Q()
        for w in words:
            title_q |= Q(title__icontains=w)
        q |= title_q

    if q:
        qs = qs.filter(q)
    else:
        qs = qs.none()

    return qs.order_by("-updated_at")[:limit]
