from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import require_role
from .forms import UserCreateForm, UserProfileForm, UserSearchForm
from .models import UserProfile

User = get_user_model()


@login_required
@require_role("admin", "supervisor")
def user_list(request):
    profile = getattr(request.user, "profile", None)
    qs = User.objects.select_related("profile").filter(
        profile__organization=profile.organization
    ).order_by("first_name", "last_name", "username")

    q = (request.GET.get("q") or "").strip()
    role = (request.GET.get("role") or "").strip()

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q) | Q(username__icontains=q)
        )
    if role:
        qs = qs.filter(profile__role=role)

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page_obj": page_obj,
        "users": page_obj.object_list,
        "search_form": UserSearchForm(request.GET),
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, "accounts/partials/user_table.html", context)

    return render(request, "accounts/user_list.html", context)


@login_required
@require_role("admin", "supervisor")
def user_create(request):
    if request.method == "POST":
        user_form = UserCreateForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.email = user_form.cleaned_data["email"]
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user
            # New users inherit the admin's organization if not explicitly set
            requester_profile = getattr(request.user, "profile", None)
            if not profile.organization_id and requester_profile:
                profile.organization = requester_profile.organization
            profile.save()

            return redirect("accounts:user_detail", user_id=user.pk)
    else:
        user_form = UserCreateForm()
        requester_profile = getattr(request.user, "profile", None)
        initial = {}
        if requester_profile:
            initial["organization"] = requester_profile.organization
        profile_form = UserProfileForm(initial=initial)

    return render(request, "accounts/user_create.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })


@login_required
@require_role("admin", "supervisor")
def user_detail(request, user_id):
    target_user = get_object_or_404(
        User.objects.select_related("profile__organization", "profile__department", "profile__team"),
        pk=user_id,
    )
    profile, _ = UserProfile.objects.get_or_create(
        user=target_user,
        defaults={"organization": request.user.profile.organization},
    )
    profile_form = UserProfileForm(instance=profile)

    return render(request, "accounts/user_detail.html", {
        "target_user": target_user,
        "profile": profile,
        "profile_form": profile_form,
    })


@login_required
@require_role("admin", "supervisor")
def user_update_profile(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    profile, _ = UserProfile.objects.get_or_create(
        user=target_user,
        defaults={"organization": request.user.profile.organization},
    )

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    form = UserProfileForm(request.POST, instance=profile)
    if form.is_valid():
        form.save()
        profile.refresh_from_db()
        return render(request, "accounts/partials/profile_card.html", {
            "target_user": target_user,
            "profile": profile,
            "profile_form": UserProfileForm(instance=profile),
            "saved": True,
        })

    return render(request, "accounts/partials/profile_card.html", {
        "target_user": target_user,
        "profile": profile,
        "profile_form": form,
    }, status=422)
