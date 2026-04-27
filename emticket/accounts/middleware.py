from django.shortcuts import redirect


class RequesterPortalMiddleware:
    """
    Redirects authenticated requesters away from the main agent UI to /portal/.
    Requesters who land on / or /tickets/* are redirected to /portal/.
    """
    _EXEMPT_PREFIXES = (
        "/portal/",
        "/tickets/new/",      # allow requesters to create tickets
        "/accounts/",
        "/admin/",
        "/notifications/",
        "/healthz/",
        "/readyz/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.path.startswith(self._EXEMPT_PREFIXES)
        ):
            role = getattr(getattr(request.user, "profile", None), "role", "")
            if role == "requester" and not request.path.startswith("/portal/"):
                return redirect("/portal/")

        return self.get_response(request)
