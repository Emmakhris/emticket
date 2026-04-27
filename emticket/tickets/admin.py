from django.contrib import admin

from .models import (
    CSAT,
    Ticket,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    TicketDependency,
    TicketLink,
    TicketSubcategory,
)


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    readonly_fields = ("author", "created_at", "is_internal")
    fields = ("author", "is_internal", "body", "created_at")


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ("uploaded_by", "filename", "content_type", "size_bytes", "created_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "title", "status", "priority", "department", "assignee", "requester", "created_at")
    list_filter = ("status", "priority", "department", "organization", "visibility")
    search_fields = ("ticket_number", "title", "description")
    readonly_fields = ("id", "ticket_number", "created_at", "updated_at", "first_response_at", "resolved_at", "closed_at")
    raw_id_fields = ("requester", "assignee", "organization", "department", "team", "site", "category", "subcategory", "related_asset")
    inlines = [TicketCommentInline, TicketAttachmentInline]
    date_hierarchy = "created_at"


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "organization", "is_active")
    list_filter = ("organization", "department", "is_active")
    search_fields = ("name",)


@admin.register(TicketSubcategory)
class TicketSubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(CSAT)
class CSATAdmin(admin.ModelAdmin):
    list_display = ("ticket", "user", "rating", "created_at")
    list_filter = ("rating",)
    readonly_fields = ("ticket", "user", "created_at")


@admin.register(TicketLink)
class TicketLinkAdmin(admin.ModelAdmin):
    list_display = ("from_ticket", "relation", "to_ticket", "created_at")
    list_filter = ("relation",)


@admin.register(TicketDependency)
class TicketDependencyAdmin(admin.ModelAdmin):
    list_display = ("blocked_ticket", "depends_on_ticket", "created_at")
