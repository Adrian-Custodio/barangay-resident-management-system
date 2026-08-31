from django.db import models


class Official(models.Model):
    """
    A barangay official shown on the home page -- distinct from `accounts.
    Profile` on purpose. A Profile is a *system user* (someone who logs in
    and does encoder/admin work); an Official is a *directory entry* for
    the home page roster (an elected Kagawad, an appointed Treasurer) who
    may never touch this system at all. Conflating the two would force
    every official to have a login just to appear on a page.

    Unlike face-recognition photos (FaceProfile never stores the raw
    image -- see recognition/models.py), `photo` here is deliberately
    persisted: this is a public-facing directory photo meant to be
    displayed, not biometric data meant to be kept unrecoverable.
    """

    class Category(models.TextChoices):
        ELECTED = "ELECTED", "Elected Official"
        APPOINTED = "APPOINTED", "Appointed Staff"

    name = models.CharField(max_length=150)
    position = models.CharField(max_length=100)  # e.g. "Barangay Captain", "Kagawad", "Secretary"
    category = models.CharField(max_length=10, choices=Category.choices)
    photo = models.ImageField(upload_to="officials/", blank=True, null=True)
    display_order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers appear first within their column."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "display_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.position})"


class SiteSettings(models.Model):
    """
    Home-page display configuration an admin can change from the app
    itself, not by editing code. Deliberately a soft singleton (save()
    always writes to pk=1) rather than a proper singleton pattern with a
    dedicated package -- one settings row is all this needs, and
    `SiteSettings.load()` is the only access path the rest of the app
    uses, so nothing depends on how the constraint is enforced.
    """

    background_image = models.ImageField(upload_to="site/", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Site settings"
