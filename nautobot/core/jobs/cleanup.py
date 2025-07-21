from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db.models import CASCADE
from django.db.models.signals import pre_delete
from django.utils import timezone

from nautobot.core.choices import ChoiceSet
from nautobot.core.utils.config import get_settings_or_config
from nautobot.extras.jobs import IntegerVar, Job, MultiChoiceVar
from nautobot.extras.models import JobResult, ObjectChange
from nautobot.extras.signals import _handle_deleted_object

name = "System Jobs"


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

    def recursive_delete_with_cascade(self, queryset, deletion_summary):
        """
        Recursively deletes all related objects with CASCADE for a given queryset.

        Args:
            queryset (QuerySet): The queryset of objects to delete.
            deletion_summary (dict): A dictionary to store the count of deleted objects for each model.
        """
        related_objects = queryset.model._meta.related_objects
        queryset = queryset.only("id")

        for related_object in related_objects:
            if related_object.on_delete is CASCADE:
                related_model = related_object.related_model
                related_field_name = related_object.field.name
                cascade_queryset = related_model.objects.filter(**{f"{related_field_name}__id__in": queryset})
                if cascade_queryset.exists():
                    self.recursive_delete_with_cascade(cascade_queryset, deletion_summary)

        genericrelation_related_fields = [
            field for field in queryset.model._meta.private_fields if hasattr(field, "bulk_related_objects")
        ]
        for gr_related_field in genericrelation_related_fields:
            related_model = gr_related_field.related_model
            related_field_name = gr_related_field.related_query_name()
            cascade_queryset = related_model.objects.filter(**{f"{related_field_name}__id__in": queryset})
            if cascade_queryset.exists():
                self.recursive_delete_with_cascade(cascade_queryset, deletion_summary)

        deleted_count = queryset._raw_delete(using="default")
        if deleted_count:
            deletion_summary.update({queryset.model._meta.label: deleted_count})
        return deletion_summary

    def run(self, *, cleanup_types, max_age=None):  # pylint: disable=arguments-differ
        if max_age in (None, ""):
            max_age = get_settings_or_config("CHANGELOG_RETENTION", fallback=90)
            if max_age == 0:
                self.logger.warning(
                    "CHANGELOG_RETENTION setting is set to zero, disabling this Job. "
                    "If you wish to use this Job to delete records, you must specify a `max_age` value."
                )
                return 0

        if CleanupTypes.JOB_RESULT in cleanup_types and not self.user.has_perm("extras.delete_jobresult"):
            self.logger.error('User "%s" does not have permission to delete JobResult records', self.user)
            raise PermissionDenied("User does not have delete permissions for JobResult records")

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
                self.recursive_delete_with_cascade(queryset, deletion_summary)
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
                self.recursive_delete_with_cascade(queryset, deletion_summary)
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
