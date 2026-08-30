from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """
    Every User needs a Profile so role checks (`profile.role`,
    `profile.is_admin`) never hit a DoesNotExist. This matters most for
    `createsuperuser`, which creates a User outside of any view we control
    -- there's no request/response cycle where we could otherwise create
    the Profile ourselves. Defaulting to ENCODER (the model's default) is
    the safe failure mode: a superuser can promote themselves to ADMIN via
    /admin/ afterwards, but nobody is silently granted admin rights by
    just signing up.
    """
    if created:
        Profile.objects.get_or_create(user=instance)
