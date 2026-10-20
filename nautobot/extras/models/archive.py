"""
Long-term retention of change and job history.

The `Archived*` models mirror the warm `ObjectChange`, `JobResult`, `JobLogEntry` and `JobConsoleEntry`
models, one table each, and are populated by copying warm records into them ("rotation").

Foreign keys are stored as bare identifier columns rather than relations, so the archive tables can later
move to a separate database and a retained record can outlive the object it refers to.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseModel
from nautobot.extras.choices import (
    JobCancelTypeChoices,
    JobConsoleEntryOutputTypeChoices,
    JobResultStatusChoices,
    LogLevelChoices,
    ObjectChangeActionChoices,
    ObjectChangeEventContextChoices,
)
from nautobot.extras.constants import (
    CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL,
    CHANGELOG_MAX_OBJECT_REPR,
    JOB_LOG_MAX_ABSOLUTE_URL_LENGTH,
    JOB_LOG_MAX_GROUPING_LENGTH,
    JOB_LOG_MAX_LOG_OBJECT_LENGTH,
)
from nautobot.extras.models.customfields import CustomFieldModel


def demoted_relation(name):
    """
    A read-only attribute standing in for a foreign key that a mirror stores only as `<name>_id`.

    It always resolves to None, so code that reaches for the relation by name, as it would on the warm
    model, gets None instead of an `AttributeError`.
    """
    return property(lambda self: None, doc=f"Always None; the related object is identified by `{name}_id`.")


class ArchivedRecord(BaseModel):
    """
    Shared shape for every retained-history mirror.

    `id` is copied from the warm record, so a retained record keeps its primary key and rotation can
    re-run without duplicating.
    """

    is_metadata_associable_model = False
    is_data_compliance_model = False
    is_version_controlled = False
    # `ArchivedJobResult` inherits `_custom_field_data`. Retained history is immutable, so it isn't offered as a
    # custom field model and its data isn't swept for orphaned keys.
    is_custom_field_model = False
    hide_in_diff_view = True
    natural_key_field_names = ["id"]

    def get_absolute_url(self, api=False):
        """
        The record's read-only detail page, or None where it has none.

        None rather than raising, so a linkified column renders plain text instead of failing the row.
        """
        try:
            return super().get_absolute_url(api=api)
        except AttributeError:
            return None

    class Meta:
        abstract = True
        # Read-only: retained records are written by rotation and never edited, so only `view` exists.
        default_permissions = ("view",)


class ArchivedObjectChange(ArchivedRecord):
    """
    Every field of a retained `extras.ObjectChange`.
    """

    time = models.DateTimeField(editable=False, db_index=True)
    user_id = models.UUIDField(blank=True, null=True)
    user_name = models.CharField(max_length=150, editable=False, db_index=True)
    request_id = models.UUIDField(editable=False, db_index=True)
    action = models.CharField(max_length=50, choices=ObjectChangeActionChoices)
    changed_object_type_id = models.PositiveIntegerField(blank=True, null=True)
    changed_object_id = models.UUIDField(db_index=True)
    change_context = models.CharField(
        max_length=50,
        choices=ObjectChangeEventContextChoices,
        editable=False,
        db_index=True,
    )
    change_context_detail = models.CharField(max_length=CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL, blank=True, editable=False)
    related_object_type_id = models.PositiveIntegerField(blank=True, null=True)
    related_object_id = models.UUIDField(blank=True, null=True)
    object_repr = models.CharField(max_length=CHANGELOG_MAX_OBJECT_REPR, editable=False)
    object_data = models.JSONField(encoder=DjangoJSONEncoder, editable=False)
    object_data_v2 = models.JSONField(encoder=NautobotKombuJSONEncoder, editable=False, null=True, blank=True)

    user = demoted_relation("user")
    changed_object = demoted_relation("changed_object")
    related_object = demoted_relation("related_object")

    class Meta(ArchivedRecord.Meta):
        ordering = ["-time"]
        get_latest_by = "time"
        verbose_name = "archived object change"
        verbose_name_plural = "archived object changes"
        # No counterpart to the warm `unique_together`: rotation copies the warm primary key, which already
        # prevents a record from being retained twice, and another unique index would only slow rotation.
        indexes = [
            models.Index(
                name="extras_aoc_triple_idx",
                fields=["request_id", "changed_object_type_id", "changed_object_id"],
            ),
            models.Index(name="extras_aoc_double_idx", fields=["request_id", "changed_object_type_id"]),
            models.Index(name="extras_aoc_rtime_idx", fields=["-time"]),
            models.Index(name="extras_aoc_changed_obj_idx", fields=["changed_object_type_id", "changed_object_id"]),
            models.Index(name="extras_aoc_related_obj_idx", fields=["related_object_type_id", "related_object_id"]),
            models.Index(
                name="extras_aoc_user_chg_obj_idx",
                fields=["user_id", "changed_object_type_id", "changed_object_id"],
            ),
            models.Index(
                name="extras_aoc_uname_chg_obj_idx",
                fields=["user_name", "changed_object_type_id", "changed_object_id"],
            ),
        ]

    def get_related_changes(self, user=None, permission="view"):
        """The other retained changes to this object, restricted to those `user` has `permission` for if given."""
        related_changes = (
            type(self)
            .objects.filter(
                changed_object_type_id=self.changed_object_type_id,
                changed_object_id=self.changed_object_id,
            )
            .exclude(pk=self.pk)
        )
        if user is not None:
            return related_changes.restrict(user, permission)
        return related_changes

    @property
    def changed_object_type(self):
        """
        The content type this record's `changed_object_type_id` names, or None.

        A content type is schema metadata rather than a changelog record, and `get_for_id` is cached per
        process. None where the app has been uninstalled since.
        """
        return self._content_type_for(self.changed_object_type_id)

    @property
    def related_object_type(self):
        """The content type this record's `related_object_type_id` names, or None."""
        return self._content_type_for(self.related_object_type_id)

    @staticmethod
    def _content_type_for(type_id):
        if not type_id:
            return None
        try:
            return ContentType.objects.get_for_id(type_id)
        except ContentType.DoesNotExist:
            return None

    def get_action_class(self):
        """CSS class for the action badge, as `ObjectChange.get_action_class` provides it."""
        return ObjectChangeActionChoices.CSS_CLASSES.get(self.action)

    def __str__(self):
        return f"{self.changed_object_type} {self.object_repr} {self.get_action_display().lower()} by {self.user_name}"


class ArchivedJobResult(ArchivedRecord, CustomFieldModel):
    """
    Every field of a retained `extras.JobResult`.
    """

    job_model_id = models.UUIDField(blank=True, null=True, db_index=True)
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    task_name = models.CharField(  # noqa: DJ001  # mirrors the warm column, which is nullable
        max_length=CHARFIELD_MAX_LENGTH,
        null=True,
        db_index=True,
        help_text="Registered name of the Celery task for this job. Internal use only.",
    )
    date_created = models.DateTimeField(db_index=True)
    date_started = models.DateTimeField(null=True, blank=True, db_index=True)
    date_done = models.DateTimeField(null=True, blank=True, db_index=True)
    user_id = models.UUIDField(blank=True, null=True, db_index=True)
    # Not a mirror: `JobResult` has no `user_name`, it reads through the `user` FK. With the FK demoted
    # to an id column, the username would be unrecoverable once the User row is deleted, so rotation
    # denormalizes it here. This is the same trade `ObjectChange.user_name` already makes.
    user_name = models.CharField(max_length=150, blank=True, default="")
    status = models.CharField(
        max_length=30,
        choices=JobResultStatusChoices,
        db_index=True,
        default=JobResultStatusChoices.STATUS_PENDING,
        help_text="Current state of the Job being run",
    )
    result = models.JSONField(
        verbose_name="Result Data",
        encoder=NautobotKombuJSONEncoder,
        null=True,
        blank=True,
        editable=False,
        help_text="The data returned by the task",
    )
    worker = models.CharField(max_length=100, null=True, default=None)  # noqa: DJ001  # mirrors the warm column
    task_args = models.JSONField(blank=True, default=list, encoder=NautobotKombuJSONEncoder)
    task_kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    celery_kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    traceback = models.TextField(blank=True, null=True)  # noqa: DJ001  # mirrors the warm column
    meta = models.JSONField(null=True, default=None, editable=False)
    scheduled_job_id = models.UUIDField(blank=True, null=True, db_index=True)
    debug_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    success_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    info_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    warning_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    error_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    canceled_by_id = models.UUIDField(blank=True, null=True, db_index=True)
    canceled_by_user_name = models.CharField(max_length=150, blank=True, editable=False)
    cancel_type = models.CharField(
        max_length=30,
        choices=JobCancelTypeChoices,
        blank=True,
        help_text="Cancel type of the Job being canceled",
    )
    date_canceled = models.DateTimeField(null=True, blank=True, help_text="Timestamp at which the job was canceled")
    # `_custom_field_data` comes from `CustomFieldModel`. Rotation copies the raw JSON, so no custom field value
    # is lost.

    job_model = demoted_relation("job_model")
    user = demoted_relation("user")
    scheduled_job = demoted_relation("scheduled_job")
    canceled_by = demoted_relation("canceled_by")

    class Meta(ArchivedRecord.Meta):
        ordering = ["-date_created"]
        get_latest_by = "date_created"
        verbose_name = "archived job result"
        verbose_name_plural = "archived job results"
        indexes = [
            models.Index(name="extras_ajr_rcreated_idx", fields=["-date_created"]),
            models.Index(name="extras_ajr_rdone_idx", fields=["-date_done"]),
            models.Index(name="extras_ajr_statrcreate_idx", fields=["status", "-date_created"]),
            models.Index(name="extras_ajr_statrdone_idx", fields=["status", "-date_done"]),
        ]

    def __str__(self):
        return f"{self.name} created at {self.date_created} ({self.status})"


class ArchivedJobLogEntry(ArchivedRecord):
    """
    Every field of a retained `extras.JobLogEntry`.
    """

    job_result_id = models.UUIDField(db_index=True)
    log_level = models.CharField(
        max_length=32, choices=LogLevelChoices, db_index=True, default=LogLevelChoices.LOG_INFO
    )
    grouping = models.CharField(max_length=JOB_LOG_MAX_GROUPING_LENGTH, default="main")
    message = models.TextField(blank=True)
    created = models.DateTimeField(db_index=True)
    log_object = models.CharField(max_length=JOB_LOG_MAX_LOG_OBJECT_LENGTH, blank=True, default="")
    absolute_url = models.CharField(max_length=JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, blank=True, default="")

    job_result = demoted_relation("job_result")

    class Meta(ArchivedRecord.Meta):
        ordering = ["created"]
        get_latest_by = "created"
        verbose_name = "archived job log entry"
        verbose_name_plural = "archived job log entries"
        indexes = [
            # The access path for a job result's log table.
            models.Index(name="extras_ajoblog_jr_created_idx", fields=["job_result_id", "created"]),
        ]

    def __str__(self):
        return self.message


class ArchivedJobConsoleEntry(ArchivedRecord):
    """
    Every field of a retained `extras.JobConsoleEntry`.
    """

    job_result_id = models.UUIDField(db_index=True)
    timestamp = models.DateTimeField(help_text="Timestamp when this output has been produced / received")
    output_type = models.CharField(
        max_length=10,
        choices=JobConsoleEntryOutputTypeChoices,
        default=JobConsoleEntryOutputTypeChoices.TYPE_OUTPUT,
        help_text="Type of the output (e.g. stdout, stderr, output)",
    )
    text = models.TextField(help_text="Actual line of output data")

    job_result = demoted_relation("job_result")

    class Meta(ArchivedRecord.Meta):
        ordering = ["timestamp"]
        get_latest_by = "timestamp"
        verbose_name = "archived job console entry"
        verbose_name_plural = "archived job console entries"
        indexes = [
            models.Index(name="extras_ajobconsole_jr_ts_idx", fields=["job_result_id", "timestamp"]),
        ]

    def __str__(self):
        return self.text
