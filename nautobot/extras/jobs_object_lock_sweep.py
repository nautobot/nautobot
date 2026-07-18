"""System Job: periodically purge expired and orphaned Object Locks."""

import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef
from django.utils import timezone

from nautobot.extras.jobs import Job
from nautobot.extras.locking import (
    object_lock_sweep_failed_content_types_counter,
    object_lock_sweep_last_success_gauge,
)
from nautobot.extras.models import ObjectLock

logger = logging.getLogger(__name__)

name = "System Jobs"


def purge_expired_and_orphaned_locks():
    """Delete expired locks and locks whose target no longer exists.

    Orphan detection is set-based per content type, using an anti-join
    (``NOT EXISTS (SELECT 1 FROM <target_table> WHERE pk = object_id)``) rather than ``NOT IN``,
    so it scales on large target tables.

    Returns:
        A dict ``{"expired": int, "orphaned": int, "failed_content_types": int}`` where
        ``failed_content_types`` counts content types whose orphan purge raised and was skipped
        (logged, not aborted).
    """
    now = timezone.now()

    # 1) Expired locks.
    expired_qs = ObjectLock.objects.filter(expires__isnull=False, expires__lte=now)
    expired_count = expired_qs.count()
    if expired_count:
        expired_qs.delete()

    # 2) Orphaned locks — one set-based query per locked content type.
    orphaned_count = 0
    failed_content_types = 0
    remaining_ct_ids = list(ObjectLock.objects.values_list("content_type_id", flat=True).distinct())
    for ct_id in remaining_ct_ids:
        try:
            model = ContentType.objects.get_for_id(ct_id).model_class()
            if model is None:
                # Target model no longer installed: every claim is orphaned.
                orphaned_count += ObjectLock.objects.filter(content_type_id=ct_id).delete()[0]
                continue
            # Anti-join (NOT EXISTS) rather than NOT IN (huge pk list), which scales on large target tables.
            target_exists = model.objects.filter(pk=OuterRef("object_id"))
            orphan_qs = ObjectLock.objects.filter(content_type_id=ct_id).filter(~Exists(target_exists))
            orphaned_count += orphan_qs.delete()[0]
        except Exception:  # pylint: disable=broad-exception-caught
            # One bad content type must not abort the sweep — log and continue so the rest are purged.
            logger.exception("Object Lock sweep: failed to purge orphaned locks for content_type_id=%s", ct_id)
            failed_content_types += 1
            object_lock_sweep_failed_content_types_counter.inc()

    # Record completion even if some content types failed (those were logged). The gauge means
    # "the sweep last finished", so a partial failure must not masquerade as a stale/never-run sweep.
    object_lock_sweep_last_success_gauge.set(now.timestamp())
    return {"expired": expired_count, "orphaned": orphaned_count, "failed_content_types": failed_content_types}


class ObjectLockSweep(Job):
    """Purge expired and orphaned Object Locks."""

    class Meta:
        name = "Object Lock Sweep"
        description = "Delete expired Object Locks and locks whose target object no longer exists."
        has_sensitive_variables = False
        is_singleton = True

    def run(self):  # pylint: disable=arguments-differ
        result = purge_expired_and_orphaned_locks()
        self.logger.info(
            "Object Lock sweep complete: %d expired, %d orphaned locks purged (%d content types failed).",
            result["expired"],
            result["orphaned"],
            result["failed_content_types"],
        )
        return result
