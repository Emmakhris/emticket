from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Role, UserProfile

User = get_user_model()


class UserCreateForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("organization", "site", "department", "team", "role", "is_vip")
        widgets = {
            "role": forms.Select(attrs={"class": "w-full border rounded px-2 py-1"}),
        }


class UserSearchForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": "Search by name or email…"}))
    role = forms.ChoiceField(
        required=False,
        choices=[("", "All roles")] + list(Role.choices),
    )
