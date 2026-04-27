from django import forms
from .models import AutomationRule


class AutomationRuleForm(forms.ModelForm):
    class Meta:
        model = AutomationRule
        fields = ("name", "trigger", "priority", "enabled", "run_once", "conditions", "actions")
        widgets = {
            "conditions": forms.Textarea(attrs={"rows": 6, "class": "font-mono text-xs w-full"}),
            "actions": forms.Textarea(attrs={"rows": 6, "class": "font-mono text-xs w-full"}),
        }
        help_texts = {
            "conditions": 'JSON: {"all":[{"field":"status","op":"eq","value":"new"}]}',
            "actions": 'JSON array: [{"type":"assign_team","value":1}]',
            "priority": "Lower number runs first.",
            "run_once": "If checked, this rule only fires once per ticket. Uncheck for repeating rules (e.g. SLA alerts).",
        }
