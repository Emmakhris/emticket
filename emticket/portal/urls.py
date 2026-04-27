from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("", views.my_tickets, name="my_tickets"),
    path("<uuid:ticket_id>/", views.ticket_detail, name="ticket_detail"),
    path("<uuid:ticket_id>/csat/", views.submit_csat, name="csat"),
]
