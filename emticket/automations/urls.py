from django.urls import path
from . import views

app_name = "automations"

urlpatterns = [
    path("", views.rule_list, name="rule_list"),
    path("new/", views.rule_create, name="rule_create"),
    path("<int:rule_id>/", views.rule_detail, name="rule_detail"),
    path("<int:rule_id>/edit/", views.rule_edit, name="rule_edit"),
    path("<int:rule_id>/toggle/", views.rule_toggle, name="rule_toggle"),
    path("<int:rule_id>/test/", views.rule_test, name="rule_test"),
]
