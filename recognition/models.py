from django.db import models

from residents.models import Resident


class FaceProfile(models.Model):
    """
    Stores a face EMBEDDING (a numeric vector), not the photo itself.

    DeepFace converts a detected face into a fixed-length vector that
    encodes facial geometry. It cannot be reversed back into an image.
    Storing this instead of the raw photo means:
      - a database leak exposes no photos, only abstract numbers
      - comparing two residents is a fast vector-distance calculation,
        not a re-run of face detection + feature extraction each time

    `model_name` matters: embeddings from Facenet are not directly
    comparable to embeddings from a different model (e.g. ArcFace). If the
    recognition model is ever upgraded, every resident needs re-enrollment
    under the new model — that's a real operational constraint, not just
    a technical footnote.
    """

    resident = models.OneToOneField(
        Resident, on_delete=models.CASCADE, related_name="face_profile"
    )
    embedding = models.JSONField()  # serialized vector, e.g. [0.123, -0.045, ...]
    model_name = models.CharField(max_length=50, default="Facenet")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"FaceProfile({self.resident.full_name}, {self.model_name})"


class FaceVerificationAttempt(models.Model):
    """
    A log of each comparison made against a FaceProfile — kept separate
    from the enrolled profile itself. The profile is the reference data;
    this table is the history of attempts made against that reference.
    Mirrors what gets written to the shared AuditLog, but keeps
    recognition-specific detail (distance score, threshold used) local
    to this app rather than bloating the generic audit table.
    """

    resident = models.ForeignKey(
        Resident, on_delete=models.CASCADE, related_name="verification_attempts"
    )
    distance = models.FloatField()  # lower = more similar, model-dependent metric
    threshold = models.FloatField()  # cutoff used to decide match/no-match
    matched = models.BooleanField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-attempted_at"]

    def __str__(self):
        result = "MATCH" if self.matched else "NO MATCH"
        return f"{self.resident.full_name} - {result} ({self.distance:.4f})"
