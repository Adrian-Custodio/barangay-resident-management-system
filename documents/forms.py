from django import forms

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
