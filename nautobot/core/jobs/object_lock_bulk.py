"""System Jobs for bulk locking / releasing objects."""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.dateparse import parse_datetime

from nautobot.extras.choices import ObjectLockModeChoices
from nautobot.extras.jobs import ChoiceVar, Job, JSONVar, ObjectVar, StringVar
from nautobot.extras.models import ObjectLock
from nautobot.extras.models.object_locks import OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH

name = "System Jobs"


def _mode_flags(mode):
    """Translate an ObjectLockModeChoices value into (prevent_delete, prevent_update).

    Args:
        mode: One of the ObjectLockModeChoices values (``delete``, ``update``, ``both``).

    Returns:
        A (prevent_delete, prevent_update) tuple of booleans.
    """
    return {
        ObjectLockModeChoices.DELETE: (True, False),
        ObjectLockModeChoices.UPDATE: (False, True),
        ObjectLockModeChoices.BOTH: (True, True),
    }[mode]


class BulkLockObjects(Job):
    """Create one Object Lock claim per selected object."""

    content_type = ObjectVar(model=ContentType, description="Type of objects to lock")
    pk_list = JSONVar(description="List of object PKs to lock")
    mode = ChoiceVar(choices=ObjectLockModeChoices, description="delete-locked / update-locked / both")
    reason = StringVar(description="Justification recorded on each claim")
    source_key = StringVar(description="Stable owner identifier", max_length=OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH)
    expires = StringVar(description="ISO-8601 expiry timestamp (required)")

    class Meta:
        name = "Bulk Lock Objects"
        description = "Create an Object Lock on each selected object."
        has_sensitive_variables = False
        soft_time_limit = 1800
        time_limit = 2000
        hidden = True

    def run(self, *, content_type, pk_list, mode, reason, source_key, expires):  # pylint: disable=arguments-differ
        """Lock each selected object, reporting how many were actioned vs. skipped.

        Args:
            content_type: ContentType of the objects to lock.
            pk_list: List of object primary keys to lock.
            mode: One of the ObjectLockModeChoices values controlling prevent_delete/prevent_update.
            reason: Human-readable justification recorded on each claim.
            source_key: Stable owner identifier shared by the created claims.
            expires: ISO-8601 expiry timestamp parsed via ``parse_datetime``.

        Returns:
            A summary string: how many objects were locked and how many failed.

        Raises:
            PermissionDenied: If the user lacks the ``extras.add_objectlock`` permission.
        """
        # Creating Object Locks requires the add permission.
        if not self.user.has_perm("extras.add_objectlock"):
            raise PermissionDenied("User does not have permission to create Object Locks")
        model = content_type.model_class()
        if model is None:
            raise ValidationError("The content type's model is no longer installed.")
        prevent_delete, prevent_update = _mode_flags(mode)
        # The bulk-lock form guarantees a valid value; a None result is acceptable (manager applies default TTL).
        expiry = parse_datetime(expires)
        # Enforce object-level view permissions on the targets.
        queryset = model.objects.restrict(self.user, "view").filter(pk__in=pk_list)
        actioned = 0
        failed = 0
        for obj in queryset:
            try:
                ObjectLock.objects.lock(
                    obj,
                    prevent_delete=prevent_delete,
                    prevent_update=prevent_update,
                    reason=reason,
                    expires=expiry,
                    source_key=source_key,
                    requesting_user=self.user,
                )
                actioned += 1
            except (ValidationError, TypeError) as err:
                # One bad target (e.g. a rejected expiry or field name) must not abort the whole batch.
                self.logger.warning("Could not lock %s: %s", obj, err)
                failed += 1
        summary = f"{actioned} locked, {failed} failed"
        self.logger.info(summary)
        return summary


class BulkReleaseObjects(Job):
    """Release Object Lock claims on selected objects for a given source key."""

    content_type = ObjectVar(model=ContentType, description="Type of objects to release")
    pk_list = JSONVar(description="List of object PKs to release")
    source_key = StringVar(
        description="Source key of claims to release", required=False, max_length=OBJECT_LOCK_SOURCE_KEY_MAX_LENGTH
    )

    class Meta:
        name = "Bulk Release Objects"
        description = "Release Object Lock claims on each selected object."
        has_sensitive_variables = False
        soft_time_limit = 1800
        time_limit = 2000
        hidden = True

    def run(self, *, content_type, pk_list, source_key=None):  # pylint: disable=arguments-differ
        """Release lock claims on each selected object, reporting actioned vs. skipped.

        Ownership is determined solely by ``created_by``: a user releasing their own claim needs
        ``extras.delete_objectlock``, while releasing another owner's claim needs
        ``extras.force_release_objectlock``. ``source_key`` is purely a filter for *which* claims to
        target, never an authorization signal.

        Args:
            content_type: ContentType of the objects to release.
            pk_list: List of object primary keys to release.
            source_key: Optional source key filtering which claims to target.

        Returns:
            A summary string reporting how many objects were actioned and how many were skipped.
        """
        model = content_type.model_class()
        if model is None:
            raise ValidationError("The content type's model is no longer installed.")
        # Enforce object-level view permissions on the targets.
        queryset = model.objects.restrict(self.user, "view").filter(pk__in=pk_list)
        actioned = 0
        skipped = 0
        for obj in queryset:
            claims = ObjectLock.objects.active().for_object(obj)
            if source_key:
                claims = claims.filter(source_key=source_key)
            released_any = False
            for claim in claims:
                is_own = claim.created_by_id == self.user.pk
                permitted = (
                    self.user.has_perm("extras.delete_objectlock")
                    if is_own
                    else self.user.has_perm("extras.force_release_objectlock")
                )
                if not permitted:
                    continue
                ObjectLock.objects.release(obj, source_key=claim.source_key)
                released_any = True
            if released_any:
                actioned += 1
            else:
                skipped += 1
        summary = f"{actioned} released, {skipped} skipped (no releasable claim)"
        self.logger.info(summary)
        return summary
