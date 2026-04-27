from django import forms
from tickets.models import Priority
from .models import SLAPolicy


class SLAPolicyForm(forms.ModelForm):
    class Meta:
        model = SLAPolicy
        fields = ("department", "site", "category", "priority", "first_response_minutes", "resolution_minutes", "is_active")
        help_texts = {
            "first_response_minutes": "Business minutes until first response is due.",
            "resolution_minutes": "Business minutes until ticket must be resolved.",
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            from organizations.models import Department, Site
            from tickets.models import TicketCategory
            self.fields["department"].queryset = Department.objects.filter(organization=organization)
            self.fields["site"].queryset = Site.objects.filter(organization=organization)
            self.fields["category"].queryset = TicketCategory.objects.filter(organization=organization)
