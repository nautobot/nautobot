from datetime import timedelta
import logging
import math

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import DO_NOTHING, PROTECT, Q, RESTRICT
from django.db.models.signals import pre_delete
from django.utils import timezone

from nautobot.core.utils.config import get_settings_or_config
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.jobs import BooleanVar, DryRunVar, IntegerVar, Job, MultiChoiceVar
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

logger = logging.getLogger(__name__)

name = "System Jobs"
JOB_NAME = "Archive Old Records"

# Read from `_meta.label` rather than written out, so that they cannot drift from the model and so that
# one spelling serves every use: the choices a run is given, the keys of the counts `run()` returns, and
# the keys Django hands back from `QuerySet.delete()`. The CamelCase form is also what `LogsCleanup`'s
# `CleanupTypes` uses, so both system jobs name these models the same way.
OBJECT_CHANGE_LABEL = ObjectChange._meta.label
JOB_RESULT_LABEL = JobResult._meta.label
JOB_LOG_ENTRY_LABEL = JobLogEntry._meta.label
JOB_CONSOLE_ENTRY_LABEL = JobConsoleEntry._meta.label

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


def _iterate_records_by_timestamp(queryset, timestamp_field_name, batch_size):
    """
    A generator to navigate through a query set based on a specific timestamped field with an arbitrarily
    determined batch size.

    Assumes that caller provides a pre-filtered query set.

    Args:
        queryset (QuerySet): The records to slice.
        timestamp_field_name (str): Name of a field the records will be filtered, ordered and paged by.
        batch_size (int): Records per batch, and rows read per slice.

    Returns:
        (generator): Yields lists of up to `batch_size` records per batch.
    """
    # PK is necessary for when a slice is made where there are multiple elements that have the same timestamp.
    # This allows resuming iteration with the next slice at the correct point instead of needing to grab all
    # records at the same timestamp.
    ordered_queryset = queryset.order_by(timestamp_field_name, "pk")

    current_record_batch = list(ordered_queryset[:batch_size])

    while current_record_batch:
        last_record_in_batch = current_record_batch[-1]
        current_timestamp = getattr(last_record_in_batch, timestamp_field_name)

        yield current_record_batch

        # Get next batch
        newer_than_current_timestamp = Q(**{f"{timestamp_field_name}__gt": current_timestamp})
        same_timestamp_later_pk = Q(**{timestamp_field_name: current_timestamp}, pk__gt=last_record_in_batch.pk)
        records_after_current_batch = ordered_queryset.filter(newer_than_current_timestamp | same_timestamp_later_pk)
        next_batch_of_records = records_after_current_batch[:batch_size]
        current_record_batch = list(next_batch_of_records)


def _exclude_records_whose_relations_block_deletion(
    queryset, model, preapproved_models_that_can_be_deleted, force_cascade_delete
):
    """
    Filter a queryset to the records whose deletion does not take unrelated records with it.

    Args:
        queryset (QuerySet): The records being considered for archival.
        model (Model): The live model the queryset selects from.
        preapproved_models_that_can_be_deleted (tuple): These models are archived with the provided `model`, or are
            approved to be deleted alongside it, whatever their CASCADE, DO_NOTHING, PROTECT, or RESTRICT
            delete option.
        force_cascade_delete (bool): A user-override that allows the ability to force related records to be deleted.

    Returns:
        (QuerySet): The queryset that has been filtered down to the records that are safe to archive.
    """
    for related_object in model._meta.related_objects:
        if related_object.related_model in preapproved_models_that_can_be_deleted:
            continue

        accessor_name = related_object.get_accessor_name()
        if accessor_name is None:
            continue

        related_query_name = related_object.field.related_query_name()

        on_delete = getattr(related_object, "on_delete", None)
        # TODO: Don't forget to handle DB_CASCADE when we adopt Django 6.1
        is_relationship_guarded = on_delete in (PROTECT, RESTRICT, DO_NOTHING)
        related_model_name = related_object.related_model._meta.verbose_name
        if is_relationship_guarded:
            # If it's a foreign key that hasn't been set AKA it's null, we allow deletion
            queryset = queryset.filter(**{f"{related_query_name}__isnull": True})
            logger.info(
                "Not archiving %s records that are referenced by a %s."
                " If you wish to archive these records, you will need to manually delete the related %s"
                " records first.",
                model._meta.verbose_name,
                related_model_name,
                related_model_name,
            )
        if not is_relationship_guarded and not force_cascade_delete:
            # CASCADE deletion would occur, but execution has not permitted CASCADE delete to happen.
            # Effectively filtering only records that have nothing to CASCADE.
            queryset = queryset.filter(**{f"{related_query_name}__isnull": True})
            logger.info(
                "Not archiving %s records that are referenced by a %s, because deleting them would delete the"
                " related %s records as well. Re-run with Force Cascade Delete to archive them anyway.",
                model._meta.verbose_name,
                related_model_name,
                related_model_name,
            )

    if not force_cascade_delete:
        for private_field in model._meta.private_fields:
            if isinstance(private_field, GenericRelation):
                queryset = queryset.filter(**{f"{private_field.name}__isnull": True})
                generic_related_model_name = private_field.related_model._meta.verbose_name
                logger.info(
                    "Not archiving %s records that are referenced by a %s, because deleting them would delete"
                    " the related %s records as well. Re-run with Force Cascade Delete to archive them anyway.",
                    model._meta.verbose_name,
                    generic_related_model_name,
                    generic_related_model_name,
                )

    return queryset


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
    force_cascade_delete = BooleanVar(
        description=(
            "Allows the archival of records that will result in automatic `cascading` deletion"
            " of related records that are not archivable. This may result in data loss! It is"
            " recommended to run the job initially without enabling this option, and then"
            " carefully review any records that the initial run skipped."
        ),
        label="Force Cascade Delete",
        default=False,
        required=False,
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
        force_cascade_delete=False,
        dryrun=True,
    ):
        """
        Archive the selected models' records that are older than the age threshold.

        Returns:
            (dict): Archived record count keyed by model label, for example
                `{"extras.ObjectChange": 12, "extras.JobResult": 3, "extras.JobLogEntry": 40,
                "extras.JobConsoleEntry": 7}`. Every archivable model is present, so a model that this run
                was not asked to archive reports 0 rather than being absent.
        """
        selected_models = set(selected_models_to_archive or ARCHIVAL_ORDER)

        # Every check below asks whether a label is in `selected_models`, so a name this job does not
        # recognise matches nothing, archives nothing, and reports success. Callers that bypass the form,
        # such as the REST API, can supply one, so it is named here instead.
        unrecognized_models = selected_models - set(ARCHIVAL_ORDER)
        if unrecognized_models:
            raise ValueError(
                f"{JOB_NAME} cannot archive {', '.join(sorted(unrecognized_models))}. "
                f"Choose from: {', '.join(ARCHIVAL_DISPLAY_ORDER)}."
            )

        # `restrict()` is used in object select during the run of this job, however it only narrows
        # each queryset to the records this user may delete. And, it does this silently. A user with
        # no delete permission gets an empty queryset and would be a successful run.
        # Permissions are checked up front in order to loudly fail for a clearer user experience
        if self.user is None:
            raise PermissionDenied(f"{JOB_NAME} deletes records and requires a user, but this run has none")
        if force_cascade_delete and not get_settings_or_config(
            "ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED", fallback=False
        ):
            self.logger.error(
                "Force Cascade Delete is disabled. Set the ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED "
                "setting to True to allow it."
            )
            raise RuntimeError(
                "Force Cascade Delete is disabled by the ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED setting"
            )
        # ----------------------------------------
        # ObjectChange
        if OBJECT_CHANGE_LABEL in selected_models and not self.user.has_perm("extras.delete_objectchange"):
            self.logger.error('User "%s" does not have permission to delete ObjectChange records', self.user)
            raise PermissionDenied("User does not have delete permissions for ObjectChange records")
        if OBJECT_CHANGE_LABEL in selected_models and not self.user.has_perm("extras.add_archivedobjectchange"):
            self.logger.error('User "%s" does not have permission to add ArchivedObjectChange records', self.user)
            raise PermissionDenied("User does not have add permissions for ArchivedObjectChange records")
        # ----------------------------------------
        # JobResult/JobConsoleEntry/JobLogEntry
        if JOB_RESULT_LABEL in selected_models and not self.user.has_perm("extras.delete_jobresult"):
            self.logger.error('User "%s" does not have permission to delete JobResult records', self.user)
            raise PermissionDenied("User does not have delete permissions for JobResult records")
        if JOB_RESULT_LABEL in selected_models and not self.user.has_perm("extras.add_archivedjobresult"):
            self.logger.error('User "%s" does not have permission to add ArchivedJobResult records', self.user)
            raise PermissionDenied("User does not have add permissions for ArchivedJobResult records")
        # Cannot select JobConsoleEntry or JobLogEntry in the UI. These are derived from the selection
        # of JobResult
        if JOB_RESULT_LABEL in selected_models and not self.user.has_perm("extras.delete_jobconsoleentry"):
            self.logger.error('User "%s" does not have permission to delete JobConsoleEntry records', self.user)
            raise PermissionDenied("User does not have delete permissions for JobConsoleEntry records")
        if JOB_RESULT_LABEL in selected_models and not self.user.has_perm("extras.add_archivedjobconsoleentry"):
            self.logger.error('User "%s" does not have permission to add ArchivedJobConsoleEntry records', self.user)
            raise PermissionDenied("User does not have add permissions for ArchivedJobConsoleEntry records")
        # -----
        if JOB_RESULT_LABEL in selected_models and not self.user.has_perm("extras.delete_joblogentry"):
            self.logger.error('User "%s" does not have permission to delete JobLogEntry records', self.user)
            raise PermissionDenied("User does not have delete permissions for JobLogEntry records")
        if JOB_RESULT_LABEL in selected_models and not self.user.has_perm("extras.add_archivedjoblogentry"):
            self.logger.error('User "%s" does not have permission to add ArchivedJobLogEntry records', self.user)
            raise PermissionDenied("User does not have add permissions for ArchivedJobLogEntry records")

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
                    archive_model_threshold_timestamp, archive_batch_size, dryrun, force_cascade_delete
                )
                archived_record_counts.update(archived_object_change_counts)
            if JOB_RESULT_LABEL in selected_models:
                archived_job_result_counts = self._archive_job_results(
                    archive_model_threshold_timestamp, archive_batch_size, dryrun, force_cascade_delete
                )
                archived_record_counts.update(archived_job_result_counts)
        finally:
            self.logger.debug("Re-connecting the _handle_deleted_object signal")
            pre_delete.connect(_handle_deleted_object)

        return archived_record_counts

    # --------------------------------------------------------------------------
    # Object Change
    # --------------------------------------------------------------------------
    def _archive_object_changes(self, threshold_timestamp, batch_size, dryrun, force_cascade_delete=False):
        """
        Archive `ObjectChange` records older than `threshold_timestamp`, one batch at a time.

        No other archivable model has a foreign key to `ObjectChange`, so it can be archived on its own, in any
        order relative to the other models.

        Args:
            threshold_timestamp (datetime): Records older than this are archived.
            batch_size (int): Records to move per batch.
            dryrun (bool): Report what would move without moving anything.
            force_cascade_delete (bool): Archive records even when deleting them cascades into related objects.

        Returns:
            (dict): Archived record count keyed by model label, or on a dry run the count a real run
                would archive. Always carries the `extras.ObjectChange` key.
        """
        archival_candidate_object_changes = ObjectChange.objects.restrict(self.user, "delete").filter(
            time__lt=threshold_timestamp
        )
        object_changes_to_archive = _exclude_records_whose_relations_block_deletion(
            archival_candidate_object_changes,
            ObjectChange,
            (),
            force_cascade_delete,
        )

        omitted_object_change_count = archival_candidate_object_changes.count() - object_changes_to_archive.count()
        if omitted_object_change_count:
            self.logger.warning(
                "Omitting %d ObjectChange records because related records would be deleted "
                "with them. Re-run with Force Cascade Delete to archive them anyway.",
                omitted_object_change_count,
            )

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

        for object_change_batch in _iterate_records_by_timestamp(object_changes_to_archive, "time", batch_size):
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

            _, deleted_counts_by_model = (
                ObjectChange.objects.restrict(self.user, "delete").filter(pk__in=object_changes_to_archive_pks).delete()
            )

        archived_object_change_count = len(object_changes_to_archive_pks)
        # Django's QuerySet.delete() returns a 2-tuple
        # (total_rows_deleted, {model_label: rows_deleted_for_that_model})
        # Instead of checking rows deleted we confirm the model count deleted
        object_change_deleted_count = deleted_counts_by_model.get(OBJECT_CHANGE_LABEL, 0)

        self.logger.debug(
            "Archived %d and deleted %d live ObjectChange rows",
            archived_object_change_count,
            object_change_deleted_count,
        )
        if archived_object_change_count != object_change_deleted_count:
            self.logger.error(
                "%d ObjectChange models were archived, but only %d were deleted.",
                archived_object_change_count,
                object_change_deleted_count,
            )

        return archived_object_change_count

    # --------------------------------------------------------------------------
    # Job Results
    # --------------------------------------------------------------------------
    def _archive_job_results(self, threshold_timestamp, batch_size, dryrun, force_cascade_delete=False):
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
            force_cascade_delete (bool): Archive records even when deleting them cascades into related objects.

        Returns:
            (dict): Archived record counts keyed by model label, or on a dry run the counts a real run
                would archive. Always carries the `extras.JobResult`, `extras.JobLogEntry` and
                `extras.JobConsoleEntry` keys.
        """
        # Only job results that are done can be archived
        archival_candidate_job_results = (
            JobResult.objects.restrict(self.user, "delete")
            .filter(
                date_done__lt=threshold_timestamp,
                status__in=JobResultStatusChoices.READY_STATES,
            )
            .select_related("user")
        )
        job_results_to_archive = _exclude_records_whose_relations_block_deletion(
            archival_candidate_job_results,
            JobResult,
            (JobLogEntry, JobConsoleEntry),
            force_cascade_delete,
        )

        omitted_job_result_count = archival_candidate_job_results.count() - job_results_to_archive.count()
        if omitted_job_result_count:
            self.logger.warning(
                "Omitting %d JobResult records because related records would be deleted "
                "with them. Re-run with Force Cascade Delete to archive them anyway.",
                omitted_job_result_count,
            )

        if dryrun:
            job_result_count = job_results_to_archive.count()
            # The children are counted too, so that a dry run names the same models a real run moves
            # instead of reporting zero for records it would in fact archive.
            # Restricted like the real path below, so the dry run does not promise to archive entries that
            # a real run would not be allowed to see.
            job_log_entry_count = _exclude_records_whose_relations_block_deletion(
                JobLogEntry.objects.restrict(self.user, "delete").filter(job_result__in=job_results_to_archive),
                JobLogEntry,
                (),
                force_cascade_delete,
            ).count()
            job_console_entry_count = _exclude_records_whose_relations_block_deletion(
                JobConsoleEntry.objects.restrict(self.user, "delete").filter(job_result__in=job_results_to_archive),
                JobConsoleEntry,
                (),
                force_cascade_delete,
            ).count()
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

        for job_result_batch in _iterate_records_by_timestamp(job_results_to_archive, "date_done", batch_size):
            try:
                current_batch_counts = self._process_archive_job_result_batch(
                    job_result_batch, batch_size, force_cascade_delete
                )
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

    def _process_archive_job_result_batch(self, job_result_batch, batch_size, force_cascade_delete=False):
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
            force_cascade_delete (bool): Archive records even when deleting them cascades into related objects.

        Returns:
            (dict): Archived record counts for this batch, keyed by model label.
        """
        job_result_pks = [job_result.pk for job_result in job_result_batch]
        job_result_pks_count = len(job_result_pks)

        archived_job_result_update_fields = [
            field.name for field in ArchivedJobResult._meta.fields if field.name != "id"
        ]
        archived_job_results = [ArchivedJobResult.from_job_result(job_result) for job_result in job_result_batch]

        # Copy the parents first so that the archived children's foreign keys resolve. Each step commits on its own.
        ArchivedJobResult.objects.bulk_create(
            archived_job_results,
            update_conflicts=True,
            update_fields=archived_job_result_update_fields,
            # Postgres requires a named conflict target; MySQL has no slot for one and rejects it.
            unique_fields=["id"] if connection.features.supports_update_conflicts_with_target else [],
        )

        archived_job_log_entry_count = self._archive_job_log_entry(job_result_pks, batch_size, force_cascade_delete)
        archived_job_console_entry_count = self._archive_job_console_entry(
            job_result_pks, batch_size, force_cascade_delete
        )

        _, deleted_counts_by_model = (
            JobResult.objects.restrict(self.user, "delete").filter(pk__in=job_result_pks).delete()
        )
        # Django's QuerySet.delete() returns a 2-tuple
        # (total_rows_deleted, {model_label: rows_deleted_for_that_model})
        # Instead of checking rows deleted we confirm the model count deleted
        job_result_deleted_count = deleted_counts_by_model.get(JOB_RESULT_LABEL, 0)

        self.logger.debug(
            "Archived %d job results with %d log entries and %d console entries, and deleted %d live rows",
            job_result_pks_count,
            archived_job_log_entry_count,
            archived_job_console_entry_count,
            job_result_deleted_count,
        )
        if job_result_pks_count != job_result_deleted_count:
            self.logger.error(
                "%d JobResult models were archived, but only %d were deleted.",
                job_result_pks_count,
                job_result_deleted_count,
            )

        archived_job_result_count = {
            JOB_RESULT_LABEL: job_result_pks_count,
            JOB_LOG_ENTRY_LABEL: archived_job_log_entry_count,
            JOB_CONSOLE_ENTRY_LABEL: archived_job_console_entry_count,
        }

        return archived_job_result_count

    # --------------------------------------------------------------------------
    # Job Log Entry
    # --------------------------------------------------------------------------
    def _archive_job_log_entry(self, job_result_pks, batch_size, force_cascade_delete=False):
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
            force_cascade_delete (bool): Archive records even when deleting them cascades into related objects.

        Returns:
            (int): Job log entries archived and removed from the live table.
        """
        archived_job_log_entry_update_fields = [
            field.name for field in ArchivedJobLogEntry._meta.fields if field.name != "id"
        ]
        archival_candidate_job_log_entries = JobLogEntry.objects.restrict(self.user, "delete").filter(
            job_result_id__in=job_result_pks
        )
        job_log_entries = _exclude_records_whose_relations_block_deletion(
            archival_candidate_job_log_entries,
            JobLogEntry,
            (),
            force_cascade_delete,
        )

        omitted_job_log_entry_count = archival_candidate_job_log_entries.count() - job_log_entries.count()
        if omitted_job_log_entry_count:
            self.logger.warning(
                "Omitting %d JobLogEntry records because related records would be deleted "
                "with them. Re-run with Force Cascade Delete to archive them anyway.",
                omitted_job_log_entry_count,
            )

        archived_job_log_entry_count = 0

        for job_log_entry_chunk in _iterate_records_by_timestamp(job_log_entries, "created", batch_size):
            with transaction.atomic():
                ArchivedJobLogEntry.objects.bulk_create(
                    [ArchivedJobLogEntry.from_job_log_entry(job_log_entry) for job_log_entry in job_log_entry_chunk],
                    update_conflicts=True,
                    update_fields=archived_job_log_entry_update_fields,
                    # Postgres requires a named conflict target; MySQL has no slot for one and rejects it.
                    unique_fields=["id"] if connection.features.supports_update_conflicts_with_target else [],
                )
                JobLogEntry.objects.restrict(self.user, "delete").filter(
                    pk__in=[job_log_entry.pk for job_log_entry in job_log_entry_chunk]
                ).delete()

            archived_job_log_entry_count += len(job_log_entry_chunk)

        return archived_job_log_entry_count

    # --------------------------------------------------------------------------
    # Job Console Entry
    # --------------------------------------------------------------------------
    def _archive_job_console_entry(self, job_result_pks, batch_size, force_cascade_delete=False):
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
        archival_candidate_job_console_entries = JobConsoleEntry.objects.restrict(self.user, "delete").filter(
            job_result_id__in=job_result_pks
        )
        job_console_entries = _exclude_records_whose_relations_block_deletion(
            archival_candidate_job_console_entries,
            JobConsoleEntry,
            (),
            force_cascade_delete,
        )

        omitted_job_console_entry_count = archival_candidate_job_console_entries.count() - job_console_entries.count()
        if omitted_job_console_entry_count:
            self.logger.warning(
                "Omitting %d JobConsoleEntry records because related records would be deleted "
                "with them. Re-run with Force Cascade Delete to archive them anyway.",
                omitted_job_console_entry_count,
            )

        archived_job_console_entry_count = 0

        for job_console_entry_chunk in _iterate_records_by_timestamp(job_console_entries, "timestamp", batch_size):
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
                JobConsoleEntry.objects.restrict(self.user, "delete").filter(
                    pk__in=[job_console_entry.pk for job_console_entry in job_console_entry_chunk]
                ).delete()

            archived_job_console_entry_count += len(job_console_entry_chunk)

        return archived_job_console_entry_count
