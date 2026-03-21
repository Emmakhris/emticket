from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("django.contrib.auth.urls")),

    # Keep only the app URLs that actually exist
    path("", include("tickets.urls")),

    # Health checks
    path("healthz/", lambda request: JsonResponse({"status": "ok"})),
    path("readyz/", lambda request: JsonResponse({"ready": True})),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)