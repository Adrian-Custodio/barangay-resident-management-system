from django.conf import settings
from django.db import models

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
    """

    resident = models.ForeignKey(
        Resident, on_delete=models.PROTECT, related_name="issued_documents"
    )
    document_type = models.ForeignKey(
        DocumentType, on_delete=models.PROTECT, related_name="issuances"
    )
    control_number = models.CharField(max_length=30, unique=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    purpose = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.control_number} - {self.document_type.name} - {self.resident.full_name}"
