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
                "{{ document.document_date }}, {{ purpose }}. "
                "control_number is blank while an admin is still reviewing the "
                "document -- it's only assigned once they finalize it."
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


class DocumentReviewForm(forms.Form):
    """
    Step 2 of issuance: review, and optionally edit, the auto-populated
    document before it becomes a real, numbered IssuedDocument. Nothing
    here is saved until this form is submitted -- see numbering.
    issue_document(), which only ever runs at this point, never at step 1.

    document_type travels forward as a hidden field rather than being
    re-selectable on this screen: changing it would mean re-rendering
    body_text from scratch, so going back to step 1 is the right way to
    do that, not a hidden reset baked into this form.
    """

    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.filter(is_active=True), widget=forms.HiddenInput,
    )
    purpose = forms.CharField(max_length=255, required=False)
    document_date = forms.DateField(
        label="Document date",
        widget=forms.SelectDateWidget(years=range(2000, datetime.date.today().year + 2)),
        help_text="Defaults to today. What's printed on the document -- editable here if it needs to be corrected or backdated.",
    )
    body_text = forms.CharField(
        label="Document text",
        widget=forms.Textarea(attrs={"rows": 14}),
        help_text="Auto-populated from the document type's template. Review and adjust before printing.",
    )


class WalkInDocumentReviewForm(DocumentReviewForm):
    """
    The same review step for "Print without an account" -- adds the
    walk-in recipient's details as hidden carry-forward values. They were
    already entered and validated in step 1; this step is about reviewing
    the generated text, not re-entering who it's for.
    """

    full_name = forms.CharField(widget=forms.HiddenInput)
    address = forms.CharField(required=False, widget=forms.HiddenInput)
    birth_date = forms.CharField(required=False, widget=forms.HiddenInput)
    sex = forms.CharField(required=False, widget=forms.HiddenInput)
    civil_status = forms.CharField(required=False, widget=forms.HiddenInput)
    purok_or_sitio = forms.CharField(required=False, widget=forms.HiddenInput)
    contact_number = forms.CharField(required=False, widget=forms.HiddenInput)

    def walk_in_details(self):
        data = self.cleaned_data
        return {
            "full_name": data["full_name"],
            "address": data["address"],
            "birth_date": data["birth_date"],
            "sex": data["sex"],
            "civil_status": data["civil_status"],
            "purok_or_sitio": data["purok_or_sitio"],
            "contact_number": data["contact_number"],
        }
