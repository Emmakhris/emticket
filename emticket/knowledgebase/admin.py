from django.contrib import admin

from .models import KBArticle, KBArticleFeedback, KBCategory


class KBArticleFeedbackInline(admin.TabularInline):
    model = KBArticleFeedback
    extra = 0
    readonly_fields = ("user", "was_helpful", "comment", "created_at")


@admin.register(KBCategory)
class KBCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "organization")
    list_filter = ("organization", "department")
    search_fields = ("name",)


@admin.register(KBArticle)
class KBArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "category", "visibility", "is_active", "created_by", "updated_at")
    list_filter = ("organization", "department", "visibility", "is_active")
    search_fields = ("title", "body")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")
    inlines = [KBArticleFeedbackInline]


@admin.register(KBArticleFeedback)
class KBArticleFeedbackAdmin(admin.ModelAdmin):
    list_display = ("article", "user", "was_helpful", "created_at")
    list_filter = ("was_helpful",)
    readonly_fields = ("article", "user", "was_helpful", "comment", "created_at")
