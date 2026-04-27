import bleach
import markdown as md
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import require_role

from .forms import KBArticleForm, KBFeedbackForm
from .models import ArticleVisibility, KBArticle, KBArticleFeedback

_ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr", "blockquote",
    "pre", "code", "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
    "strong", "em", "del", "img",
]
_ALLOWED_ATTRS = {**bleach.sanitizer.ALLOWED_ATTRIBUTES, "img": ["src", "alt", "title"]}


def _get_org(request):
    profile = getattr(request.user, "profile", None)
    return profile.organization if profile else None


def _render_body(raw: str) -> str:
    html = md.markdown(raw, extensions=["tables", "fenced_code", "nl2br"])
    return bleach.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS)


@login_required
def article_list(request):
    org = _get_org(request)
    role = getattr(getattr(request.user, "profile", None), "role", "")
    is_agent = role in ("admin", "supervisor", "team_lead", "agent")

    qs = KBArticle.objects.filter(organization=org, is_active=True).select_related(
        "category", "department"
    )
    if not is_agent:
        qs = qs.filter(visibility=ArticleVisibility.PUBLIC)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))

    paginator = Paginator(qs.order_by("-updated_at"), 30)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    ctx = {"page_obj": page_obj, "articles": page_obj.object_list, "q": q, "is_agent": is_agent}

    if request.headers.get("HX-Request") == "true":
        return render(request, "knowledgebase/partials/article_table.html", ctx)

    return render(request, "knowledgebase/article_list.html", ctx)


@login_required
def article_detail(request, pk):
    org = _get_org(request)
    article = get_object_or_404(KBArticle, pk=pk, organization=org, is_active=True)

    role = getattr(getattr(request.user, "profile", None), "role", "")
    is_agent = role in ("admin", "supervisor", "team_lead", "agent")

    if not is_agent and article.visibility == ArticleVisibility.INTERNAL:
        return HttpResponseForbidden("Access denied.")

    rendered_body = _render_body(article.body)
    feedback_form = KBFeedbackForm()
    user_already_gave_feedback = KBArticleFeedback.objects.filter(
        article=article, user=request.user
    ).exists()

    return render(request, "knowledgebase/article_detail.html", {
        "article": article,
        "rendered_body": rendered_body,
        "feedback_form": feedback_form,
        "already_gave_feedback": user_already_gave_feedback,
    })


@login_required
@require_role("admin", "supervisor", "team_lead", "agent")
def article_edit(request, pk=None):
    org = _get_org(request)
    article = get_object_or_404(KBArticle, pk=pk, organization=org) if pk else None

    if request.method == "POST":
        form = KBArticleForm(request.POST, instance=article, organization=org)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.organization = org
            if not pk:
                obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            return redirect("knowledgebase:article_detail", pk=obj.pk)
    else:
        form = KBArticleForm(instance=article, organization=org)

    title = f"Edit: {article.title}" if article else "New Article"
    return render(request, "knowledgebase/article_edit.html", {"form": form, "title": title, "article": article})


@login_required
@require_POST
def article_feedback(request, pk):
    org = _get_org(request)
    article = get_object_or_404(KBArticle, pk=pk, organization=org)

    form = KBFeedbackForm(request.POST)
    if form.is_valid():
        fb = form.save(commit=False)
        fb.article = article
        fb.user = request.user
        fb.save()
        return render(request, "knowledgebase/partials/feedback_thanks.html")

    return render(request, "knowledgebase/partials/feedback_form.html", {
        "article": article, "feedback_form": form,
    })
