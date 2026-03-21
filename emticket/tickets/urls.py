from django.urls import path
from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("new/", views.ticket_create, name="create"),
    path("<uuid:ticket_id>/", views.ticket_detail, name="detail"),

    path("<uuid:ticket_id>/comment/", views.ticket_add_comment, name="add_comment"),
    path("<uuid:ticket_id>/status/", views.ticket_set_status, name="set_status"),
    path("<uuid:ticket_id>/assign/", views.ticket_assign, name="assign"),
    path("<uuid:ticket_id>/unassign/", views.ticket_unassign, name="unassign"),
    path("<uuid:ticket_id>/attachments/", views.ticket_add_attachment, name="add_attachment"),
]