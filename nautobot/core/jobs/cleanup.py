from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete
from django.utils import timezone

from nautobot.core.choices import ChoiceSet
from nautobot.core.jobs.deletion_utils import (
    exclude_records_whose_dependents_the_user_cannot_delete,
    exclude_records_whose_relations_block_deletion,
)
from nautobot.core.utils.config import get_settings_or_config
from nautobot.extras.jobs import IntegerVar, Job, MultiChoiceVar
from nautobot.extras.models import JobConsoleEntry, JobLogEntry, JobResult, ObjectChange
from nautobot.extras.signals import _handle_deleted_object

name = "System Jobs"

# The number of records that are loaded into memory and deleted at one time.
CLEANUP_BATCH_SIZE = 1000


def _iterate_pks_in_batches(queryset, batch_size):
    """
    Yield the primary keys of the queryset's records, in ascending order, a list of at most `batch_size` at a time.

    Each batch is read after the previous one has been yielded, starting after the last primary key in the previous
    batch. A caller that deletes each batch before it asks for the next one therefore never gets a deleted record,
    and the loop ends even if a batch is not deleted.
    """
    ordered_queryset = queryset.order_by("pk")
    # Materialized with `list()`, because MySQL cannot use a sliced subquery in a later `pk__in` filter.
    batch_pks = list(ordered_queryset.values_list("pk", flat=True)[:batch_size])
    while batch_pks:
        yield batch_pks
        batch_pks = list(ordered_queryset.filter(pk__gt=batch_pks[-1]).values_list("pk", flat=True)[:batch_size])


def _delete_batch(model, pks, deletion_summary):
    """
    Delete the `model` records with the given primary keys, and add the deleted record counts to `deletion_summary`.

    The counts include the records of other models that the deletion cascaded to.
    """
    _, deleted_counts_by_model = model.objects.filter(pk__in=pks).delete()
    for model_label, deleted_count in deleted_counts_by_model.items():
        deletion_summary[model_label] = deletion_summary.get(model_label, 0) + deleted_count


class CleanupTypes(ChoiceSet):
    JOB_RESULT = "extras.JobResult"
    OBJECT_CHANGE = "extras.ObjectChange"

    CHOICES = (
        (JOB_RESULT, "Job results"),
        (OBJECT_CHANGE, "Change logs"),
    )


class LogsCleanup(Job):
    """
    System job to clean up ObjectChange and/or JobResult (and JobLogEntry) records older than a given age.
    """

    cleanup_types = MultiChoiceVar(
        choices=CleanupTypes.CHOICES,
        required=True,
    )

    max_age = IntegerVar(
        description=(
            "Maximum age of records to retain, in days. "
            "Leave empty to use the CHANGELOG_RETENTION setting as the maximum."
        ),
        label="Max Age",
        min_value=0,
        required=False,
    )

    class Meta:
        name = "Logs Cleanup"
        description = "Delete ObjectChange and/or JobResult/JobLogEntry records older than a specified cutoff."
        has_sensitive_variables = False

    def _delete_records(self, queryset, model, deletion_summary):
        """
        Delete the records that can be deleted safely, together with everything that cascades from them.

        Records are skipped, and reported, when deleting them would fail: see
        `exclude_records_whose_relations_block_deletion`. They are also skipped when the user may not delete every
        record that would be deleted with them: see `exclude_records_whose_dependents_the_user_cannot_delete`.
        Everything else is deleted through `QuerySet.delete()`, so that Django clears many-to-many rows, applies
        `SET_NULL` and similar options, and follows generic relations, rather than this job reimplementing each case.

        `QuerySet.delete()` loads the records it deletes into memory, so they are deleted in batches. The log and
        console entries of a batch of job results are deleted first, in batches of their own, because a single job
        result can have tens of thousands of them. Each batch commits on its own, which keeps the transactions as
        small as the batches. If deleting a job result then fails, its entries are already gone and the job result is
        left in place, to be deleted by the next run.

        Args:
            queryset (QuerySet): The records to delete.
            model (Model): The model the queryset selects from.
            deletion_summary (dict): Deleted record counts keyed by model label, updated in place.
        """
        candidate_queryset = queryset
        queryset = exclude_records_whose_relations_block_deletion(
            queryset, model, (), force_cascade_delete=True, logger=self.logger
        )
        queryset = exclude_records_whose_dependents_the_user_cannot_delete(
            queryset, model, (), force_cascade_delete=True, user=self.user, logger=self.logger
        )
        omitted_record_count = candidate_queryset.count() - queryset.count()
        if omitted_record_count:
            self.logger.warning(
                "Omitting %d %s records because related records prevent their deletion, or may not be deleted by"
                " this user.",
                omitted_record_count,
                model._meta.object_name,
            )
        for batch_pks in _iterate_pks_in_batches(queryset, CLEANUP_BATCH_SIZE):
            if model is JobResult:
                for child_model in (JobLogEntry, JobConsoleEntry):
                    child_queryset = child_model.objects.filter(job_result_id__in=batch_pks)
                    for child_batch_pks in _iterate_pks_in_batches(child_queryset, CLEANUP_BATCH_SIZE):
                        _delete_batch(child_model, child_batch_pks, deletion_summary)
            _delete_batch(model, batch_pks, deletion_summary)

    def run(self, *, cleanup_types, max_age=None):  # pylint: disable=arguments-differ
        if max_age in (None, ""):
            max_age = get_settings_or_config("CHANGELOG_RETENTION", fallback=90)
            if max_age == 0:
                self.logger.warning(
                    "CHANGELOG_RETENTION setting is set to zero, disabling this Job. "
                    "If you wish to use this Job to delete records, you must specify a `max_age` value."
                )
                return 0

        if CleanupTypes.JOB_RESULT in cleanup_types:
            # Deleting a job result also deletes its log and console entries.
            for model in (JobResult, JobLogEntry, JobConsoleEntry):
                if not self.user.has_perm(f"extras.delete_{model._meta.model_name}"):
                    self.logger.error(
                        'User "%s" does not have permission to delete %s records', self.user, model._meta.object_name
                    )
                    raise PermissionDenied(
                        f"User does not have delete permissions for {model._meta.object_name} records"
                    )

        if CleanupTypes.OBJECT_CHANGE in cleanup_types and not self.user.has_perm("extras.delete_objectchange"):
            self.logger.error('User "%s" does not have permission to delete ObjectChange records', self.user)
            raise PermissionDenied("User does not have delete permissions for ObjectChange records")

        # Bulk delete goes much faster if Django doesn't have signals to process.
        # Temporarily detach the ones we *know* to be irrelevant.
        self.logger.debug("Temporarily disconnecting some signals for performance")
        pre_delete.disconnect(_handle_deleted_object)

        try:
            cutoff = timezone.now() - timedelta(days=max_age)
            result = {}

            if CleanupTypes.JOB_RESULT in cleanup_types:
                self.logger.info("Deleting JobResult records prior to %s", cutoff)
                queryset = JobResult.objects.restrict(self.user, "delete").filter(date_done__lt=cutoff)
                deletion_summary = {}
                self._delete_records(queryset, JobResult, deletion_summary)
                result.setdefault("extras.JobResult", 0)
                result.setdefault("extras.JobLogEntry", 0)
                result.update(deletion_summary)

                for modelname, count in deletion_summary.items():
                    self.logger.info(
                        "As part of deleting %d JobResult records, also deleted %d related %s records",
                        result["extras.JobResult"],
                        count,
                        modelname,
                    )

            if CleanupTypes.OBJECT_CHANGE in cleanup_types:
                self.logger.info("Deleting ObjectChange records prior to %s", cutoff)
                queryset = ObjectChange.objects.restrict(self.user, "delete").filter(time__lt=cutoff)
                deletion_summary = {}
                self._delete_records(queryset, ObjectChange, deletion_summary)
                result.setdefault("extras.ObjectChange", 0)
                result.update(deletion_summary)

                for modelname, count in deletion_summary.items():
                    self.logger.info(
                        "As part of deleting %d ObjectChange records, also deleted %d related %s records",
                        result["extras.ObjectChange"],
                        count,
                        modelname,
                    )
            return result
        finally:
            # Be sure to clean up after ourselves!
            self.logger.debug("Re-connecting signals")
            pre_delete.connect(_handle_deleted_object)
