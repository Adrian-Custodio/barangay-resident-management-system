from django.contrib.contenttypes.models import ContentType

from .models import AuditLog


def log_action(actor, action, target, detail=""):
    """
    Single write path for AuditLog. Without this, every app that needs to
    log something would hand-assemble content_type/object_id itself --
    easy to get subtly wrong (e.g. logging target.__class__ instead of
    target's actual instance) and impossible to change consistently later
    (e.g. adding a new field to every log entry).

    `actor` may be None -- AuditLog.actor is nullable specifically for
    actions that don't originate from a logged-in request (e.g. a future
    management command or scheduled job), though every call site today
    passes request.user.
    """
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        content_type=ContentType.objects.get_for_model(target),
        object_id=target.pk,
        detail=detail,
    )
