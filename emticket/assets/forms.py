from django import forms
from .models import Asset, AssetLocation, AssetType


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ("asset_id", "asset_type", "site", "vendor", "model", "serial_number",
                  "location", "location_text", "notes", "in_service")
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["asset_type"].queryset = AssetType.objects.filter(organization=organization)
            self.fields["location"].queryset = AssetLocation.objects.filter(organization=organization)
            self.fields["site"].queryset = organization.sites.all()


class AssetTypeForm(forms.ModelForm):
    class Meta:
        model = AssetType
        fields = ("name",)


class AssetLocationForm(forms.ModelForm):
    class Meta:
        model = AssetLocation
        fields = ("site", "name", "details")
