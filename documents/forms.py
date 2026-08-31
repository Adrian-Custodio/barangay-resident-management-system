import datetime

from django import forms

from residents.models import Resident

from .models import DocumentType


class DocumentTypeForm(forms.ModelForm):
    class Meta:
        model = DocumentType
        fields = ["name", "code", "template_body", "fee", "is_active"]
        widgets = {
            "template_body": forms.Textarea(attrs={"rows": 12}),
        }
        help_texts = {
            "template_body": (
                "Django template syntax. Available variables: "
                "{{ resident }}, {{ document.control_number }}, "
                "{{ document.issued_at }}, {{ purpose }}."
            ),
        }


class IssueDocumentForm(forms.Form):
    """
    Only the two things an encoder actually chooses at issuance time:
    which document, and why. Everything else on the IssuedDocument
    (resident, control_number, issued_by, issued_at) is derived, not
    entered -- see documents.numbering.issue_document.
    """

    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.filter(is_active=True),
        empty_label="Select a document type",
    )
    purpose = forms.CharField(max_length=255, required=False)


class WalkInIssueForm(forms.Form):
    """
    Manual-entry counterpart to IssueDocumentForm, for "Print without an
    account". Not a ModelForm -- there's no Resident row backing this;
    cleaned_data feeds documents.rendering.WalkInSubject (via
    IssuedDocument.walk_in_details) instead, which is why the field set
    mirrors Resident's template-relevant attributes rather than the
    model itself.
    """

    full_name = forms.CharField(max_length=200, label="Full name")
    address = forms.CharField(max_length=255, required=False)
    birth_date = forms.DateField(
        required=False,
        widget=forms.SelectDateWidget(years=range(1900, datetime.date.today().year + 1)),
    )
    sex = forms.ChoiceField(choices=[("", "—")] + list(Resident.Sex.choices), required=False)
    civil_status = forms.ChoiceField(
        choices=[("", "—")] + list(Resident.CivilStatus.choices), required=False,
    )
    purok_or_sitio = forms.CharField(max_length=100, required=False, label="Purok / Sitio")
    contact_number = forms.CharField(max_length=20, required=False)
    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.filter(is_active=True),
        empty_label="Select a document type",
    )
    purpose = forms.CharField(max_length=255, required=False)

    def walk_in_details(self):
        """Everything except document_type/purpose, which live on IssuedDocument directly."""
        data = self.cleaned_data
        return {
            "full_name": data["full_name"],
            "address": data["address"],
            "birth_date": data["birth_date"].isoformat() if data["birth_date"] else "",
            "sex": data["sex"],
            "civil_status": data["civil_status"],
            "purok_or_sitio": data["purok_or_sitio"],
            "contact_number": data["contact_number"],
        }
