from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.user_list, name="user_list"),
    path("new/", views.user_create, name="user_create"),
    path("<int:user_id>/", views.user_detail, name="user_detail"),
    path("<int:user_id>/profile/", views.user_update_profile, name="user_update_profile"),
]
