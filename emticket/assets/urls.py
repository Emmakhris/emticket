from django.urls import path
from . import views

app_name = "assets"

urlpatterns = [
    path("", views.asset_list, name="asset_list"),
    path("new/", views.asset_create, name="asset_create"),
    path("<int:asset_id>/", views.asset_detail, name="asset_detail"),
    path("<int:asset_id>/edit/", views.asset_edit, name="asset_edit"),
]
