from django.urls import path
from . import views

app_name = "knowledgebase"

urlpatterns = [
    path("", views.article_list, name="article_list"),
    path("new/", views.article_edit, name="article_new"),
    path("<int:pk>/", views.article_detail, name="article_detail"),
    path("<int:pk>/edit/", views.article_edit, name="article_edit"),
    path("<int:pk>/feedback/", views.article_feedback, name="article_feedback"),
    path("suggest/", views.suggest, name="suggest"),
]
