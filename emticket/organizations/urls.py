from django.urls import path
from . import views

app_name = "organizations"

urlpatterns = [
    path("", views.org_list, name="org_list"),
    path("new/", views.org_create, name="org_create"),
    path("<int:org_id>/edit/", views.org_edit, name="org_edit"),
    path("<int:org_id>/sites/", views.site_list, name="site_list"),
    path("<int:org_id>/sites/new/", views.site_create, name="site_create"),
    path("<int:org_id>/sites/<int:site_id>/edit/", views.site_edit, name="site_edit"),
    path("<int:org_id>/sites/<int:site_id>/calendar/", views.calendar_edit, name="calendar_edit"),
    path("<int:org_id>/departments/", views.department_list, name="department_list"),
    path("<int:org_id>/departments/new/", views.department_create, name="department_create"),
    path("<int:org_id>/departments/<int:dept_id>/edit/", views.department_edit, name="department_edit"),
    path("<int:org_id>/departments/<int:dept_id>/teams/", views.team_list, name="team_list"),
    path("<int:org_id>/departments/<int:dept_id>/teams/new/", views.team_create, name="team_create"),
]
