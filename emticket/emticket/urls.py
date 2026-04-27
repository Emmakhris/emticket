from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("django.contrib.auth.urls")),

    path("", include("reporting.urls")),        # dashboard at /
    path("tickets/", include("tickets.urls")),
    path("users/", include("accounts.urls")),
    path("organizations/", include("organizations.urls")),
    path("assets/", include("assets.urls")),
    path("automations/", include("automations.urls")),
    path("sla/", include("sla.urls")),
    path("notifications/", include("notifications.urls")),

    path("healthz/", lambda request: JsonResponse({"status": "ok"})),
    path("readyz/", lambda request: JsonResponse({"ready": True})),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
