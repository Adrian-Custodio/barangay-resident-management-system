from django.db import migrations


def backfill_profiles(apps, schema_editor):
    """
    accounts.signals only creates a Profile on a User's post_save with
    created=True -- it can't retroactively cover Users that already
    existed before that signal was wired up (e.g. an account made via
    `createsuperuser` back when this app was just data models, no
    accounts logic yet). Left alone, that account's Profile.role check
    fails with DoesNotExist the moment it hits any real view.

    Defaults to ENCODER, the same safe default the signal uses -- a
    migration silently promoting whatever Users already exist in
    whatever database this runs against to ADMIN would be a much worse
    surprise than under-privileging them by default.
    """
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("accounts", "Profile")
    # Historical models from apps.get_model() don't carry the Role
    # TextChoices class (only fields survive into migration state), so
    # this uses the raw stored value directly rather than Profile.Role.ENCODER.
    for user in User.objects.filter(profile__isnull=True):
        Profile.objects.create(user=user, role="ENCODER")


def noop_reverse(apps, schema_editor):
    # Deliberately not deleting Profiles on reverse -- a migration
    # rollback shouldn't destroy role assignments an admin may have set
    # by hand after this ran.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_profiles, noop_reverse),
    ]
