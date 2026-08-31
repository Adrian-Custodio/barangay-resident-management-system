from django.conf import settings
from django.db import models
from django.utils import timezone

from residents.models import Resident


class DocumentType(models.Model):
    """
    Catalog/lookup table: the 23 kinds of documents this barangay issues
    (clearance, indigency certificate, residency certificate, etc.) and
    their template text. This is configuration data — it describes what
    CAN be issued, not any specific issuance event.

    Mirrors the classic "Product vs Order" relational pattern: a catalog
    table (what's possible) separate from a transaction table (what
    actually happened) — see IssuedDocument below.
    """

    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)  # short code, e.g. "BRGY-CLR"
    template_body = models.TextField(
        help_text="Template text with placeholders, e.g. {{resident.full_name}}"
    )
    fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class IssuedDocument(models.Model):
    """
    Transaction record: THIS resident was issued THIS type of document,
    on THIS date, with THIS control number, by THIS staff member.

    control_number is a real-world requirement, not a technical one:
    physical barangay documents need a traceable reference so their
    authenticity can be verified later. Enforcing uniqueness at the
    schema level turns a paperwork rule into a database constraint.

    resident is nullable to support "Print without an account" (a walk-in
    who isn't in the Resident table at all): walk_in_details then carries
    whatever the encoder typed by hand -- a dict rather than a matching
    set of nullable columns, because it's rendered into the exact same
    document_type.template_body a real Resident would be (see
    rendering.py's WalkInSubject), so it only ever needs to hold
    Resident-shaped data, never grow its own independent schema.
    A row always has exactly one of resident or walk_in_details set, never
    both, never neither -- enforced in numbering.issue_document(), not at
    the DB level (SQLite's CHECK constraint support makes that more
    friction than the guarantee is worth here).
    """

    resident = models.ForeignKey(
        Resident, on_delete=models.PROTECT, related_name="issued_documents",
        null=True, blank=True,
    )
    walk_in_details = models.JSONField(
        null=True, blank=True,
        help_text="Manually entered recipient info for a walk-in with no Resident record.",
    )
    document_type = models.ForeignKey(
        DocumentType, on_delete=models.PROTECT, related_name="issuances"
    )
    control_number = models.CharField(max_length=30, unique=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    # The system's own record of when this row was created -- immutable
    # (auto_now_add), used for control-number sequencing and audit
    # ordering. NOT what's printed on the document; see document_date.
    issued_at = models.DateTimeField(auto_now_add=True)
    purpose = models.CharField(max_length=255, blank=True)

    # The date shown on the printed document. Defaults to today but is
    # editable in the review step before finalizing (an office sometimes
    # needs to correct or backdate this) -- deliberately a separate field
    # from issued_at rather than making issued_at itself editable, so the
    # true "when was this actually issued" system record can never be
    # quietly rewritten.
    document_date = models.DateField(default=timezone.localdate)

    # The rendered document text as reviewed and (optionally) edited by
    # the admin, captured at issuance time -- not regenerated from
    # document_type.template_body on every view. Without this, editing a
    # DocumentType's wording later would silently rewrite the text of
    # every document already issued from it, which is wrong for records
    # that are supposed to be an immutable account of what was actually
    # printed. Blank on rows created before this field existed; those
    # still fall back to live rendering (see rendering.build_subject and
    # views._RenderedDocumentMixin).
    body_text = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        recipient = self.resident.full_name if self.resident_id else self.recipient_name
        return f"{self.control_number} - {self.document_type.name} - {recipient}"

    @property
    def recipient_name(self):
        """Works whether this was issued to a real Resident or a walk-in."""
        if self.resident_id:
            return self.resident.full_name
        return (self.walk_in_details or {}).get("full_name", "Walk-in")
