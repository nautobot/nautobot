"""
Long-term retention of change and job history.

The `Archived*` models hold archived copies of the live `ObjectChange`, `JobResult`, `JobLogEntry` and
`JobConsoleEntry` models, one table each, and are populated by copying live records into them ("rotation").

Foreign keys between archived models, such as from an archived job log entry to its archived job result, are
real foreign keys, since the archive tables are always stored together. Foreign keys to any other model are stored
as bare identifier columns rather than relations, so the archive tables can later move to a separate database and an
archived record can outlive the object it refers to.
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
    Helper method to create a read-only property, representing a previous foreign key relation that cannot be referenced from the archived model.

    It always resolves to `None`, to prevent `AttributeErrors` from occurring when code tries to access the relation by its property name, as it would have done the live
    model.

    Args:
        relation_name (str): The name of the relation on the live model, such as `"user"`. Assign the result to an
            attribute of the same name; the archived model is expected to store the related object's id in a
            field named `<relation_name>_id`.

    Returns:
        (property): A read-only property that resolves to `None` on every instance.
    """

    def always_none(self):
        return None

    return property(always_none, doc=f"Always None; the related object is identified by `{relation_name}_id`.")


class ArchivedLogModel(BaseModel):
    """
    Abstract base class for archived copies of Nautobot's log-like models.

    The `id` of the original live record is copied to the archived database record in order to simplify auditing, to allow
    archival workflows, and to support idempotency.
    """

    is_metadata_associable_model = False
    is_data_compliance_model = False
    is_version_controlled = False
    # ArchivedLogModel records are immutable, so their `_custom_field_data` (if any) exists
    # independent of `CustomField` definitions, and new fields cannot be associated to them.
    is_custom_field_model = False
    hide_in_diff_view = True
    natural_key_field_names = ["id"]

    def get_absolute_url(self, api=False):
        """
        The archived model's read-only detail page, or None where it has none.

        Returns None rather than raising an exception in the case of no valid URL being located. Done so that a linkified table column
        (which calls `get_absolute_url()`) renders unlinked plaintext correctly instead of failing to render the row entirely.

        Args:
            api (bool): Specifies if an API url should be returned

        Returns:
            (str | None): The UI or API URL for the Log, or None where it has no route.
        """
        try:
            return super().get_absolute_url(api=api)
        except AttributeError:
            return None

    class Meta:
        abstract = True
        # Archived data must be read-only
        default_permissions = ("view",)


class ArchivedObjectChange(ArchivedLogModel):
    """An ObjectChange model that has been Archived."""

    time = models.DateTimeField(editable=False, db_index=True)
    # Not indexed, unlike the live `user` foreign key: `user` can't be followed from an archived change, so
    # archived changes are looked up by `user_name` instead.
    user_id = models.UUIDField(blank=True, null=True)
    user_name = models.CharField(max_length=150, editable=False, db_index=True)
    request_id = models.UUIDField(editable=False, db_index=True)
    action = models.CharField(max_length=50, choices=ObjectChangeActionChoices)
    # Not indexed on its own, as it's already the first element in index `extras_aoc_changed_obj_idx`.
    changed_object_type_id = models.PositiveIntegerField(blank=True, null=True)
    # Not indexed on its own, as it's covered by the composite index `extras_aoc_changed_obj_idx`.
    changed_object_id = models.UUIDField()
    # Not indexed on its own: it has only a handful of distinct values, so an index would rarely help.
    change_context = models.CharField(
        max_length=50,
        choices=ObjectChangeEventContextChoices,
        editable=False,
    )
    change_context_detail = models.CharField(max_length=CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL, blank=True, editable=False)
    # Not indexed on its own, as it's covered by the composite index `extras_aoc_related_obj_idx`.
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

    # TODO: Naming is hard, get a better name
    @classmethod
    def from_object_change(cls, object_change):
        """
        Build an unsaved `ArchivedObjectChange` from a live `ObjectChange`.

        TODO: Add more documentation

        Args:
            object_change (ObjectChange): The live record to copy.

        Returns:
            (ArchivedObjectChange): An unsaved instance. Saving it is the caller's responsibility.
        """
        return cls(
            id=object_change.id,
            time=object_change.time,
            user_id=object_change.user_id,
            user_name=object_change.user_name,
            request_id=object_change.request_id,
            action=object_change.action,
            changed_object_type_id=object_change.changed_object_type_id,
            changed_object_id=object_change.changed_object_id,
            change_context=object_change.change_context,
            change_context_detail=object_change.change_context_detail,
            related_object_type_id=object_change.related_object_type_id,
            related_object_id=object_change.related_object_id,
            object_repr=object_change.object_repr,
            object_data=object_change.object_data,
            object_data_v2=object_change.object_data_v2,
        )

    def get_related_changes(self, user=None, permission="view"):
        """
        Retrieve other ArchivedObjectChanges that have the same `changed_object` as this record.

        Equivalent to `ObjectChange.get_related_changes`.

        Args:
            user (User | None): If given, restrict the results to those this user holds `permission` for.
                When None, no restriction is applied and every matching record is returned.
            permission (str): The permission action to restrict by, such as `"view"`. Ignored unless
                `user` is given.

        Returns:
            (QuerySet): ArchivedChangeObjects sharing this record's `changed_object_type_id` and
                `changed_object_id`, excluding this record.
        """
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

        Equivalent to the `ObjectChange.changed_object_type` GenericForeignKey.
        Note that ContentTypes aren't archived, so this returns a "live" ContentType record, if any.
        """
        return self._content_type_for(self.changed_object_type_id)

    @property
    def related_object_type(self):
        """
        The content type that `related_object_type_id` identifies, or None if there is no such content type.

        Equivalent to the `ObjectChange.related_object_type` GenericForeignKey.
        Note that ContentTypes aren't archived, so this returns a "live" ContentType record, if any.
        """
        return self._content_type_for(self.related_object_type_id)

    @staticmethod
    def _content_type_for(type_id):
        """
        Retrieves the `ContentType` by id or `None` if not located.

        Returns:
            (ContentType | None): A ContentType or None
        """
        if not type_id:
            return None
        try:
            return ContentType.objects.get_for_id(type_id)
        except ContentType.DoesNotExist:
            return None

    def get_action_class(self):
        """CSS class for rendering an `action` badge in the UI, same as `ObjectChange.get_action_class`."""
        return ObjectChangeActionChoices.CSS_CLASSES.get(self.action)

    def __str__(self):
        return f"{self.changed_object_type} {self.object_repr} {self.get_action_display().lower()} by {self.user_name}"


class ArchivedJobResult(ArchivedLogModel, CustomFieldModel):
    """Archived copy of a `JobResult`."""

    # Indexed like the `JobResult.job_model_id`, for listing a job's archived results.
    job_model_id = models.UUIDField(blank=True, null=True, db_index=True)
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    # Not indexed, as only live `JobResult` records are looked up by `task_name` during job execution.
    task_name = models.CharField(  # noqa: DJ001  # matches the live column, which is nullable
        max_length=CHARFIELD_MAX_LENGTH,
        null=True,
        help_text="Registered name of the Celery task for this job. Internal use only.",
    )
    date_created = models.DateTimeField(db_index=True)
    # `date_started` and `date_done` are not indexed, unlike the equivalent `JobResult` fields, as
    # `ArchivedJobResult` is almost always filtered or ordered by its `date_created` alone.
    date_started = models.DateTimeField(null=True, blank=True)
    date_done = models.DateTimeField(null=True, blank=True)
    # Not indexed. Unlike the `JobResult.user` foreign key, `user` cannot be followed from an `ArchivedJobResult`
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

    job_model = unresolved_relation("job_model")
    user = unresolved_relation("user")
    scheduled_job = unresolved_relation("scheduled_job")
    canceled_by = unresolved_relation("canceled_by")

    class Meta(ArchivedLogModel.Meta):
        ordering = ["-date_created"]
        get_latest_by = "date_created"
        verbose_name = "archived job result"
        verbose_name_plural = "archived job results"
        # The following indexes are NOT replicated from `JobResult` because:
        # - `extras_jobresult_rcreated_idx`: newest-first ordering here uses the index on `date_created`, since an
        #   index can be read in either direction.
        # - `extras_jr_rdone_idx` and `extras_jr_statrdone_idx` serve the homepage's "recent job results" panel,
        #   and there is no equivalent UI for `ArchivedJobResult` records.
        indexes = [
            models.Index(name="extras_ajr_statrcreate_idx", fields=["status", "-date_created"]),
        ]

    def __str__(self):
        return f"{self.name} created at {self.date_created} ({self.status})"


class ArchivedJobLogEntry(ArchivedLogModel):
    """Archived copy of a `JobLogEntry`."""

    job_result = models.ForeignKey(
        to="extras.ArchivedJobResult", on_delete=models.CASCADE, related_name="job_log_entries"
    )
    # `log_level` and `created` are not indexed on their own, as entries are only retrieved within the
    # context of a specific job result, which the index `extras_ajoblog_jr_created_idx` covers.
    log_level = models.CharField(max_length=32, choices=LogLevelChoices, default=LogLevelChoices.LOG_INFO)
    grouping = models.CharField(max_length=JOB_LOG_MAX_GROUPING_LENGTH, default="main")
    message = models.TextField(blank=True)
    created = models.DateTimeField()
    log_object = models.CharField(max_length=JOB_LOG_MAX_LOG_OBJECT_LENGTH, blank=True, default="")
    absolute_url = models.CharField(max_length=JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, blank=True, default="")

    class Meta(ArchivedLogModel.Meta):
        ordering = ["created"]
        get_latest_by = "created"
        verbose_name = "archived job log entry"
        verbose_name_plural = "archived job log entries"
        indexes = [
            # The access path for a job result's log table.
            models.Index(name="extras_ajoblog_jr_created_idx", fields=["job_result", "created"]),
        ]

    def __str__(self):
        return self.message


class ArchivedJobConsoleEntry(ArchivedLogModel):
    """Archived copy of a `JobConsoleEntry`."""

    job_result = models.ForeignKey(
        to="extras.ArchivedJobResult", on_delete=models.CASCADE, related_name="job_console_entries"
    )
    timestamp = models.DateTimeField(help_text="Timestamp when this output has been produced / received")
    output_type = models.CharField(
        max_length=10,
        choices=JobConsoleEntryOutputTypeChoices,
        default=JobConsoleEntryOutputTypeChoices.TYPE_OUTPUT,
        help_text="Type of the output (e.g. stdout, stderr, output)",
    )
    text = models.TextField(help_text="Actual line of output data")

    class Meta(ArchivedLogModel.Meta):
        ordering = ["timestamp"]
        get_latest_by = "timestamp"
        verbose_name = "archived job console entry"
        verbose_name_plural = "archived job console entries"
        indexes = [
            models.Index(name="extras_ajobconsole_jr_ts_idx", fields=["job_result", "timestamp"]),
        ]

    def __str__(self):
        return self.text
