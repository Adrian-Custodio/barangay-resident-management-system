"""
control_number generation and issuance.

Kept out of views.py because "what makes a control number valid/unique"
is a business rule independent of any particular request-handling code --
worth testing and reasoning about on its own.
"""
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import IssuedDocument

MAX_ISSUANCE_ATTEMPTS = 5


def _next_control_number(year):
    """
    Format: {BARANGAY_CODE}-{year}-{sequence, zero-padded to 4 digits},
    e.g. BRGY-2026-0001. The sequence resets each year (matching how a
    physical barangay logbook is numbered) and is derived by counting
    this year's existing IssuedDocuments rather than kept in a separate
    counter table -- one less piece of state to keep in sync. That does
    leave a small race window under concurrent issuance; see
    issue_document() below, which closes it by retrying on collision
    instead of relying on this function alone to guarantee uniqueness.
    """
    count_this_year = IssuedDocument.objects.filter(issued_at__year=year).count()
    sequence = count_this_year + 1
    return f"{settings.BARANGAY_CODE}-{year}-{sequence:04d}"


def issue_document(*, document_type, purpose, issued_by, resident=None, walk_in_details=None):
    """
    Creates the IssuedDocument row with a freshly generated control
    number, retrying with the next number if a concurrent request won the
    same one first. control_number's DB-level uniqueness constraint is
    the actual source of truth here -- the retry loop is just what makes
    that constraint survive a race instead of surfacing as a 500 error.

    Exactly one of resident / walk_in_details must be given -- this is
    the single call path every issuance goes through (the normal
    resident-scoped flow and "Print without an account" both end up
    here), so it's the right place to enforce that invariant once instead
    of trusting every caller to get it right.
    """
    if bool(resident) == bool(walk_in_details):
        raise ValueError("issue_document requires exactly one of resident or walk_in_details.")

    year = timezone.now().year
    last_error = None
    for _ in range(MAX_ISSUANCE_ATTEMPTS):
        control_number = _next_control_number(year)
        try:
            with transaction.atomic():
                return IssuedDocument.objects.create(
                    resident=resident,
                    walk_in_details=walk_in_details,
                    document_type=document_type,
                    control_number=control_number,
                    issued_by=issued_by,
                    purpose=purpose,
                )
        except IntegrityError as exc:
            last_error = exc
            continue
    raise last_error
