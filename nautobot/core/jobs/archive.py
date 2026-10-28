from datetime import timedelta
import math

from django.db.models.signals import pre_delete
from django.utils import timezone

from nautobot.core.utils.config import get_settings_or_config
from nautobot.extras.jobs import DryRunVar, IntegerVar, Job, MultiChoiceVar
from nautobot.extras.models import ArchivedObjectChange, ObjectChange
from nautobot.extras.signals import _handle_deleted_object

name = "System Jobs"
JOB_NAME = "Archive Old Records"

# Archival order matters, used to determine what gets archived first to remove issues with cascading deletions
ARCHIVAL_ORDER = (
    "extras.objectchange",  # Independent
    # --------------------
    "extras.jobresult",  # Parent to JobConsoleEntry, Parent to JobLogEntry
    "extras.joblogentry",  # Dependent on JobResult
    "extras.jobconsoleentry",  # Dependent on JobResult
)
# TODO: Ask about FileProxy which is dependent on JobResult

# The records that can be archived are displayed in alphabetical order
# But `ARCHIVAL_ORDER` is the actual order that archival occurs in
ARCHIVAL_DISPLAY_ORDER = tuple(sorted(ARCHIVAL_ORDER))


# TODO: This really isn't ChangeLogRotation, It's ObjectChanges + JobResult + JobConsoleEntry/JobLogEntry
#       Should either separate these into different jobs or rename this to something like `ArchiveOldRecords` (naming is hard)
class ArchiveOldRecords(Job):
    """
    Move database records that are past specific age threshold into a warm database and table.

    This job helps migrate old database records to a separate database and table in order to help optimize performance of database queries.
    """

    ui_selected_models_to_archive = MultiChoiceVar(
        choices=[(label, label) for label in ARCHIVAL_DISPLAY_ORDER],
        description="The Database records archive. Leave empty to archive all of them.",
        label="Models To Archive",
        required=False,
    )
    ui_archive_age_threshold = IntegerVar(
        description=(
            "Records older than this age are selected to be archived. Leave empty to use the ARCHIVE_MODEL_DEFAULT_AGE_THRESHOLD setting."
        ),
        label="Archive Age Threshold",
        min_value=1,
        required=False,
    )
    ui_archive_batch_size = IntegerVar(
        description=(
            "Records to move per each archival step. Leave empty to use the ARCHIVE_MODEL_DEFAULT_BATCH_SIZE setting. Lower it if the archival task runs out of memory."
        ),
        label="Archive Batch Size",
        min_value=1,
        required=False,
    )
    dryrun = DryRunVar(description="Report what would be archived without moving anything.")

    class Meta:
        name = JOB_NAME
        description = "This job will migrate the specified Model records to a separate database and table in order to enhance performance of the existing database."
        has_sensitive_variables = False
        dryrun_default = True

    def run(  # pylint: disable=arguments-differ
        self,
        *,
        ui_selected_models_to_archive=None,
        ui_archive_age_threshold=None,
        ui_archive_batch_size=None,
        dryrun=True,
    ):
        selected_models = set(ui_selected_models_to_archive or ARCHIVAL_ORDER)
        dependency_sorted_models_to_archive = [
            model_label for model_label in ARCHIVAL_ORDER if model_label in selected_models
        ]

        archive_model_age_threshold = ui_archive_age_threshold or get_settings_or_config(
            "ARCHIVE_MODEL_DEFAULT_AGE_THRESHOLD"
        )
        archive_model_batch_size = ui_archive_batch_size or get_settings_or_config("ARCHIVE_MODEL_DEFAULT_BATCH_SIZE")

        # Calculated once so that every model is archived against the same instant
        archive_model_threshold_timestamp = timezone.now() - timedelta(days=archive_model_age_threshold)

        # Nautobot has a global `_handle_deleted_object` registerd to the pre_delete signal
        # We disable it here because deletions that occur with an archival job do not need it. Also helps with performance
        self.logger.debug("Temporarily disconnecting the _handle_deleted_object signal for performance")
        pre_delete.disconnect(_handle_deleted_object)
        try:
            for model_label in dependency_sorted_models_to_archive:
                if model_label == "extras.objectchange":
                    self._archive_object_changes(archive_model_threshold_timestamp, archive_model_batch_size, dryrun)
                # TODO: extras.jobresult, which carries its log and console entries with it.
        finally:
            self.logger.debug("Re-connecting the _handle_deleted_object signal")
            pre_delete.connect(_handle_deleted_object)

    def _archive_object_changes(self, threshold_timestamp, batch_size, dryrun):
        """
        Archive `ObjectChange` records older than `threshold_timestamp`, one batch at a time.

        `ObjectChange` has no relations in either direction, so it is archived on its own and carries no
        ordering constraints.

        Args:
            threshold_timestamp (datetime): Records older than this are archived.
            batch_size (int): Records to move per batch.
            dryrun (bool): Report what would move without moving anything.

        Returns:
            (int): Records archived, or on a dry run the count a real run would archive.
        """
        object_changes_to_archive = ObjectChange.objects.filter(time__lt=threshold_timestamp).order_by("time")

        object_change_count = object_changes_to_archive.count()

        if not object_change_count:
            self.logger.info("No ObjectChange records older than %s", threshold_timestamp)
            return 0

        total_batch_count = math.ceil(object_change_count / batch_size)

        if dryrun:
            self.logger.warning(
                "%s Dry Run: %d ObjectChange records in batches of %d for a total of %d operations would be archived.",
                JOB_NAME,
                object_change_count,
                batch_size,
                total_batch_count,
            )
            return object_change_count

        total_archived_object_change_count = 0
        current_batch = 0

        while current_batch < total_batch_count:
            # Re-sliced rather than paged with an offset: each batch's rows are deleted before the next
            # slice is taken, so the front of the queryset is always the next batch. An offset would skip
            # records as the table shrinks underneath it.
            object_change_batch = list(object_changes_to_archive[:batch_size])
            if not object_change_batch:
                break

            current_batch += 1

            try:
                current_archived_object_change_count = self._archive_object_change_batch(object_change_batch)
            except Exception as exception:
                self.fail(
                    "Stopping at batch %d: %s. Archived %d of %d ObjectChange records before stopping.",
                    current_batch,
                    exception,
                    total_archived_object_change_count,
                    object_change_count,
                )
                return total_archived_object_change_count

            total_archived_object_change_count += current_archived_object_change_count
            self.logger.info(
                "Batch %d: archived %d ObjectChange records", current_batch, current_archived_object_change_count
            )

        self.logger.success(
            "Archived %d ObjectChange records across %d batches",
            total_archived_object_change_count,
            current_batch,
        )
        return total_archived_object_change_count

    def _archive_object_change_batch(self, object_change_batch):
        """
        Copy one batch into the archive, confirm it landed, then delete the live rows it covers.

        Copy before delete, and not inside one transaction: the archive tables are headed for a database
        of their own, where a single transaction cannot span both sides. A run that dies between the two
        leaves the record in both places, which the next run resolves, because the archived copy keeps the
        primary key it had live. Deleting first would lose the record outright.

        Args:
            object_change_batch (list): Live `ObjectChange` records to archive.

        Returns:
            (int): Records archived and removed from the live table.

        Raises:
            RuntimeError: If any record in the batch did not reach the archive. The live rows are left in
                place, so a later run retries them.
        """
        object_changes_to_archive_pks = [object_change.pk for object_change in object_change_batch]

        # `ignore_conflicts` is what makes a re-run harmless: an archived record keeps the primary key it
        # had live, so re-archiving one that is already there conflicts rather than duplicating it.
        ArchivedObjectChange.objects.bulk_create(
            [ArchivedObjectChange.from_source(object_change) for object_change in object_change_batch],
            ignore_conflicts=True,
        )

        # The write above is silent about rows it skipped, so ask the archive what it has
        archived_object_change_pks = list(
            ArchivedObjectChange.objects.filter(pk__in=object_changes_to_archive_pks).values_list("pk", flat=True)
        )

        if len(archived_object_change_pks) != len(object_changes_to_archive_pks):
            raise RuntimeError(
                f"{len(object_changes_to_archive_pks) - len(archived_object_change_pks)} of {len(object_changes_to_archive_pks)} "
                "ObjectChange records did not reach the archive"
            )

        deleted_count, _ = ObjectChange.objects.filter(pk__in=archived_object_change_pks).delete()
        self.logger.debug(
            "Archived %d and deleted %d live ObjectChange rows", len(archived_object_change_pks), deleted_count
        )
        return len(archived_object_change_pks)
