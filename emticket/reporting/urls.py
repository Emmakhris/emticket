from django.urls import path
from . import views

app_name = "reporting"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("analytics/", views.analytics, name="analytics"),
    path("saved-views/", views.saved_views_list, name="saved_views"),
    path("saved-views/new/", views.saved_view_create, name="saved_view_create"),
    path("saved-views/<int:pk>/delete/", views.saved_view_delete, name="saved_view_delete"),
]
