from django.conf import settings
from django.db import models


class Profile(models.Model):
    """
    Extends Django's built-in User model with a role field.

    We use a OneToOneField rather than a custom AbstractUser because:
    - We don't need custom authentication logic (login by username/password
      is fine as-is).
    - OneToOneField is additive: it can be introduced at any point in a
      project's life without touching the auth system Django already built.
    - A custom User model must be configured before the FIRST migration
      ever runs on a project — too risky/irreversible for what we need here.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        ENCODER = "ENCODER", "Encoder / Staff"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.ENCODER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
