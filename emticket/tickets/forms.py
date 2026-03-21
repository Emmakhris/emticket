from django import forms
from .models import Ticket, TicketComment, TicketAttachment, TicketStatus


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "site", "department", "team",
            "category", "subcategory",
            "title", "description",
            "impact", "urgency",
            "location_detail",
            "related_asset",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "title": forms.TextInput(attrs={"placeholder": "e.g., Printer not printing in Ward A"}),
            "location_detail": forms.TextInput(attrs={"placeholder": "Ward/Room/Unit"}),
        }


class TicketCommentForm(forms.ModelForm):
    is_internal = forms.BooleanField(required=False, initial=False)

    class Meta:
        model = TicketComment
        fields = ["body", "is_internal"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4, "placeholder": "Write a reply..."}),
        }


class TicketStatusForm(forms.Form):
    status = forms.ChoiceField(choices=TicketStatus.choices)


class TicketAssignForm(forms.Form):
    assignee_id = forms.IntegerField(required=False)  # set with select of users in template


class TicketAttachmentForm(forms.ModelForm):
    class Meta:
        model = TicketAttachment
        fields = ["file"]
