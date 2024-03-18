from datetime import timedelta

from django.db.models.signals import post_delete, pre_delete
from django.utils import timezone

from nautobot.core.utils.config import get_settings_or_config
from nautobot.extras.jobs import IntegerVar, Job
from nautobot.extras.models import ObjectChange
from nautobot.extras.signals import _handle_deleted_object, invalidate_lru_cache

name = "System Jobs"


class ObjectChangeCleanup(Job):
    """
    System job to clean up ObjectChange records older than a given age.
    """

    max_age = IntegerVar(
        description=(
            "Maximum age of ObjectChange records to retain, in days. "
            "Leave empty to use the CHANGELOG_RETENTION setting as the maximum."
        ),
        label="Max Age",
        min_value=0,
        required=False,
    )

    class Meta:
        name = "Cleanup of ObjectChange records"
        has_sensitive_variables = False

    def run(self, max_age=None):
        if max_age in (None, ""):
            max_age = get_settings_or_config("CHANGELOG_RETENTION")
            if max_age == 0:
                self.logger.warning(
                    "CHANGELOG_RETENTION setting is set to zero, disabling this Job. "
                    "If you wish to use this Job to delete ObjectChange history, you must specify a `max_age` value."
                )
                return 0

        # Bulk delete goes much faster if Django doesn't have signals to process.
        # Temporarily detach the ones we *know* to be irrelevant.
        self.logger.debug("Temporarily disconnecting some signals for performance")
        pre_delete.disconnect(_handle_deleted_object)
        post_delete.disconnect(invalidate_lru_cache)

        try:
            self.logger.info("Deleting all ObjectChange records older than %d days", max_age)
            cutoff = timezone.now() - timedelta(days=max_age)
            deleted_count, _ = ObjectChange.objects.filter(time__lt=cutoff).delete()
            self.logger.info("Deleted %d ObjectChange records", deleted_count)
            return deleted_count
        finally:
            # Be sure to clean up after ourselves!
            self.logger.debug("Re-connecting signals")
            pre_delete.connect(_handle_deleted_object)
            post_delete.connect(invalidate_lru_cache)
