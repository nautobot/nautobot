"""
Long-term retention of change and job history.

The `Archived*` models hold archived copies of the live `ObjectChange`, `JobResult`, `JobLogEntry` and
`JobConsoleEntry` models, one table each, and are populated by copying live records into them ("rotation").

Foreign keys are stored as bare identifier columns rather than relations, so the archive tables can later
move to a separate database and an archived record can outlive the object it refers to.
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


def unresolved_relation(relation_name):
    """
    A read-only attribute standing in for a relation that an archived model stores only as an id.

    It always resolves to None, so code that reaches for the relation by name, as it would on the live
    model, gets None instead of an `AttributeError`.

    Args:
        relation_name (str): The name of the relation on the live model, such as `"user"`. Assign the result to an
            attribute of the same name; the archived model is expected to store the related object's id in a
            field named `<relation_name>_id`.
    """
    return property(lambda self: None, doc=f"Always None; the related object is identified by `{relation_name}_id`.")


class ArchivedLogModel(BaseModel):
    """
    Abstract base for archived copies of Nautobot's log models.

    The log models are `ObjectChange`, `JobResult`, `JobLogEntry` and `JobConsoleEntry`. `id` is copied from the
    live record, so an archived record keeps its primary key and rotation can re-run without duplicating.
    """

    is_metadata_associable_model = False
    is_data_compliance_model = False
    is_version_controlled = False
    # `ArchivedJobResult` inherits `_custom_field_data`. Archived records are immutable, so it isn't offered as a
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
        # Read-only: archived records are written by rotation and never edited, so only `view` exists.
        default_permissions = ("view",)


class ArchivedObjectChange(ArchivedLogModel):
    """Archived copy of an `ObjectChange`."""

    time = models.DateTimeField(editable=False, db_index=True)
    # Not indexed, unlike the live `user` foreign key: `user` can't be followed from an archived change, so
    # archived changes are looked up by `user_name` instead.
    user_id = models.UUIDField(blank=True, null=True)
    user_name = models.CharField(max_length=150, editable=False, db_index=True)
    request_id = models.UUIDField(editable=False, db_index=True)
    action = models.CharField(max_length=50, choices=ObjectChangeActionChoices)
    # Not indexed on its own, unlike the live foreign key: it leads `extras_aoc_changed_obj_idx`.
    changed_object_type_id = models.PositiveIntegerField(blank=True, null=True)
    # Not indexed on its own, unlike the live field: objects are looked up by type and id together, which
    # `extras_aoc_changed_obj_idx` covers.
    changed_object_id = models.UUIDField()
    # Not indexed, unlike the live field: it has only a handful of distinct values, so an index would rarely help.
    change_context = models.CharField(
        max_length=50,
        choices=ObjectChangeEventContextChoices,
        editable=False,
    )
    change_context_detail = models.CharField(max_length=CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL, blank=True, editable=False)
    # Not indexed on its own, unlike the live foreign key: it leads `extras_aoc_related_obj_idx`.
    related_object_type_id = models.PositiveIntegerField(blank=True, null=True)
    related_object_id = models.UUIDField(blank=True, null=True)
    object_repr = models.CharField(max_length=CHANGELOG_MAX_OBJECT_REPR, editable=False)
    object_data = models.JSONField(encoder=DjangoJSONEncoder, editable=False)
    object_data_v2 = models.JSONField(encoder=NautobotKombuJSONEncoder, editable=False, null=True, blank=True)

    user = unresolved_relation("user")
    changed_object = unresolved_relation("changed_object")
    related_object = unresolved_relation("related_object")

    class Meta(ArchivedLogModel.Meta):
        ordering = ["-time"]
        get_latest_by = "time"
        verbose_name = "archived object change"
        verbose_name_plural = "archived object changes"
        # No counterpart to the live `unique_together`: rotation copies the live primary key, which already
        # prevents a record from being archived twice, and another unique index would only slow rotation.
        # Not replicated from `ObjectChange`, since rotation pays for every index on every insert:
        # - `extras_objectchange_triple_idx` and `extras_objectchange_double_idx` serve change logging, which looks up
        #   a request's earlier changes while recording new ones, and webhook dispatch. Neither writes archived changes.
        # - `extras_objectchange_rtime_idx` serves the homepage's latest changes panel. Newest-first ordering here
        #   uses the index on `time`, since an index can be read in either direction.
        # - `user_changed_object_idx` and `user_name_changed_object_idx` serve combined user and object lookups that
        #   nothing makes against archived changes; `user_name` has its own index.
        indexes = [
            models.Index(name="extras_aoc_changed_obj_idx", fields=["changed_object_type_id", "changed_object_id"]),
            models.Index(name="extras_aoc_related_obj_idx", fields=["related_object_type_id", "related_object_id"]),
        ]

    def get_related_changes(self, user=None, permission="view"):
        """The other archived changes to this object, restricted to those `user` has `permission` for if given."""
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
        The content type that `changed_object_type_id` identifies, or None if there is no such content type.

        Content types aren't archived, so this is looked up (and cached) from the live table.
        """
        return self._content_type_for(self.changed_object_type_id)

    @property
    def related_object_type(self):
        """
        The content type that `related_object_type_id` identifies, or None if there is no such content type.

        Content types aren't archived, so this is looked up (and cached) from the live table.
        """
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


class ArchivedJobResult(ArchivedLogModel, CustomFieldModel):
    """Archived copy of a `JobResult`."""

    # Indexed like the live foreign key, for listing a job's archived results.
    job_model_id = models.UUIDField(blank=True, null=True, db_index=True)
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    # Not indexed, unlike the live field, which is internal to job execution.
    task_name = models.CharField(  # noqa: DJ001  # matches the live column, which is nullable
        max_length=CHARFIELD_MAX_LENGTH,
        null=True,
        help_text="Registered name of the Celery task for this job. Internal use only.",
    )
    date_created = models.DateTimeField(db_index=True)
    # `date_started` and `date_done` aren't indexed, unlike the live fields: archived job results are listed and
    # filtered by `date_created`.
    date_started = models.DateTimeField(null=True, blank=True)
    date_done = models.DateTimeField(null=True, blank=True)
    # Not indexed, unlike the live `user` foreign key: `user` can't be followed from an archived job result.
    user_id = models.UUIDField(blank=True, null=True)
    # `JobResult` has no `user_name` field; it reads the username through its `user` foreign key. With only the
    # user's id archived, the username would be unrecoverable once the User is deleted, so rotation records it
    # here, as `ObjectChange.user_name` already does.
    user_name = models.CharField(max_length=150, blank=True, default="")
    # Not indexed on its own, unlike the live field: it leads `extras_ajr_statrcreate_idx`.
    status = models.CharField(
        max_length=30,
        choices=JobResultStatusChoices,
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
    worker = models.CharField(max_length=100, null=True, default=None)  # noqa: DJ001  # matches the live column
    task_args = models.JSONField(blank=True, default=list, encoder=NautobotKombuJSONEncoder)
    task_kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    celery_kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    traceback = models.TextField(blank=True, null=True)  # noqa: DJ001  # matches the live column
    meta = models.JSONField(null=True, default=None, editable=False)
    # Not indexed, unlike the live `scheduled_job` foreign key: `scheduled_job` can't be followed from an archived
    # job result.
    scheduled_job_id = models.UUIDField(blank=True, null=True)
    debug_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    success_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    info_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    warning_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    error_log_count = models.PositiveIntegerField(blank=True, null=True, editable=False)
    # Not indexed, unlike the live `canceled_by` foreign key: `canceled_by` can't be followed from an archived job
    # result.
    canceled_by_id = models.UUIDField(blank=True, null=True)
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

    job_model = unresolved_relation("job_model")
    user = unresolved_relation("user")
    scheduled_job = unresolved_relation("scheduled_job")
    canceled_by = unresolved_relation("canceled_by")

    class Meta(ArchivedLogModel.Meta):
        ordering = ["-date_created"]
        get_latest_by = "date_created"
        verbose_name = "archived job result"
        verbose_name_plural = "archived job results"
        # Not replicated from `JobResult`, since rotation pays for every index on every insert:
        # - `extras_jobresult_rcreated_idx`: newest-first ordering here uses the index on `date_created`, since an
        #   index can be read in either direction.
        # - `extras_jr_rdone_idx` and `extras_jr_statrdone_idx` serve the homepage's recent job results panel.
        indexes = [
            models.Index(name="extras_ajr_statrcreate_idx", fields=["status", "-date_created"]),
        ]

    def __str__(self):
        return f"{self.name} created at {self.date_created} ({self.status})"


class ArchivedJobLogEntry(ArchivedLogModel):
    """Archived copy of a `JobLogEntry`."""

    # Not indexed on its own, unlike the live foreign key: it leads `extras_ajoblog_jr_created_idx`.
    job_result_id = models.UUIDField()
    # `log_level` and `created` aren't indexed on their own, unlike the live fields: entries are only read within a
    # single job result, which `extras_ajoblog_jr_created_idx` has already narrowed to.
    log_level = models.CharField(max_length=32, choices=LogLevelChoices, default=LogLevelChoices.LOG_INFO)
    grouping = models.CharField(max_length=JOB_LOG_MAX_GROUPING_LENGTH, default="main")
    message = models.TextField(blank=True)
    created = models.DateTimeField()
    log_object = models.CharField(max_length=JOB_LOG_MAX_LOG_OBJECT_LENGTH, blank=True, default="")
    absolute_url = models.CharField(max_length=JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, blank=True, default="")

    job_result = unresolved_relation("job_result")

    class Meta(ArchivedLogModel.Meta):
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


class ArchivedJobConsoleEntry(ArchivedLogModel):
    """Archived copy of a `JobConsoleEntry`."""

    # Not indexed on its own, unlike the live foreign key: it leads `extras_ajobconsole_jr_ts_idx`.
    job_result_id = models.UUIDField()
    timestamp = models.DateTimeField(help_text="Timestamp when this output has been produced / received")
    output_type = models.CharField(
        max_length=10,
        choices=JobConsoleEntryOutputTypeChoices,
        default=JobConsoleEntryOutputTypeChoices.TYPE_OUTPUT,
        help_text="Type of the output (e.g. stdout, stderr, output)",
    )
    text = models.TextField(help_text="Actual line of output data")

    job_result = unresolved_relation("job_result")

    class Meta(ArchivedLogModel.Meta):
        ordering = ["timestamp"]
        get_latest_by = "timestamp"
        verbose_name = "archived job console entry"
        verbose_name_plural = "archived job console entries"
        indexes = [
            models.Index(name="extras_ajobconsole_jr_ts_idx", fields=["job_result_id", "timestamp"]),
        ]

    def __str__(self):
        return self.text
