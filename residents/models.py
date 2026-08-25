from django.db import models


class Resident(models.Model):
    """
    The core entity. Everything else (face embeddings, generated documents,
    audit entries) points back to a Resident via ForeignKey.

    Design notes:
    - Name fields are kept separate (not one `full_name` string) because
      official documents need specific print formats, e.g.
      "DELA CRUZ, Juan Santos Jr." — that's not reliably reconstructable
      from a single free-text field once it's been merged.
    - Fuzzy search (thefuzz) happens in Python at query time against these
      fields; it's an application-layer algorithm, not a DB feature, so no
      special "searchable" column is needed here.
    - `resident_id` is a separate indexed field, distinct from the DB's
      auto-incrementing `id`. Barangays keep their own logbook numbering,
      and using the raw DB primary key as a public-facing ID is a minor
      anti-pattern (leaks row counts, brittle if data is ever migrated).
    """

    class Sex(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    class CivilStatus(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        MARRIED = "MARRIED", "Married"
        WIDOWED = "WIDOWED", "Widowed"
        SEPARATED = "SEPARATED", "Separated"

    resident_id = models.CharField(max_length=20, unique=True, db_index=True)

    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=10, blank=True)  # Jr., Sr., III...

    birth_date = models.DateField()
    sex = models.CharField(max_length=1, choices=Sex.choices)
    civil_status = models.CharField(max_length=10, choices=CivilStatus.choices)

    address = models.CharField(max_length=255)
    purok_or_sitio = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)

    is_active = models.BooleanField(default=True)  # soft-delete flag
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        parts = [self.last_name + ",", self.first_name, self.middle_name, self.suffix]
        return " ".join(p for p in parts if p)
