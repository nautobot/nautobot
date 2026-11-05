from datetime import timedelta
import math

from django.db import connection, transaction
from django.db.models.signals import pre_delete
from django.utils import timezone

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

OBJECT_CHANGE_LABEL = "extras.objectchange"
JOB_RESULT_LABEL = "extras.jobresult"
JOB_LOG_ENTRY_LABEL = "extras.joblogentry"
JOB_CONSOLE_ENTRY_LABEL = "extras.jobconsoleentry"

# Archival order matters, used to determine what gets archived first to remove concerns about foreign key
# relationships when archiving
ARCHIVAL_ORDER = (
    OBJECT_CHANGE_LABEL,  # Independent
    # --------------------
    JOB_RESULT_LABEL,  # Parent to JobConsoleEntry, Parent to JobLogEntry
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
        default=365,
        min_value=1,
        required=True,
    )
    archive_batch_size = IntegerVar(
        description=(
            "Number of records to move for each batch in the archival step. "
            "Lower it if the archival task runs out of memory."
        ),
        label="Archive Batch Size",
        default=1000,
        min_value=1,
        required=True,
    )
    dryrun = DryRunVar(description="Report what would be archived without moving anything.")

    class Meta:
        name = JOB_NAME
        description = "This job will migrate the specified Model records to a separate table in order to enhance performance of the existing database."
        has_sensitive_variables = False
        dryrun_default = True
        soft_time_limit = 600
        time_limit = 660

    def run(  # pylint: disable=arguments-differ
        self,
        *,
        selected_models_to_archive=None,
        archive_age_threshold=None,
        archive_batch_size=None,
        dryrun=True,
    ):
        """
        Archive the selected models' records that are older than the age threshold.

        Returns:
            (dict): Archived record count keyed by model label, for example
                `{"extras.objectchange": 12, "extras.jobresult": 3, "extras.joblogentry": 40,
                "extras.jobconsoleentry": 7}`. Every archivable model is present, so a model that this run
                was not asked to archive reports 0 rather than being absent.
        """
        selected_models = set(selected_models_to_archive or ARCHIVAL_ORDER)

        archived_record_counts = {
            OBJECT_CHANGE_LABEL: 0,
            JOB_RESULT_LABEL: 0,
            JOB_LOG_ENTRY_LABEL: 0,
            JOB_CONSOLE_ENTRY_LABEL: 0,
        }

        # Calculated once so that every model is archived against the same instant
        archive_model_threshold_timestamp = timezone.now() - timedelta(days=archive_age_threshold)

        # Nautobot has a global `_handle_deleted_object` registered to the pre_delete signal
        # We disable it here because deletions that occur with an archival job do not need it
        # resulting in better performance
        self.logger.debug("Temporarily disconnecting the `_handle_deleted_object` signal for performance")
        pre_delete.disconnect(_handle_deleted_object)
        try:
            if OBJECT_CHANGE_LABEL in selected_models:
                archived_object_change_counts = self._archive_object_changes(
                    archive_model_threshold_timestamp, archive_batch_size, dryrun
                )
                archived_record_counts.update(archived_object_change_counts)
            if JOB_RESULT_LABEL in selected_models:
                archived_job_result_counts = self._archive_job_results(
                    archive_model_threshold_timestamp, archive_batch_size, dryrun
                )
                archived_record_counts.update(archived_job_result_counts)
        finally:
            self.logger.debug("Re-connecting the _handle_deleted_object signal")
            pre_delete.connect(_handle_deleted_object)

        return archived_record_counts

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
            (dict): Archived record count keyed by model label, or on a dry run the count a real run
                would archive. Always carries the `extras.objectchange` key.
        """
        object_changes_to_archive = ObjectChange.objects.filter(time__lt=threshold_timestamp).order_by("time")

        if dryrun:
            object_change_count = object_changes_to_archive.count()
            total_batch_count = math.ceil(object_change_count / batch_size)
            self.logger.warning(
                "%s Dry Run: %d ObjectChange records in batches of %d for a total of %d operations would be archived.",
                JOB_NAME,
                object_change_count,
                batch_size,
                total_batch_count,
            )
            return {OBJECT_CHANGE_LABEL: object_change_count}

        total_archived_object_change_count = 0
        current_batch = 0

        while True:
            object_change_batch = list(object_changes_to_archive[:batch_size])
            if not object_change_batch:
                break

            try:
                current_archived_object_change_count = self._process_archive_object_change_batch(object_change_batch)
            except Exception as exception:
                self.fail(
                    "Stopping at batch %d: %s. Archived %d ObjectChange records before stopping.",
                    current_batch,
                    exception,
                    total_archived_object_change_count,
                )
                return {OBJECT_CHANGE_LABEL: total_archived_object_change_count}

            total_archived_object_change_count += current_archived_object_change_count
            self.logger.info(
                "Batch %d: archived %d ObjectChange records",
                current_batch,
                current_archived_object_change_count,
            )

            current_batch += 1

        if not total_archived_object_change_count:
            self.logger.info("No ObjectChange records older than %s", threshold_timestamp)
            return {OBJECT_CHANGE_LABEL: 0}

        self.logger.success(
            "Archived %d ObjectChange records across %d batches.",
            total_archived_object_change_count,
            current_batch,
        )

        return {OBJECT_CHANGE_LABEL: total_archived_object_change_count}

    def _process_archive_object_change_batch(self, object_change_batch):
        """
        Copy one batch into the archive and delete the live rows it covers, both in one transaction.

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

        with transaction.atomic():
            ArchivedObjectChange.objects.bulk_create(
                new_archived_object_changes,
                update_conflicts=True,
                update_fields=archived_object_change_update_fields,
                # PostgreSQL needs the conflict column named. MySQL's ON DUPLICATE KEY UPDATE cannot name one,
                # so unique_fields must be empty there.
                unique_fields=["id"] if connection.features.supports_update_conflicts_with_target else [],
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
            (dict): Archived record counts keyed by model label, or on a dry run the counts a real run
                would archive. Always carries the `extras.jobresult`, `extras.joblogentry` and
                `extras.jobconsoleentry` keys.
        """
        # Only job results that are done can be archived
        job_results_to_archive = (
            JobResult.objects.filter(
                date_done__lt=threshold_timestamp,
                status__in=JobResultStatusChoices.READY_STATES,
                # TODO: Add optional flag to include files, otherwise default to leaving the JobResult unarchived
                files__isnull=True,
            )
            .select_related("user")
            .order_by("date_done")
        )

        if dryrun:
            job_result_count = job_results_to_archive.count()
            # The children are counted too, so that a dry run names the same models a real run moves
            # instead of reporting zero for records it would in fact archive.
            job_log_entry_count = JobLogEntry.objects.filter(job_result__in=job_results_to_archive).count()
            job_console_entry_count = JobConsoleEntry.objects.filter(job_result__in=job_results_to_archive).count()
            total_batch_count = math.ceil(job_result_count / batch_size)
            self.logger.warning(
                "%s Dry Run: %d JobResult records in batches of %d for a total of %d operations would be archived, "
                "along with %d JobLogEntry and %d JobConsoleEntry records.",
                JOB_NAME,
                job_result_count,
                batch_size,
                total_batch_count,
                job_log_entry_count,
                job_console_entry_count,
            )
            return {
                JOB_RESULT_LABEL: job_result_count,
                JOB_LOG_ENTRY_LABEL: job_log_entry_count,
                JOB_CONSOLE_ENTRY_LABEL: job_console_entry_count,
            }

        archived_job_result_counts = {
            JOB_RESULT_LABEL: 0,
            JOB_LOG_ENTRY_LABEL: 0,
            JOB_CONSOLE_ENTRY_LABEL: 0,
        }
        current_batch = 0

        while True:
            job_result_batch = list(job_results_to_archive[:batch_size])
            if not job_result_batch:
                break

            try:
                current_batch_counts = self._process_archive_job_result_batch(job_result_batch, batch_size)
            except Exception as exception:
                self.fail(
                    "Stopping at batch %d: %s. Archived %d JobResult records before stopping.",
                    current_batch,
                    exception,
                    archived_job_result_counts[JOB_RESULT_LABEL],
                )
                return archived_job_result_counts

            archived_job_result_counts[JOB_RESULT_LABEL] += current_batch_counts[JOB_RESULT_LABEL]
            archived_job_result_counts[JOB_LOG_ENTRY_LABEL] += current_batch_counts[JOB_LOG_ENTRY_LABEL]
            archived_job_result_counts[JOB_CONSOLE_ENTRY_LABEL] += current_batch_counts[JOB_CONSOLE_ENTRY_LABEL]

            self.logger.info(
                "Batch %d: archived %d JobResult records",
                current_batch,
                current_batch_counts[JOB_RESULT_LABEL],
            )

            current_batch += 1

        if not archived_job_result_counts[JOB_RESULT_LABEL]:
            self.logger.info("No JobResult records older than %s", threshold_timestamp)
            return archived_job_result_counts

        self.logger.success(
            "Archived %d JobResult records across %d batches.",
            archived_job_result_counts[JOB_RESULT_LABEL],
            current_batch,
        )

        return archived_job_result_counts

    def _process_archive_job_result_batch(self, job_result_batch, batch_size):
        """
        Copy one batch of job results and their children into the archive, then delete the live parents.

        The order is forced by the schema. An archived child's foreign key needs its archived parent to
        exist already, so the parents are copied first. The children are then moved a chunk at a time,
        and the live parents are deleted last, once their children are already gone.

        No step spans the whole batch. The parent copy, each chunk of children, and the parent delete
        each commit on their own, which is what makes an interrupted run resumable: whatever was archived
        has already left the live table, so the next run starts from the first chunk that did not make it
        rather than working through the job result again. Re-copying a parent costs nothing, because the
        archived copy keeps the primary key it had live and is overwritten rather than duplicated.

        The children are chunked because one job result can carry tens of thousands of entries, so the
        parent batch size says nothing about how much work a batch is. Committing per chunk bounds the
        transaction as well as the memory.

        Args:
            job_result_batch (list of JobResult): Live `JobResult` records to archive.
            batch_size (int): Chunk size for copying the children, which are unbounded per parent.

        Returns:
            (dict): Archived record counts for this batch, keyed by model label.
        """
        job_result_pks = [job_result.pk for job_result in job_result_batch]
        job_result_pks_count = len(job_result_pks)

        archived_job_result_update_fields = [
            field.name for field in ArchivedJobResult._meta.fields if field.name != "id"
        ]
        new_archived_job_results = [ArchivedJobResult.from_job_result(job_result) for job_result in job_result_batch]

        # Copy the parents first so that the archived children's foreign keys resolve. Each step commits on its own.
        ArchivedJobResult.objects.bulk_create(
            new_archived_job_results,
            update_conflicts=True,
            update_fields=archived_job_result_update_fields,
            # Postgres requires a named conflict target; MySQL has no slot for one and rejects it.
            unique_fields=["id"] if connection.features.supports_update_conflicts_with_target else [],
        )

        archived_job_log_entry_count = self._archive_job_log_entry(job_result_pks, batch_size)
        archived_job_console_entry_count = self._archive_job_console_entry(job_result_pks, batch_size)

        deleted_count, _ = JobResult.objects.filter(pk__in=job_result_pks).delete()

        self.logger.debug(
            "Archived %d job results with %d log entries and %d console entries, and deleted %d live rows",
            len(job_result_pks),
            archived_job_log_entry_count,
            archived_job_console_entry_count,
            deleted_count,
        )

        archived_job_result_count = {
            JOB_RESULT_LABEL: job_result_pks_count,
            JOB_LOG_ENTRY_LABEL: archived_job_log_entry_count,
            JOB_CONSOLE_ENTRY_LABEL: archived_job_console_entry_count,
        }

        return archival_result_count

    # --------------------------------------------------------------------------
    # Job Log Entry
    # --------------------------------------------------------------------------
    def _archive_job_log_entry(self, job_result_pks, batch_size):
        """
        Move the job results' `JobLogEntry` records into the archive, a bounded chunk at a time.

        Chunked separately from the parent batch because the log entries are unbounded: a single job
        result can carry tens of thousands of them, so a batch of parents says nothing about how many
        log entries come with it.

        Each chunk is copied and deleted in one transaction, which commits before the next chunk is read.
        If a run stops part way through, the chunks that it finished are already in the archive and no
        longer in the live table, so the next run reads only the log entries that are still live instead
        of processing entries that it has already moved.

        Args:
            job_result_pks (list of uuid.UUID): Primary keys of the job results whose log entries are archived.
            batch_size (int): Number of log entries to load into memory, copy into the archive, and delete per chunk.

        Returns:
            (int): Job log entries archived and removed from the live table.
        """
        archived_job_log_entry_update_fields = [
            field.name for field in ArchivedJobLogEntry._meta.fields if field.name != "id"
        ]
        job_log_entries = JobLogEntry.objects.filter(job_result_id__in=job_result_pks)

        archived_job_log_entry_count = 0

        while True:
            job_log_entry_chunk = list(job_log_entries[:batch_size])
            if not job_log_entry_chunk:
                break

            with transaction.atomic():
                ArchivedJobLogEntry.objects.bulk_create(
                    [ArchivedJobLogEntry.from_job_log_entry(job_log_entry) for job_log_entry in job_log_entry_chunk],
                    update_conflicts=True,
                    update_fields=archived_job_log_entry_update_fields,
                    # Postgres requires a named conflict target; MySQL has no slot for one and rejects it.
                    unique_fields=["id"] if connection.features.supports_update_conflicts_with_target else [],
                )
                JobLogEntry.objects.filter(pk__in=[job_log_entry.pk for job_log_entry in job_log_entry_chunk]).delete()

            archived_job_log_entry_count += len(job_log_entry_chunk)

        return archived_job_log_entry_count

    # --------------------------------------------------------------------------
    # Job Console Entry
    # --------------------------------------------------------------------------
    def _archive_job_console_entry(self, job_result_pks, batch_size):
        """
        Move the job results' `JobConsoleEntry` records into the archive, a bounded chunk at a time.

        Chunked separately from the parent batch because the console entries are unbounded: a single job
        result can carry tens of thousands of them, so a batch of parents says nothing about how many
        console entries come with it.

        Each chunk is copied and deleted in one transaction, which commits before the next chunk is read.
        If a run stops part way through, the chunks that it finished are already in the archive and no
        longer in the live table, so the next run reads only the console entries that are still live
        instead of processing entries that it has already moved.

        Args:
            job_result_pks (list of uuid.UUID): Primary keys of the job results whose console entries are archived.
            batch_size (int): Records to hold in memory, insert and delete at a time.

        Returns:
            (int): Job console entries archived and removed from the live table.
        """
        archived_job_console_entry_update_fields = [
            field.name for field in ArchivedJobConsoleEntry._meta.fields if field.name != "id"
        ]
        job_console_entries = JobConsoleEntry.objects.filter(job_result_id__in=job_result_pks)

        archived_job_console_entry_count = 0

        while True:
            job_console_entry_chunk = list(job_console_entries[:batch_size])
            if not job_console_entry_chunk:
                break

            with transaction.atomic():
                ArchivedJobConsoleEntry.objects.bulk_create(
                    [
                        ArchivedJobConsoleEntry.from_job_console_entry(job_console_entry)
                        for job_console_entry in job_console_entry_chunk
                    ],
                    update_conflicts=True,
                    update_fields=archived_job_console_entry_update_fields,
                    # Postgres requires a named conflict target; MySQL has no slot for one and rejects it.
                    unique_fields=["id"] if connection.features.supports_update_conflicts_with_target else [],
                )
                JobConsoleEntry.objects.filter(
                    pk__in=[job_console_entry.pk for job_console_entry in job_console_entry_chunk]
                ).delete()

            archived_job_console_entry_count += len(job_console_entry_chunk)

        return archived_job_console_entry_count
