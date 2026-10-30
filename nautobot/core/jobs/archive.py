from datetime import timedelta
import math

from django.db.models.signals import pre_delete
from django.utils import timezone

from nautobot.core.utils.config import get_settings_or_config
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.jobs import DryRunVar, IntegerVar, Job, MultiChoiceVar
from nautobot.extras.models import (
    ArchivedJobConsoleEntry,
    ArchivedJobLogEntry,
    ArchivedJobResult,
    ArchivedObjectChange,
    JobConsoleEntry,
    JobLogEntry,
    JobResult,
    ObjectChange,
)
from nautobot.extras.signals import _handle_deleted_object

name = "System Jobs"
JOB_NAME = "Archive Old Records"

# Archival order matters, used to determine what gets archived first to remove concerns about foreign key
# relationships when archiving
ARCHIVAL_ORDER = (
    "extras.objectchange",  # Independent
    # --------------------
    "extras.jobresult",  # Parent to JobConsoleEntry, Parent to JobLogEntry
)

# The records that can be archived are displayed in alphabetical order
# But `ARCHIVAL_ORDER` is the actual order that archival occurs in
ARCHIVAL_DISPLAY_ORDER = tuple(sorted(ARCHIVAL_ORDER))


# TODO: Ask if we want to gate this to super users/admins?
class ArchiveOldRecords(Job):
    """
    Move database records that are past specific age threshold into a warm table.

    This job helps migrate old database records to a separate table in order to help optimize performance of database queries.
    """

    selected_models_to_archive = MultiChoiceVar(
        choices=[(label, label) for label in ARCHIVAL_DISPLAY_ORDER],
        description="The models whose records are archived.",
        label="Models To Archive",
        required=True,
    )
    archive_age_threshold = IntegerVar(
        description="Records older than this many days are archived.",
        label="Archive Age Threshold",
        default=get_settings_or_config("ARCHIVE_MODEL_DEFAULT_AGE_THRESHOLD"),
        min_value=1,
        required=True,
    )
    archive_batch_size = IntegerVar(
        description=(
            "Number of records to move for each batch in the archival step. Leave empty to use the ARCHIVE_MODEL_DEFAULT_BATCH_SIZE setting. Lower it if the archival task runs out of memory."
        ),
        label="Archive Batch Size",
        default=get_settings_or_config("ARCHIVE_MODEL_DEFAULT_BATCH_SIZE"),
        min_value=1,
        required=False,
    )
    dryrun = DryRunVar(description="Report what would be archived without moving anything.")

    class Meta:
        name = JOB_NAME
        description = "This job will migrate the specified Model records to a separate table in order to enhance performance of the existing database."
        has_sensitive_variables = False
        dryrun_default = True

    def run(  # pylint: disable=arguments-differ
        self,
        *,
        selected_models_to_archive=None,
        archive_age_threshold=None,
        archive_batch_size=None,
        dryrun=True,
    ):
        selected_models = set(selected_models_to_archive or ARCHIVAL_ORDER)
        dependency_sorted_models_to_archive = [
            model_label for model_label in ARCHIVAL_ORDER if model_label in selected_models
        ]

        archive_age_threshold = archive_age_threshold or get_settings_or_config("ARCHIVE_MODEL_DEFAULT_AGE_THRESHOLD")
        archive_batch_size = archive_batch_size or get_settings_or_config("ARCHIVE_MODEL_DEFAULT_BATCH_SIZE")

        # Calculated once so that every model is archived against the same instant
        archive_model_threshold_timestamp = timezone.now() - timedelta(days=archive_age_threshold)

        # Nautobot has a global `_handle_deleted_object` registered to the pre_delete signal
        # We disable it here because deletions that occur with an archival job do not need it
        # resulting in better performance
        self.logger.debug("Temporarily disconnecting the _handle_deleted_object signal for performance")
        pre_delete.disconnect(_handle_deleted_object)
        try:
            for model_label in dependency_sorted_models_to_archive:
                if model_label == "extras.objectchange":
                    self._archive_object_changes(archive_model_threshold_timestamp, archive_batch_size, dryrun)
                elif model_label == "extras.jobresult":
                    self._archive_job_results(archive_model_threshold_timestamp, archive_batch_size, dryrun)
        finally:
            self.logger.debug("Re-connecting the _handle_deleted_object signal")
            pre_delete.connect(_handle_deleted_object)

    # --------------------------------------------------------------------------
    # Object Change
    # --------------------------------------------------------------------------
    def _archive_object_changes(self, threshold_timestamp, batch_size, dryrun):
        """
        Archive `ObjectChange` records older than `threshold_timestamp`, one batch at a time.

        No other archivable model has a foreign key to `ObjectChange`, so it can be archived on its own, in any
        order relative to the other models.

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

            try:
                current_archived_object_change_count = self._process_archive_object_change_batch(object_change_batch)
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
                "Batch %d: archived %d ObjectChange records",
                current_batch,
                current_archived_object_change_count,
            )

            current_batch += 1

        self.logger.success(
            "Archived %d ObjectChange records across %d batches.",
            total_archived_object_change_count,
            current_batch,
        )
        return total_archived_object_change_count

    def _process_archive_object_change_batch(self, object_change_batch):
        """
        Copy one batch into the archive, then delete the live rows it covers.

        Copy before delete, and not inside one transaction: the archive tables are headed for a database
        of their own, where a single transaction cannot span both sides. A run that dies between the two
        leaves the record in both places, which the next run resolves, because the archived copy keeps the
        primary key it had live. Deleting first would lose the record outright.

        Args:
            object_change_batch (list of ObjectChange): Live `ObjectChange` records to archive.

        Returns:
            (int): Records archived and removed from the live table.
        """
        object_changes_to_archive_pks = [object_change.pk for object_change in object_change_batch]
        new_archived_object_changes = [
            ArchivedObjectChange.from_object_change(object_change) for object_change in object_change_batch
        ]

        # Only the `id` field is unique, because it is the primary key. Rather than explicitly list
        # every field to overwrite, we use the metadata fields to determine it. ObjectChange and
        # ArchivedObjectChange are both not modified after write, so overwriting is performed in
        # order to guarantee full copies in cases where a previous copy failed.
        archived_object_change_update_fields = [
            field.name for field in ArchivedObjectChange._meta.fields if field.name != "id"
        ]

        ArchivedObjectChange.objects.bulk_create(
            new_archived_object_changes,
            update_conflicts=True,
            update_fields=archived_object_change_update_fields,
            unique_fields=["id"],
        )

        deleted_count, _ = ObjectChange.objects.filter(pk__in=object_changes_to_archive_pks).delete()
        self.logger.debug(
            "Archived %d and deleted %d live ObjectChange rows", len(object_changes_to_archive_pks), deleted_count
        )
        return len(object_changes_to_archive_pks)

    # --------------------------------------------------------------------------
    # Job Results
    # --------------------------------------------------------------------------
    def _archive_job_results(self, threshold_timestamp, batch_size, dryrun):
        """
        Archive `JobResult` records older than `threshold_timestamp`, together with their log and console
        entries, one batch at a time.

        `ArchivedJobResult` is a dependency (ForeignKey) of `ArchivedJobLogEntry` and `ArchivedJobConsoleEntry`.
        This means that `ArchivedJobResult` must be archived first in order for the `ArchivedJobLogEntry`
        and `ArchivedJobConsoleEntry` references to be valid.

        `JobResult` status is a wrapper around Celery states. Celery indicates lifecycle complete states as `READY_STATES`.
        `READY_STATES` is comprised of `SUCCESS`, `FAILURE`, and `REVOKED`.
        Only lifecycle complete `JobResult`s will be archived.
        Subsequently `JobResult` time for determining archival is selected by `date_done`

        Args:
            threshold_timestamp (datetime): Job results that finished before this are archived.
            batch_size (int): Job results to move per batch, and the chunk size used for their children.
            dryrun (bool): Report what would move without moving anything.

        Returns:
            (int): Job results archived, or on a dry run the count a real run would archive.
        """
        # Only job results that are done can be archived
        job_results_to_archive = JobResult.objects.filter(
            date_done__lt=threshold_timestamp,
            status__in=JobResultStatusChoices.READY_STATES,
            # TODO: Add optional flag to include files, otherwise default to leaving the JobResult unarchived
            files__isnull=True,
        ).order_by("date_done")

        job_result_count = job_results_to_archive.count()

        if not job_result_count:
            self.logger.info("No JobResult records older than %s", threshold_timestamp)
            return 0

        total_batch_count = math.ceil(job_result_count / batch_size)

        if dryrun:
            self.logger.warning(
                "%s Dry Run: %d JobResult records in batches of %d for a total of %d operations would be archived.",
                JOB_NAME,
                job_result_count,
                batch_size,
                total_batch_count,
            )
            return job_result_count

        total_archived_job_result_count = 0
        current_batch = 0

        while current_batch < total_batch_count:
            job_result_batch = list(job_results_to_archive[:batch_size])
            if not job_result_batch:
                break

            try:
                current_archived_job_result_count = self._process_archive_job_result_batch(job_result_batch, batch_size)
            except Exception as exception:
                self.fail(
                    "Stopping at batch %d: %s. Archived %d of %d JobResult records before stopping.",
                    current_batch,
                    exception,
                    total_archived_job_result_count,
                    job_result_count,
                )
                return total_archived_job_result_count

            total_archived_job_result_count += current_archived_job_result_count
            self.logger.info(
                "Batch %d: archived %d JobResult records",
                current_batch,
                current_archived_job_result_count,
            )

            current_batch += 1

        self.logger.success(
            "Archived %d JobResult records across %d batches.",
            total_archived_job_result_count,
            current_batch,
        )

        return total_archived_job_result_count

    def _process_archive_job_result_batch(self, job_result_batch, batch_size):
        """
        Copy one batch of job results and their children into the archive, then delete the live parents.

        The order is forced by the schema. An archived child's foreign key needs its archived parent to
        exist already, and deleting a live parent cascades its live children away before they can be read.
        So parents are copied, then children, then the live parents are deleted and the cascade clears the
        live children along with them.

        Args:
            job_result_batch (list of JobResult): Live `JobResult` records to archive.
            batch_size (int): Chunk size for copying the children, which are unbounded per parent.

        Returns:
            (int): Job results archived and removed from the live table.
        """
        job_result_pks = [job_result.pk for job_result in job_result_batch]

        archived_job_result_update_fields = [
            field.name for field in ArchivedJobResult._meta.fields if field.name != "id"
        ]
        ArchivedJobResult.objects.bulk_create(
            [ArchivedJobResult.from_job_result(job_result) for job_result in job_result_batch],
            update_conflicts=True,
            update_fields=archived_job_result_update_fields,
            unique_fields=["id"],
        )

        archived_job_log_entry_count = self._archive_job_result_child_records(
            JobLogEntry.objects.filter(job_result_id__in=job_result_pks),
            ArchivedJobLogEntry,
            ArchivedJobLogEntry.from_job_log_entry,
            batch_size,
        )
        archived_job_console_entry_count = self._archive_job_result_child_records(
            JobConsoleEntry.objects.filter(job_result_id__in=job_result_pks),
            ArchivedJobConsoleEntry,
            ArchivedJobConsoleEntry.from_job_console_entry,
            batch_size,
        )

        deleted_count, _ = JobResult.objects.filter(pk__in=job_result_pks).delete()
        self.logger.debug(
            "Archived %d job results with %d log entries and %d console entries, and deleted %d live rows",
            len(job_result_pks),
            archived_job_log_entry_count,
            archived_job_console_entry_count,
            deleted_count,
        )
        return len(job_result_pks)

    def _archive_job_result_child_records(
        self, child_records, archived_child_model, build_archived_child_record, chunk_size
    ):
        """
        Copy a job result's child records into the archive, a bounded chunk at a time.

        Chunked separately from the parent batch because the children are unbounded: a single job result
        can carry tens of thousands of log entries, so a batch of parents says nothing about how many
        children come with it.

        Args:
            child_records (QuerySet): Live child records belonging to the batch's job results.
            archived_child_model (Model): The archived model the records are copied into.
            build_archived_child_record (callable): Maps one live record to an unsaved archived record.
            chunk_size (int): Records to hold in memory and insert at a time.

        Returns:
            (int): Child records copied into the archive.
        """
        archived_child_update_fields = [field.name for field in archived_child_model._meta.fields if field.name != "id"]
        archived_child_record_count = 0
        archived_child_record_chunk = []

        for child_record in child_records.iterator(chunk_size=chunk_size):
            archived_child_record_chunk.append(build_archived_child_record(child_record))
            if len(archived_child_record_chunk) >= chunk_size:
                archived_child_model.objects.bulk_create(
                    archived_child_record_chunk,
                    update_conflicts=True,
                    update_fields=archived_child_update_fields,
                    unique_fields=["id"],
                )
                archived_child_record_count += len(archived_child_record_chunk)
                archived_child_record_chunk = []

        if archived_child_record_chunk:
            archived_child_model.objects.bulk_create(
                archived_child_record_chunk,
                update_conflicts=True,
                update_fields=archived_child_update_fields,
                unique_fields=["id"],
            )
            archived_child_record_count += len(archived_child_record_chunk)

        return archived_child_record_count
