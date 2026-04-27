from django.contrib import admin

from .models import Department, Organization, Site, Team, WorkingCalendar


class SiteInline(admin.TabularInline):
    model = Site
    extra = 0
    fields = ("name", "code", "address")


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 0
    fields = ("name", "code", "is_confidential")


class TeamInline(admin.TabularInline):
    model = Team
    extra = 0
    fields = ("name", "department", "email_alias", "is_active")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    inlines = [SiteInline, DepartmentInline]


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "organization")
    list_filter = ("organization",)
    search_fields = ("name", "code")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "organization", "is_confidential")
    list_filter = ("organization", "is_confidential")
    search_fields = ("name", "code")
    inlines = [TeamInline]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "organization", "is_active")
    list_filter = ("organization", "department", "is_active")
    search_fields = ("name",)


@admin.register(WorkingCalendar)
class WorkingCalendarAdmin(admin.ModelAdmin):
    list_display = ("site", "timezone")
    search_fields = ("site__name",)
