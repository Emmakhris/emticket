from django.urls import path
from . import views

app_name = "sla"

urlpatterns = [
    path("policies/", views.policy_list, name="policy_list"),
    path("policies/new/", views.policy_create, name="policy_create"),
    path("policies/<int:pk>/edit/", views.policy_edit, name="policy_edit"),
    path("policies/cell/", views.policy_cell, name="policy_cell"),
]
