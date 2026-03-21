from django.conf import settings
from django.db import models

from organizations.models import Organization, Department


class ArticleVisibility(models.TextChoices):
    INTERNAL = "internal", "Internal"
    PUBLIC = "public", "Public"


class KBCategory(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="kb_categories")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="kb_categories")
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ("organization", "department", "name")


class KBArticle(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="kb_articles")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="kb_articles")
    category = models.ForeignKey(KBCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")

    title = models.CharField(max_length=255)
    body = models.TextField()  # markdown/html
    visibility = models.CharField(max_length=20, choices=ArticleVisibility.choices, default=ArticleVisibility.INTERNAL)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="kb_created")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="kb_updated")

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class KBArticleFeedback(models.Model):
    article = models.ForeignKey(KBArticle, on_delete=models.CASCADE, related_name="feedback")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    was_helpful = models.BooleanField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
