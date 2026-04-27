from django import forms
from .models import KBArticle, KBArticleFeedback


class KBArticleForm(forms.ModelForm):
    class Meta:
        model = KBArticle
        fields = ("title", "body", "category", "visibility", "is_active")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 20, "class": "font-mono text-sm"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            from .models import KBCategory
            self.fields["category"].queryset = KBCategory.objects.filter(organization=organization)
            self.fields["category"].required = False


class KBFeedbackForm(forms.ModelForm):
    class Meta:
        model = KBArticleFeedback
        fields = ("was_helpful", "comment")
        widgets = {"comment": forms.Textarea(attrs={"rows": 2, "placeholder": "Optional comment…"})}
