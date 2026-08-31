from django import forms

from .models import Official, SiteSettings


class OfficialForm(forms.ModelForm):
    class Meta:
        model = Official
        fields = ["name", "position", "category", "photo", "display_order", "is_active"]


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["background_image"]
