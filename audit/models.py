from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLog(models.Model):
    """
    A single, shared log table for every sensitive action across the system,
    instead of one log table per app (residents_log, documents_log, etc.).

    Uses Django's GenericForeignKey (content_type + object_id) so one row
    can point to ANY model — a Resident, a Document, a face verification
    attempt — without this app importing or depending on any of them.

    This is the key decoupling decision: `audit` has zero foreign-key
    dependency on `residents`, `documents`, or `recognition`. Those apps
    depend on `audit` (they call into it to log), not the other way
    around. That one-directional dependency is what keeps the apps
    genuinely separable.
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Created"
        VIEW = "VIEW", "Viewed"
        UPDATE = "UPDATE", "Updated"
        DELETE = "DELETE", "Deleted"
        FACE_VERIFY_SUCCESS = "FACE_VERIFY_OK", "Face Verification Succeeded"
        FACE_VERIFY_FAIL = "FACE_VERIFY_FAIL", "Face Verification Failed"
        DOCUMENT_ISSUED = "DOC_ISSUED", "Document Issued"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=20, choices=Action.choices)

    # --- Generic relation: points to any model instance ---
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    detail = models.TextField(blank=True)  # free-text context, e.g. failure reason
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.actor} {self.action}"
