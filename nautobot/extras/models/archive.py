"""
Long-term retention of change and job history.

The `Archived*` models hold archived copies of the live `ObjectChange`, `JobResult`, `JobLogEntry` and
`JobConsoleEntry` models, one table each, and are populated by copying live records into them ("rotation").

Foreign keys between archived models, such as from an archived job log entry to its archived job result, are
real foreign keys, since the archive tables are always stored together. Foreign keys to any other model are stored
as bare identifier columns rather than relations, so the archive tables can later move to a separate database and an
archived record can outlive the object it refers to.
"""

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, models

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

# An archived model is named with a prefix of `Archived<LiveModel>`, there should
# be no deviation from this.
ARCHIVED_MODEL_NAME_PREFIX = "Archived"


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

    # This tuple tracks the field names on this model that have no live model counterpart. Each one is a
    # deliberate denormalization rather than drift. Anything not named here is reported as drift.
    archived_only_field_names = ()

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
        new_archived_object_change = cls(
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

        return new_archived_object_change

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

    archived_only_field_names = ("user_name",)

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

    @classmethod
    def from_job_result(cls, job_result):
        """
        Build an unsaved `ArchivedJobResult` from a live `JobResult`.

        The source record's primary key is carried over unchanged. That is what makes archival idempotent,
        and what lets this record's archived log and console entries keep pointing at it without any
        translation of their foreign key.

        `user_name` is the one field with no live counterpart: a `JobResult` reads the username through its
        `user` foreign key, which cannot be followed from the archive, so it is denormalized here.

        Args:
            job_result (JobResult): The live record to copy.

        Returns:
            (ArchivedJobResult): An unsaved instance. Saving it is the caller's responsibility.
        """
        new_archived_job_result = cls(
            id=job_result.id,
            _custom_field_data=job_result._custom_field_data,
            job_model_id=job_result.job_model_id,
            name=job_result.name,
            task_name=job_result.task_name,
            date_created=job_result.date_created,
            date_started=job_result.date_started,
            date_done=job_result.date_done,
            user_id=job_result.user_id,
            user_name=getattr(job_result.user, "username", "") or "",
            status=job_result.status,
            result=job_result.result,
            worker=job_result.worker,
            task_args=job_result.task_args,
            task_kwargs=job_result.task_kwargs,
            celery_kwargs=job_result.celery_kwargs,
            traceback=job_result.traceback,
            meta=job_result.meta,
            scheduled_job_id=job_result.scheduled_job_id,
            debug_log_count=job_result.debug_log_count,
            success_log_count=job_result.success_log_count,
            info_log_count=job_result.info_log_count,
            warning_log_count=job_result.warning_log_count,
            error_log_count=job_result.error_log_count,
            canceled_by_id=job_result.canceled_by_id,
            canceled_by_user_name=job_result.canceled_by_user_name,
            cancel_type=job_result.cancel_type,
            date_canceled=job_result.date_canceled,
        )

        return new_archived_job_result

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

    @classmethod
    def from_job_log_entry(cls, job_log_entry):
        """
        Build an unsaved `ArchivedJobLogEntry` from a live `JobLogEntry`.

        `job_result_id` is copied across as a raw identifier rather than resolved. An archived job result
        keeps the primary key it had live, so the live entry's `job_result_id` already names the correct
        `ArchivedJobResult` -- provided that parent has been archived first, which the foreign key enforces.

        Args:
            job_log_entry (JobLogEntry): The live record to copy.

        Returns:
            (ArchivedJobLogEntry): An unsaved instance. Saving it is the caller's responsibility.
        """
        new_job_log_entry = cls(
            id=job_log_entry.id,
            job_result_id=job_log_entry.job_result_id,
            log_level=job_log_entry.log_level,
            grouping=job_log_entry.grouping,
            message=job_log_entry.message,
            created=job_log_entry.created,
            log_object=job_log_entry.log_object,
            absolute_url=job_log_entry.absolute_url,
        )

        return new_job_log_entry

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

    @classmethod
    def from_job_console_entry(cls, job_console_entry):
        """
        Build an unsaved `ArchivedJobConsoleEntry` from a live `JobConsoleEntry`.

        `job_result_id` is copied across as a raw identifier rather than resolved. An archived job result
        keeps the primary key it had live, so the live entry's `job_result_id` already names the correct
        `ArchivedJobResult` -- provided that parent has been archived first, which the foreign key enforces.

        Args:
            job_console_entry (JobConsoleEntry): The live record to copy.

        Returns:
            (ArchivedJobConsoleEntry): An unsaved instance. Saving it is the caller's responsibility.
        """
        new_job_console_entry = cls(
            id=job_console_entry.id,
            job_result_id=job_console_entry.job_result_id,
            timestamp=job_console_entry.timestamp,
            output_type=job_console_entry.output_type,
            text=job_console_entry.text,
        )

        return new_job_console_entry

    def __str__(self):
        return self.text


# --------------------------------------------------------------------------------------------------
# Schema drift
# --------------------------------------------------------------------------------------------------
# An archived model has to stay field-compatible with the live model it archives. Nothing in Django
# enforces that. The two are separate models with separate migrations, so a field added to `ObjectChange`
# and not to `ArchivedObjectChange` needs to produce a loud failure.
def get_all_archived_models():
    """
    Every concrete archived log model.

    Returns:
        (list[type]): The subclasses of `ArchivedLogModel`.
    """
    return [model for model in apps.get_models() if issubclass(model, ArchivedLogModel)]


def get_live_model_name_from_archived_model(archived_model):
    """
    The name of the live model an archived model is derived from.

    Args:
        archived_model (type): The archived model to read the name of.

    Returns:
        (str | None): The live model's name, or None where the archived model is not named for one.
    """
    if not archived_model.__name__.startswith(ARCHIVED_MODEL_NAME_PREFIX):
        return None
    else:
        return archived_model.__name__.removeprefix(ARCHIVED_MODEL_NAME_PREFIX) or None


def get_live_model_from_archived_model(archived_model):
    """
    Retrieves the live model that an archived model is derived from.

    Args:
        archived_model (type): The archived model to resolve the live model for.

    Returns:
        (type | None): The live model, or None where the archived model is not named for one or names
            one that is not registered.
    """
    live_model_name = get_live_model_name_from_archived_model(archived_model)
    if live_model_name is None:
        return None
    try:
        return apps.get_model(archived_model._meta.app_label, live_model_name)
    except LookupError:
        return None


def get_archived_model_from_live_model(live_model):
    """
    Retrieves the archived model derived from a live model.

    Args:
        live_model (type): The live model to resolve the archived model for.

    Returns:
        (type | None): The archived model, or None where no model named `Archived<LiveModel>` is
            registered in the live model's app.
    """
    try:
        return apps.get_model(live_model._meta.app_label, f"{ARCHIVED_MODEL_NAME_PREFIX}{live_model.__name__}")
    except LookupError:
        return None


def get_archived_model_and_live_model_pairs():
    """
    Each archived model beside the live model it archives, resolved from the archived model's name.

    Returns:
        (list[tuple[type, type]]): Each archived model paired with the live model it archives.

    Raises:
        (LookupError): An archived model is not named for a live model, or names one that is not registered.
    """
    archived_model_and_live_models = []
    for archived_model in get_all_archived_models():
        expected_live_model_name = get_live_model_name_from_archived_model(archived_model)
        live_model = get_live_model_from_archived_model(archived_model)
        if live_model is None:
            raise LookupError(
                f"{archived_model._meta.label} does not resolve to a registered model named "
                f"{expected_live_model_name}. There is nothing to compare it against"
            )
        archived_model_and_live_models.append((archived_model, live_model))

    return archived_model_and_live_models


def _validate_plain_field(archived_model, archived_model_field, live_model, live_model_field):
    """
    Validates a plain field of an archived model and a live model.

    A plain field has no relationship.
    """
    drift_messages = []

    do_both_field_types_match = type(archived_model_field) is type(live_model_field)
    if do_both_field_types_match is False:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` is a "
            f"`{type(archived_model_field).__name__}` but `{live_model._meta.label}.{live_model_field.name}` "
            f"is a `{type(live_model_field).__name__}`"
        )

    # length only matters if they're the same type
    if do_both_field_types_match is True and archived_model_field.max_length != live_model_field.max_length:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` has a max_length of `{archived_model_field.max_length}`"
            f" and does not match the `{live_model._meta.label}.{live_model_field.name}` max_length of `{live_model_field.max_length}`."
        )

    return drift_messages


def _validate_dropped_relation_field(archived_model, archived_model_field, live_model, live_model_field):
    """
    Validates a dropped relation field of an archived model and a live model.

    A dropped relation points at a model that is not archived, so the archived model holds it as a plain
    identifier column rather than as a relation.
    """
    drift_messages = []

    is_archived_model_field_still_a_relation = archived_model_field.is_relation is True
    if is_archived_model_field_still_a_relation is True:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` is a relation to "
            f"`{archived_model_field.related_model._meta.label}` but it must be a plain identifier column, "
            f"because `{live_model._meta.label}.{live_model_field.name}` points at "
            f"`{live_model_field.related_model._meta.label}` which is not archived."
        )
        return drift_messages

    archived_model_field_column_type = archived_model_field.db_type(connection)
    live_model_field_referent_column_type = live_model_field.target_field.rel_db_type(connection)
    do_both_column_types_match = archived_model_field_column_type == live_model_field_referent_column_type
    if do_both_column_types_match is False:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` is a "
            f"`{archived_model_field_column_type}` column but it must be a "
            f"`{live_model_field_referent_column_type}` column to hold a "
            f"`{live_model_field.related_model._meta.label}` primary key."
        )

    return drift_messages


def _validate_persisted_relation_field(archived_model, archived_model_field, live_model, live_model_field):
    """
    Validates a persisted relation field of an archived model and a live model.

    A persisted relation points at a model that is archived, so the archived model keeps it as a relation,
    pointed at that archived model rather than at the live one.
    """
    drift_messages = []

    archived_model_for_live_model_field_relation = get_archived_model_from_live_model(live_model_field.related_model)

    is_archived_model_field_a_relation = archived_model_field.is_relation is True
    if is_archived_model_field_a_relation is False:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` is a plain field but it must be a "
            f"relation to `{archived_model_for_live_model_field_relation._meta.label}`, because "
            f"`{live_model._meta.label}.{live_model_field.name}` points at "
            f"`{live_model_field.related_model._meta.label}` which is archived."
        )
        return drift_messages

    does_archived_model_field_point_at_the_archived_model = (
        archived_model_field.related_model is archived_model_for_live_model_field_relation
    )
    if does_archived_model_field_point_at_the_archived_model is False:
        drift_messages.append(
            f"`{archived_model._meta.label}.{archived_model_field.name}` points at "
            f"`{archived_model_field.related_model._meta.label}` but it must point at "
            f"`{archived_model_for_live_model_field_relation._meta.label}`, the archived model for "
            f"`{live_model_field.related_model._meta.label}`."
        )

    return drift_messages


def _find_archived_model_drift(archived_model, live_model):
    """
    What has drifted on one archived model.

    Returns:
        (list[str]): One message per difference found, empty when the two models match.
    """
    archived_fields = {field.name: field for field in archived_model._meta.fields}
    live_fields = {field.name: field for field in live_model._meta.fields}

    drift_messages = []

    for live_model_field in live_model._meta.fields:
        # --------------------
        # Live Model Classification
        # --------------------
        is_live_model_field_a_foreign_relationship = live_model_field.is_relation is True
        is_live_model_field_a_plain_field = is_live_model_field_a_foreign_relationship is False

        # --------------------
        # Archived Model Classification
        # --------------------
        archived_model_relational_field_reference = (
            get_archived_model_from_live_model(live_model_field.related_model)
            if is_live_model_field_a_foreign_relationship is True
            else None
        )
        is_archived_model_relational_field_dropped = (
            is_live_model_field_a_foreign_relationship is True and archived_model_relational_field_reference is None
        )
        is_archived_model_relational_field_kept = (
            is_live_model_field_a_foreign_relationship is True and archived_model_relational_field_reference is not None
        )
        expected_archived_model_field_name = (
            f"{live_model_field.name}_id"
            if is_archived_model_relational_field_dropped is True
            else live_model_field.name
        )
        archived_model_field = archived_fields.get(expected_archived_model_field_name)

        # --------------------
        # Checks
        # --------------------
        # First check - does the field even exist
        does_archive_model_have_live_model_field = archived_model_field is not None
        if does_archive_model_have_live_model_field is False:
            new_drift_message = (
                f"`{archived_model._meta.label}` is missing the field "
                f"`{live_model._meta.label}.{live_model_field.name}`"
            )
            drift_messages.append(new_drift_message)
            # If there's no matching attribute, there's no point in continuing further checks
            continue

        # Second check - does nullability settings match
        does_archive_model_field_nullability_match_live_model_field_nullability = (
            archived_model_field.null == live_model_field.null
        )
        if does_archive_model_field_nullability_match_live_model_field_nullability is False:
            drift_messages.append(
                f"`{archived_model._meta.label}.{archived_model_field.name}` has nullability set to `null={archived_model_field.null}`."
                f" This differs with `{live_model._meta.label}.{live_model_field.name}` which has nullability set to `null={live_model_field.null}`."
            )

        # Third check - is it a plain field? If so what are the possible issues?
        if is_live_model_field_a_plain_field is True:
            plain_field_drift_messages = _validate_plain_field(
                archived_model, archived_model_field, live_model, live_model_field
            )
            drift_messages.extend(plain_field_drift_messages)

        # Fourth check - is it a relation the archived model dropped? If so what are the possible issues?
        if is_archived_model_relational_field_dropped is True:
            dropped_relation_field_drift_messages = _validate_dropped_relation_field(
                archived_model, archived_model_field, live_model, live_model_field
            )
            drift_messages.extend(dropped_relation_field_drift_messages)

        # Fifth check - is it a relation the archived model persisted? If so what are the possible issues?
        if is_archived_model_relational_field_kept is True:
            kept_relation_field_drift_messages = _validate_persisted_relation_field(
                archived_model, archived_model_field, live_model, live_model_field
            )
            drift_messages.extend(kept_relation_field_drift_messages)

    # Sixth check - does the archived model hold a column that no live model field feeds?
    for archived_model_field in archived_model._meta.fields:
        does_live_model_have_a_field_of_the_same_name = archived_model_field.name in live_fields
        is_archived_model_field_declared_as_archive_only = (
            archived_model_field.name in archived_model.archived_only_field_names
        )
        live_model_field_the_relation_was_dropped_from = live_fields.get(archived_model_field.name.removesuffix("_id"))
        is_archived_model_field_a_dropped_relation_column = (
            live_model_field_the_relation_was_dropped_from is not None
            and live_model_field_the_relation_was_dropped_from.is_relation is True
        )

        if (
            does_live_model_have_a_field_of_the_same_name is False
            and is_archived_model_field_declared_as_archive_only is False
            and is_archived_model_field_a_dropped_relation_column is False
        ):
            drift_messages.append(
                f"`{archived_model._meta.label}.{archived_model_field.name}` has no counterpart on "
                f"`{live_model._meta.label}` and is not in `archived_only_field_names`."
            )

    # Seventh check - does the live model hold a many to many field, which cannot be archived at all?
    for live_model_many_to_many_field in live_model._meta.many_to_many:
        drift_messages.append(
            f"`{archived_model._meta.label}` cannot hold "
            f"`{live_model._meta.label}.{live_model_many_to_many_field.name}` because it is a many-to-many "
            f"field, so its values are lost when a record is archived."
        )

    return drift_messages


def find_archive_schema_drift(archived_model_pairs=None):
    """
    Compare each archived model against the live model it archives.

    Args:
        archived_model_pairs (list[tuple[type, type]] | None): Each archived model paired with the live
            model it archives.

    Returns:
        (list[tuple[type, type, list[str]]]): Each archived model that has drifted, with the live model it
            archives and what has drifted on it. Empty when each archived model matches the live model it
            archives.

    Raises:
        (LookupError): An archived model is not named for a live model, or names one that is not registered.
    """
    if archived_model_pairs is None:
        archived_model_pairs = get_archived_model_and_live_model_pairs()

    archived_model_and_drifts = []
    for archived_model, live_model in archived_model_pairs:
        drift = _find_archived_model_drift(archived_model, live_model)
        if drift:
            archived_model_and_drifts.append((archived_model, live_model, drift))

    return archived_model_and_drifts
