from django import forms
from .models import Department, Organization, Site, Team, WorkingCalendar


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ("name", "code", "is_active")


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ("name", "code", "address")
        widgets = {"address": forms.Textarea(attrs={"rows": 2})}


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ("name", "code", "is_confidential")


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ("name", "department", "email_alias", "is_active")

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["department"].queryset = Department.objects.filter(organization=organization)


class WorkingCalendarForm(forms.ModelForm):
    class Meta:
        model = WorkingCalendar
        fields = ("timezone", "weekly_hours", "holidays")
        widgets = {
            "weekly_hours": forms.Textarea(attrs={"rows": 10, "class": "font-mono text-xs"}),
            "holidays": forms.Textarea(attrs={"rows": 4, "class": "font-mono text-xs"}),
        }
        help_texts = {
            "weekly_hours": 'JSON: {"mon":[["08:00","17:00"]],"tue":[["08:00","17:00"]],...}',
            "holidays": 'JSON array of dates: ["2026-01-01","2026-03-06"]',
        }
