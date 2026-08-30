import datetime

from django import forms

from .models import Resident


class ResidentForm(forms.ModelForm):
    """
    A straight ModelForm: every Resident field is something an encoder
    fills in directly during intake, with no derived/composite values to
    assemble by hand -- so there's no reason to hand-write the field list.

    birth_date gets a SelectDateWidget instead of the default text input.
    A free-text date field on a form used by non-technical office staff
    is a reliable source of malformed dates (mixed MM/DD/YYYY vs DD/MM/YYYY,
    typos); three constrained dropdowns can't be typed wrong, and it
    mirrors how a paper barangay intake form already separates day/month/
    year.
    """

    class Meta:
        model = Resident
        fields = [
            "resident_id",
            "first_name",
            "middle_name",
            "last_name",
            "suffix",
            "birth_date",
            "sex",
            "civil_status",
            "address",
            "purok_or_sitio",
            "contact_number",
        ]
        widgets = {
            "birth_date": forms.SelectDateWidget(
                years=range(1900, datetime.date.today().year + 1)
            ),
        }
        labels = {
            "resident_id": "Resident ID (logbook number)",
            "purok_or_sitio": "Purok / Sitio",
        }
