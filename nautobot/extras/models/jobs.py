# Data models relating to Jobs

from datetime import timedelta
import logging
import os
import uuid

from celery import schedules

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import signals
from django.urls import reverse
from django.utils import timezone

from django_celery_beat.clockedschedule import clocked
from django_celery_beat.managers import ExtendedManager

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.fields import AutoSlugField, slugify_dots_to_dashes
from nautobot.core.models import BaseModel
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.extras.choices import JobExecutionType, JobResultStatusChoices, JobSourceChoices, LogLevelChoices
from nautobot.extras.constants import (
    JOB_LOG_MAX_ABSOLUTE_URL_LENGTH,
    JOB_LOG_MAX_GROUPING_LENGTH,
    JOB_LOG_MAX_LOG_OBJECT_LENGTH,
    JOB_MAX_GROUPING_LENGTH,
    JOB_MAX_NAME_LENGTH,
    JOB_MAX_SLUG_LENGTH,
    JOB_MAX_SOURCE_LENGTH,
    JOB_OVERRIDABLE_FIELDS,
)
from nautobot.extras.plugins.utils import import_object
from nautobot.extras.querysets import JobQuerySet, ScheduledJobExtendedQuerySet
from nautobot.extras.utils import (
    ChangeLoggedModelsQuery,
    FeatureQuery,
    extras_features,
    get_job_content_type,
    jobs_in_directory,
)
from nautobot.utilities.fields import JSONArrayField
from nautobot.utilities.logging import sanitize

from .customfields import CustomFieldModel


logger = logging.getLogger(__name__)


# The JOB_LOGS variable is used to tell the JobLogEntry model the database to store to.
# We default this to job_logs, and creating at the Global level allows easy override
# during testing. This needs to point to the same physical database so that the
# foreign key relationship works, but needs its own connection to avoid JobLogEntry
# objects being created within transaction.atomic().
JOB_LOGS = "job_logs"


@extras_features(
    "custom_fields",
    "custom_links",
    "graphql",
    "job_results",
    "relationships",
    "webhooks",
)
class Job(PrimaryModel):
    """
    Database model representing an installed Job class.
    """

    # Information used to locate the Job source code
    source = models.CharField(
        max_length=JOB_MAX_SOURCE_LENGTH,
        choices=JobSourceChoices,
        editable=False,
        db_index=True,
        help_text="Source of the Python code for this job - local, Git repository, or plugins",
    )
    git_repository = models.ForeignKey(
        to="extras.GitRepository",
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        db_index=True,
        related_name="jobs",
        help_text="Git repository that provides this job",
    )
    module_name = models.CharField(
        max_length=JOB_MAX_NAME_LENGTH,
        editable=False,
        db_index=True,
        help_text="Dotted name of the Python module providing this job",
    )
    job_class_name = models.CharField(
        max_length=JOB_MAX_NAME_LENGTH,
        editable=False,
        db_index=True,
        help_text="Name of the Python class providing this job",
    )

    slug = AutoSlugField(
        max_length=JOB_MAX_SLUG_LENGTH,
        populate_from=["class_path"],
        slugify_function=slugify_dots_to_dashes,
    )

    # Human-readable information, potentially inherited from the source code
    # See also the docstring of nautobot.extras.jobs.BaseJob.Meta.
    grouping = models.CharField(
        max_length=JOB_MAX_GROUPING_LENGTH,
        help_text="Human-readable grouping that this job belongs to",
        db_index=True,
    )
    name = models.CharField(
        max_length=JOB_MAX_NAME_LENGTH,
        help_text="Human-readable name of this job",
        db_index=True,
    )
    description = models.TextField(blank=True, help_text="Markdown formatting is supported")

    # Control flags
    installed = models.BooleanField(
        default=True,
        db_index=True,
        editable=False,
        help_text="Whether the Python module and class providing this job are presently installed and loadable",
    )
    enabled = models.BooleanField(default=False, help_text="Whether this job can be executed by users")

    is_job_hook_receiver = models.BooleanField(
        default=False, editable=False, help_text="Whether this job is a job hook receiver"
    )

    has_sensitive_variables = models.BooleanField(
        default=True, help_text="Whether this job contains sensitive variables"
    )

    # Additional properties, potentially inherited from the source code
    # See also the docstring of nautobot.extras.jobs.BaseJob.Meta.
    approval_required = models.BooleanField(
        default=False, help_text="Whether the job requires approval from another user before running"
    )
    commit_default = models.BooleanField(
        default=True, help_text="Whether the job defaults to committing changes when run, or defaults to a dry-run"
    )
    hidden = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the job defaults to not being shown in the UI",
    )
    # Job.Meta.field_order is not overridable in this model
    read_only = models.BooleanField(
        default=False, help_text="Whether the job is prevented from making lasting changes to the database"
    )
    soft_time_limit = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Maximum runtime in seconds before the job will receive a <code>SoftTimeLimitExceeded</code> "
        "exception.<br>Set to 0 to use Nautobot system default",
    )
    time_limit = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Maximum runtime in seconds before the job will be forcibly terminated."
        "<br>Set to 0 to use Nautobot system default",
    )
    task_queues = JSONArrayField(
        base_field=models.CharField(max_length=100, blank=True),
        default=list,
        blank=True,
        help_text="Comma separated list of task queues that this job can run on. A blank list will use the default queue",
    )

    # Flags to indicate whether the above properties are inherited from the source code or overridden by the database
    grouping_override = models.BooleanField(
        default=False,
        help_text="If set, the configured grouping will remain even if the underlying Job source code changes",
    )
    name_override = models.BooleanField(
        default=False,
        help_text="If set, the configured name will remain even if the underlying Job source code changes",
    )
    description_override = models.BooleanField(
        default=False,
        help_text="If set, the configured description will remain even if the underlying Job source code changes",
    )

    approval_required_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    commit_default_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    hidden_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    read_only_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    soft_time_limit_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    time_limit_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    has_sensitive_variables_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    task_queues_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )

    objects = JobQuerySet.as_manager()

    class Meta:
        managed = True
        ordering = ["grouping", "name"]
        unique_together = [
            ("source", "git_repository", "module_name", "job_class_name"),
            ("grouping", "name"),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._job_class = None
        self._latest_result = None

    def __str__(self):
        return self.name

    def validate_unique(self, exclude=None):
        """
        Check for duplicate (source, module_name, job_class_name) in the case where git_repository is None.

        This is needed because NULL != NULL and so the unique_together constraint will not flag this case.
        """
        if self.git_repository is None:
            if Job.objects.exclude(pk=self.pk).filter(
                source=self.source, module_name=self.module_name, job_class_name=self.job_class_name
            ):
                raise ValidationError(
                    {"job_class_name": "A Job already exists with this source, module_name, and job_class_name"}
                )

        super().validate_unique(exclude=exclude)

    @property
    def job_class(self):
        """Get the Job class (source code) associated with this Job model."""
        if not self.installed:
            return None
        if self._job_class is None:
            if self.source == JobSourceChoices.SOURCE_LOCAL:
                path = settings.JOBS_ROOT
                for job_info in jobs_in_directory(settings.JOBS_ROOT, module_name=self.module_name):
                    if job_info.job_class_name == self.job_class_name:
                        self._job_class = job_info.job_class
                        break
                else:
                    logger.warning("Module %s job class %s not found!", self.module_name, self.job_class_name)
            elif self.source == JobSourceChoices.SOURCE_GIT:
                from nautobot.extras.datasources.git import ensure_git_repository

                if self.git_repository is None:
                    logger.warning("Job %s %s has no associated Git repository", self.module_name, self.job_class_name)
                    return None
                try:
                    # In the case where we have multiple Nautobot instances, or multiple worker instances,
                    # they are not required to share a common filesystem; therefore, we may need to refresh our local
                    # clone of the Git repository to ensure that it is in sync with the latest repository clone
                    # from any instance.
                    ensure_git_repository(
                        self.git_repository,
                        head=self.git_repository.current_head,
                        logger=logger,
                    )
                    path = os.path.join(self.git_repository.filesystem_path, "jobs")
                    for job_info in jobs_in_directory(path, module_name=self.module_name):
                        if job_info.job_class_name == self.job_class_name:
                            self._job_class = job_info.job_class
                            break
                    else:
                        logger.warning(
                            "Module %s job class %s not found in repository %s",
                            self.module_name,
                            self.job_class_name,
                            self.git_repository,
                        )
                except ObjectDoesNotExist:
                    return None
                except Exception as exc:
                    logger.error(f"Error during local clone/refresh of Git repository {self.git_repository}: {exc}")
                    return None
            elif self.source == JobSourceChoices.SOURCE_PLUGIN:
                # pkgutil.resolve_name is only available in Python 3.9 and later
                self._job_class = import_object(f"{self.module_name}.{self.job_class_name}")

        return self._job_class

    @property
    def class_path(self):
        if self.git_repository is not None:
            return f"{self.source}.{self.git_repository.slug}/{self.module_name}/{self.job_class_name}"
        return f"{self.source}/{self.module_name}/{self.job_class_name}"

    @property
    def latest_result(self):
        if self._latest_result is None:
            self._latest_result = self.results.first()
        return self._latest_result

    @property
    def description_first_line(self):
        return self.description.splitlines()[0]

    @property
    def runnable(self):
        return (
            self.enabled
            and self.installed
            and self.job_class is not None
            and not (self.has_sensitive_variables and self.approval_required)
        )

    def clean(self):
        """For any non-overridden fields, make sure they get reset to the actual underlying class value if known."""
        if self.job_class is not None:
            for field_name in JOB_OVERRIDABLE_FIELDS:
                if not getattr(self, f"{field_name}_override", False):
                    setattr(self, field_name, getattr(self.job_class, field_name))

        if self.git_repository is not None and self.source != JobSourceChoices.SOURCE_GIT:
            raise ValidationError('A Git repository may only be specified when the source is "git"')

        # Protect against invalid input when auto-creating Job records
        if len(self.source) > JOB_MAX_SOURCE_LENGTH:
            raise ValidationError(f"Source may not exceed {JOB_MAX_SOURCE_LENGTH} characters in length")
        if len(self.module_name) > JOB_MAX_NAME_LENGTH:
            raise ValidationError(f"Module name may not exceed {JOB_MAX_NAME_LENGTH} characters in length")
        if len(self.job_class_name) > JOB_MAX_NAME_LENGTH:
            raise ValidationError(f"Job class name may not exceed {JOB_MAX_NAME_LENGTH} characters in length")
        if len(self.grouping) > JOB_MAX_GROUPING_LENGTH:
            raise ValidationError("Grouping may not exceed {JOB_MAX_GROUPING_LENGTH} characters in length")
        if len(self.name) > JOB_MAX_NAME_LENGTH:
            raise ValidationError(f"Name may not exceed {JOB_MAX_NAME_LENGTH} characters in length")
        if len(self.slug) > JOB_MAX_SLUG_LENGTH:
            raise ValidationError(f"Slug may not exceed {JOB_MAX_SLUG_LENGTH} characters in length")

        if self.has_sensitive_variables is True and self.approval_required is True:
            raise ValidationError(
                {"approval_required": "A job that may have sensitive variables cannot be marked as requiring approval"}
            )

    def get_absolute_url(self):
        return reverse("extras:job_detail", kwargs={"slug": self.slug})


@extras_features("graphql")
class JobHook(OrganizationalModel):
    """
    A job hook defines a request that will trigger a job hook receiver when an object is created, updated, and/or
    deleted in Nautobot. Each job hook can be limited to firing only on certain actions or certain object types.
    """

    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="job_hooks",
        verbose_name="Object types",
        # 2.0 TODO: standardize verbose name for ContentType fields
        limit_choices_to=ChangeLoggedModelsQuery,
        help_text="The object(s) to which this job hook applies.",
    )
    enabled = models.BooleanField(default=True)
    job = models.ForeignKey(
        to=Job,
        related_name="job_hook",
        verbose_name="Job",
        help_text="The job that this job hook will initiate",
        on_delete=models.CASCADE,
        limit_choices_to={"is_job_hook_receiver": True},
    )
    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    type_create = models.BooleanField(default=False, help_text="Call this job hook when a matching object is created.")
    type_delete = models.BooleanField(default=False, help_text="Call this job hook when a matching object is deleted.")
    type_update = models.BooleanField(default=False, help_text="Call this job hook when a matching object is updated.")

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        # At least one action type must be selected
        if not self.type_create and not self.type_delete and not self.type_update:
            raise ValidationError("You must select at least one type: create, update, and/or delete.")

    def get_absolute_url(self):
        return reverse("extras:jobhook", kwargs={"slug": self.slug})

    @classmethod
    def check_for_conflicts(
        cls, instance=None, content_types=None, job=None, type_create=None, type_update=None, type_delete=None
    ):
        """
        Helper method for enforcing uniqueness.

        Don't allow two job hooks with the same content_type, same job, and any action(s) in common.
        Called by JobHookForm.clean() and JobHookSerializer.validate()
        """

        conflicts = {}
        job_hook_error_msg = "A job hook already exists for {action} on {content_type} to job {job}"

        if instance is not None and instance.present_in_database:
            # This is a PATCH and might not include all relevant data
            # Therefore we get data not available from instance
            content_types = instance.content_types.all() if content_types is None else content_types
            type_create = instance.type_create if type_create is None else type_create
            type_update = instance.type_update if type_update is None else type_update
            type_delete = instance.type_delete if type_delete is None else type_delete

        if content_types is not None:
            for content_type in content_types:
                job_hooks = cls.objects.filter(content_types__in=[content_type], job=job)
                if instance and instance.present_in_database:
                    job_hooks = job_hooks.exclude(pk=instance.pk)

                existing_type_create = job_hooks.filter(type_create=type_create).exists() if type_create else False
                existing_type_update = job_hooks.filter(type_update=type_update).exists() if type_update else False
                existing_type_delete = job_hooks.filter(type_delete=type_delete).exists() if type_delete else False

                if existing_type_create:
                    conflicts.setdefault("type_create", []).append(
                        job_hook_error_msg.format(content_type=content_type, action="create", job=job),
                    )

                if existing_type_update:
                    conflicts.setdefault("type_update", []).append(
                        job_hook_error_msg.format(content_type=content_type, action="update", job=job),
                    )

                if existing_type_delete:
                    conflicts.setdefault("type_delete", []).append(
                        job_hook_error_msg.format(content_type=content_type, action="delete", job=job),
                    )

        return conflicts


@extras_features(
    "graphql",
)
class JobLogEntry(BaseModel):
    """Stores each log entry for the JobResult."""

    job_result = models.ForeignKey(to="extras.JobResult", on_delete=models.CASCADE, related_name="logs")
    log_level = models.CharField(
        max_length=32, choices=LogLevelChoices, default=LogLevelChoices.LOG_DEFAULT, db_index=True
    )
    grouping = models.CharField(max_length=JOB_LOG_MAX_GROUPING_LENGTH, default="main")
    message = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)
    # Storing both of the below as strings instead of using GenericForeignKey to support
    # compatibility with existing JobResult logs. GFK would pose a problem with dangling foreign-key
    # references, whereas this allows us to retain all records for as long as the entry exists.
    # This also simplifies migration from the JobResult Data field as these were stored as strings.
    log_object = models.CharField(max_length=JOB_LOG_MAX_LOG_OBJECT_LENGTH, null=True, blank=True)
    absolute_url = models.CharField(max_length=JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, null=True, blank=True)

    csv_headers = ["created", "grouping", "log_level", "log_object", "message"]

    def __str__(self):
        return self.message

    class Meta:
        ordering = ["created"]
        get_latest_by = "created"
        verbose_name_plural = "job log entries"

    def to_csv(self):
        """Indicates model fields to return as csv."""
        return (str(self.created), self.grouping, self.log_level, self.log_object, self.message)


#
# Job results
#
@extras_features(
    "custom_fields",
    "custom_links",
    "graphql",
)
class JobResult(BaseModel, CustomFieldModel):
    """
    This model stores the results from running a Job.
    """

    # Note that we allow job_model to be null and use models.SET_NULL here.
    # This is because we want to be able to keep JobResult records for tracking and auditing purposes even after
    # deleting the corresponding Job record.
    job_model = models.ForeignKey(
        to="extras.Job", null=True, blank=True, on_delete=models.SET_NULL, related_name="results"
    )

    name = models.CharField(max_length=255, db_index=True)
    obj_type = models.ForeignKey(
        to=ContentType,
        related_name="job_results",
        verbose_name="Object types",
        limit_choices_to=FeatureQuery("job_results"),
        help_text="The object type to which this job result applies",
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)
    completed = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", blank=True, null=True
    )
    # todoindex:
    status = models.CharField(
        max_length=30,
        choices=JobResultStatusChoices,
        default=JobResultStatusChoices.STATUS_PENDING,
    )
    data = models.JSONField(encoder=DjangoJSONEncoder, null=True, blank=True)
    job_kwargs = models.JSONField(blank=True, null=True, encoder=NautobotKombuJSONEncoder)
    schedule = models.ForeignKey(to="extras.ScheduledJob", on_delete=models.SET_NULL, null=True, blank=True)
    """
    Although "data" is technically an unstructured field, we have a standard structure that we try to adhere to.

    This structure is created loosely as a superset of the formats used by Scripts and Reports in NetBox 2.10.

    Log Messages now go to their own object, the JobLogEntry.

    data = {
        "output": <optional string, such as captured stdout/stderr>,
    }
    """

    job_id = models.UUIDField(unique=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_job_logs_db = True

    class Meta:
        ordering = ["-created"]
        get_latest_by = "created"

    def __str__(self):
        return str(self.job_id)

    @property
    def duration(self):
        if not self.completed:
            return None

        duration = self.completed - self.created
        minutes, seconds = divmod(duration.total_seconds(), 60)

        return f"{int(minutes)} minutes, {seconds:.2f} seconds"

    @property
    def related_object(self):
        """Get the related object, if any, identified by the `obj_type`, `name`, and/or `job_id` fields.

        If `obj_type` is extras.Job, then the `name` is used to look up an extras.jobs.Job subclass based on the
        `class_path` of the Job subclass.
        Note that this is **not** the extras.models.Job model class nor an instance thereof.

        Else, if the the model class referenced by `obj_type` has a `name` field, our `name` field will be used
        to look up a corresponding model instance. This is used, for example, to look up a related `GitRepository`;
        more generally it can be used by any model that 1) has a unique `name` field and 2) needs to have a many-to-one
        relationship between JobResults and model instances.

        Else, the `obj_type` and `job_id` will be used together as a quasi-GenericForeignKey to look up a model
        instance whose PK corresponds to the `job_id`. This behavior is currently unused in the Nautobot core,
        but may be of use to plugin developers wishing to create JobResults that have a one-to-one relationship
        to plugin model instances.

        This method is potentially rather slow as get_job() may need to actually load the Job class from disk;
        consider carefully whether you actually need to use it.
        """
        from nautobot.extras.jobs import get_job  # needed here to avoid a circular import issue

        if self.obj_type == get_job_content_type():
            # Related object is an extras.Job subclass, our `name` matches its `class_path`
            return get_job(self.name)

        model_class = self.obj_type.model_class()

        if model_class is not None:
            if hasattr(model_class, "name"):
                # See if we have a many-to-one relationship from JobResult to model_class record, based on `name`
                try:
                    return model_class.objects.get(name=self.name)
                except model_class.DoesNotExist:
                    pass

            # See if we have a one-to-one relationship from JobResult to model_class record based on `job_id`
            try:
                return model_class.objects.get(id=self.job_id)
            except model_class.DoesNotExist:
                pass

        return None

    @property
    def related_name(self):
        """
        Similar to self.name, but if there's an appropriate `related_object`, use its name instead.

        Since this calls related_object, the same potential performance concerns exist. Use with caution.
        """
        related_object = self.related_object
        if not related_object:
            return self.name
        if hasattr(related_object, "name"):
            return related_object.name
        return str(related_object)

    @property
    def linked_record(self):
        """
        A newer alternative to self.related_object that looks up an extras.models.Job instead of an extras.jobs.Job.
        """
        if self.job_model is not None:
            return self.job_model
        model_class = self.obj_type.model_class()
        if model_class is not None:
            if hasattr(model_class, "name"):
                try:
                    return model_class.objects.get(name=self.name)
                except model_class.DoesNotExist:
                    pass
            if hasattr(model_class, "class_path"):
                try:
                    return model_class.objects.get(class_path=self.name)
                except model_class.DoesNotExist:
                    pass
        return None

    def get_absolute_url(self):
        return reverse("extras:jobresult", kwargs={"pk": self.pk})

    def set_status(self, status):
        """
        Helper method to change the status of the job result. If the target status is terminal, the  completion
        time is also set.
        """
        self.status = status
        if status in JobResultStatusChoices.TERMINAL_STATE_CHOICES:
            self.completed = timezone.now()

    @classmethod
    def enqueue_job(cls, func, name, obj_type, user, *args, celery_kwargs=None, schedule=None, **kwargs):
        """
        Create a JobResult instance and enqueue a job using the given callable

        func: The callable object to be enqueued for execution
        name: Name for the JobResult instance - corresponds to the desired Job class's "class_path" attribute,
            if obj_type is extras.Job; for other funcs and obj_types it may differ.
        obj_type: ContentType to link to the JobResult instance obj_type
        user: User object to link to the JobResult instance
        celery_kwargs: Dictionary of kwargs to pass as **kwargs to Celery when job is queued
        args: additional args passed to the callable
        schedule: Optional ScheduledJob instance to link to the JobResult
        kwargs: additional kwargs passed to the callable
        """
        # Discard "request" parameter from the kwargs that we save in the job_result, as it's not relevant to re-runs,
        # and will likely go away in the future.
        job_result_kwargs = {key: value for key, value in kwargs.items() if key != "request"}
        job_result = cls.objects.create(
            name=name,
            obj_type=obj_type,
            user=user,
            job_id=uuid.uuid4(),
            schedule=schedule,
        )

        kwargs["job_result_pk"] = job_result.pk

        # Prepare kwargs that will be sent to Celery
        if celery_kwargs is None:
            celery_kwargs = {}

        if obj_type.app_label == "extras" and obj_type.model.lower() == "job":
            try:
                job_model = Job.objects.get_for_class_path(name)
                if job_model.soft_time_limit > 0:
                    celery_kwargs["soft_time_limit"] = job_model.soft_time_limit
                if job_model.time_limit > 0:
                    celery_kwargs["time_limit"] = job_model.time_limit
                if not job_model.has_sensitive_variables:
                    job_result.job_kwargs = job_result_kwargs
                job_result.job_model = job_model
                job_result.save()
            except Job.DoesNotExist:
                # 2.0 TODO: remove this fallback logic, database records should always exist
                from nautobot.extras.jobs import get_job  # needed here to avoid a circular import issue

                job_class = get_job(name)
                if job_class is not None:
                    logger.error("No Job instance found in the database corresponding to %s", name)
                    if hasattr(job_class.Meta, "soft_time_limit"):
                        celery_kwargs["soft_time_limit"] = job_class.Meta.soft_time_limit
                    if hasattr(job_class.Meta, "time_limit"):
                        celery_kwargs["time_limit"] = job_class.Meta.time_limit
                    if not job_class.has_sensitive_variables:
                        job_result.job_kwargs = job_result_kwargs
                        job_result.save()
                else:
                    logger.error("Neither a Job database record nor a Job source class were found for %s", name)

        # Jobs queued inside of a transaction need to run after the transaction completes and the JobResult is saved to the database
        transaction.on_commit(
            lambda: func.apply_async(args=args, kwargs=kwargs, task_id=str(job_result.job_id), **celery_kwargs)
        )

        return job_result

    def log(
        self,
        message,
        obj=None,
        level_choice=LogLevelChoices.LOG_DEFAULT,
        grouping="main",
        logger=None,  # pylint: disable=redefined-outer-name
    ):
        """
        General-purpose API for storing log messages in a JobResult's 'data' field.

        message (str): Message to log (an attempt will be made to sanitize sensitive information from this message)
        obj (object): Object associated with this message, if any
        level_choice (LogLevelChoices): Message severity level
        grouping (str): Grouping to store the log message under
        logger (logging.logger): Optional logger to also output the message to
        """
        if level_choice not in LogLevelChoices.as_dict():
            raise Exception(f"Unknown logging level: {level_choice}")

        message = sanitize(str(message))

        log = JobLogEntry(
            job_result=self,
            log_level=level_choice,
            grouping=grouping[:JOB_LOG_MAX_GROUPING_LENGTH],
            message=message,
            created=timezone.now().isoformat(),
            log_object=str(obj)[:JOB_LOG_MAX_LOG_OBJECT_LENGTH] if obj else None,
            absolute_url=obj.get_absolute_url()[:JOB_LOG_MAX_ABSOLUTE_URL_LENGTH]
            if hasattr(obj, "get_absolute_url")
            else None,
        )

        # If the override is provided, we want to use the default database(pass no using argument)
        # Otherwise we want to use a separate database here so that the logs are created immediately
        # instead of within transaction.atomic(). This allows us to be able to report logs when the jobs
        # are running, and allow us to rollback the database without losing the log entries.
        if not self.use_job_logs_db or not JOB_LOGS:
            log.save()
        else:
            log.save(using=JOB_LOGS)

        if logger:
            if level_choice == LogLevelChoices.LOG_FAILURE:
                log_level = logging.ERROR
            elif level_choice == LogLevelChoices.LOG_WARNING:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO
            logger.log(log_level, message)


class ScheduledJobs(models.Model):
    """Helper table for tracking updates to scheduled tasks.
    This stores a single row with ident=1.  last_update is updated
    via django signals whenever anything is changed in the ScheduledJob model.
    Basically this acts like a DB data audit trigger.
    Doing this so we also track deletions, and not just insert/update.
    """

    ident = models.SmallIntegerField(default=1, primary_key=True, unique=True)
    last_update = models.DateTimeField(null=False)

    objects = ExtendedManager()

    @classmethod
    def changed(cls, instance, **kwargs):
        """This function acts as a signal handler to track changes to the scheduled job that is triggered before a change"""
        if not instance.no_changes:
            cls.update_changed()

    @classmethod
    def update_changed(cls, **kwargs):
        """This function acts as a signal handler to track changes to the scheduled job that is triggered after a change"""
        cls.objects.update_or_create(ident=1, defaults={"last_update": timezone.now()})

    @classmethod
    def last_change(cls):
        """This function acts as a getter for the last update on scheduled jobs"""
        try:
            return cls.objects.get(ident=1).last_update
        except cls.DoesNotExist:
            return None


class ScheduledJob(BaseModel):
    """Model representing a periodic task."""

    name = models.CharField(
        max_length=200, verbose_name="Name", help_text="Short Description For This Task", db_index=True
    )
    task = models.CharField(
        max_length=200,
        verbose_name="Task Name",
        help_text='The name of the Celery task that should be run. (Example: "proj.tasks.import_contacts")',
        db_index=True,
    )
    # Note that we allow job_model to be null and use models.SET_NULL here.
    # This is because we want to be able to keep ScheduledJob records for tracking and auditing purposes even after
    # deleting the corresponding Job record.
    job_model = models.ForeignKey(
        to="extras.Job", null=True, blank=True, on_delete=models.SET_NULL, related_name="scheduled_jobs"
    )
    job_class = models.CharField(
        max_length=255,
        verbose_name="Job Class",
        help_text="Name of the fully qualified Nautobot Job class path",
        db_index=True,
    )
    interval = models.CharField(choices=JobExecutionType, max_length=255)
    args = models.JSONField(blank=True, default=list, encoder=NautobotKombuJSONEncoder)
    kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    queue = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default=None,
        verbose_name="Queue Override",
        help_text="Queue defined in CELERY_TASK_QUEUES. Leave None for default queuing.",
        db_index=True,
    )
    one_off = models.BooleanField(
        default=False,
        verbose_name="One-off Task",
        help_text="If True, the schedule will only run the task a single time",
    )
    start_time = models.DateTimeField(
        verbose_name="Start Datetime",
        help_text="Datetime when the schedule should begin triggering the task to run",
    )
    # todoindex:
    enabled = models.BooleanField(
        default=True,
        verbose_name="Enabled",
        help_text="Set to False to disable the schedule",
    )
    last_run_at = models.DateTimeField(
        editable=False,
        blank=True,
        null=True,
        verbose_name="Most Recent Run",
        help_text="Datetime that the schedule last triggered the task to run. "
        "Reset to None if enabled is set to False.",
    )
    total_run_count = models.PositiveIntegerField(
        default=0,
        editable=False,
        verbose_name="Total Run Count",
        help_text="Running count of how many times the schedule has triggered the task",
    )
    date_changed = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Modified",
        help_text="Datetime that this scheduled job was last modified",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Detailed description about the details of this scheduled job",
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        help_text="User that requested the schedule",
    )
    approved_by_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        help_text="User that approved the schedule",
    )
    # todoindex:
    approval_required = models.BooleanField(default=False)
    approved_at = models.DateTimeField(
        editable=False,
        blank=True,
        null=True,
        verbose_name="Approval date/time",
        help_text="Datetime that the schedule was approved",
    )
    crontab = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Custom cronjob",
        help_text="Cronjob syntax string for custom scheduling",
    )

    objects = ScheduledJobExtendedQuerySet.as_manager()
    no_changes = False

    def __str__(self):
        return f"{self.name}: {self.interval}"

    def get_absolute_url(self):
        return reverse("extras:scheduledjob", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        self.queue = self.queue or None
        # pass pk to worker task in kwargs, celery doesn't provide the full object to the worker
        self.kwargs["scheduled_job_pk"] = self.pk
        # make sure non-valid crontab doesn't get saved
        if self.interval == JobExecutionType.TYPE_CUSTOM:
            try:
                self.get_crontab(self.crontab)
            except Exception as e:
                raise ValidationError({"crontab": e})
        if not self.enabled:
            self.last_run_at = None
        elif not self.last_run_at:
            # I'm not sure if this is a bug, or "works as designed", but if self.last_run_at is not set,
            # the celery beat scheduler will never pick up a recurring job. One-off jobs work just fine though.
            if self.interval in [
                JobExecutionType.TYPE_HOURLY,
                JobExecutionType.TYPE_DAILY,
                JobExecutionType.TYPE_WEEKLY,
            ]:
                # A week is 7 days, otherwise the iteration is set to 1
                multiplier = 7 if self.interval == JobExecutionType.TYPE_WEEKLY else 1
                # Set the "last run at" time to one interval before the scheduled start time
                self.last_run_at = self.start_time - timedelta(
                    **{JobExecutionType.CELERY_INTERVAL_MAP[self.interval]: multiplier},
                )

        super().save(*args, **kwargs)

    def clean(self):
        """
        Model Validation
        """
        if self.user and self.approved_by_user and self.user == self.approved_by_user:
            raise ValidationError("The requesting and approving users cannot be the same")
        # bitwise xor also works on booleans, but not on complex values
        if bool(self.approved_by_user) ^ bool(self.approved_at):
            raise ValidationError("Approval by user and approval time must either both be set or both be undefined")

    @property
    def schedule(self):
        if self.interval == JobExecutionType.TYPE_FUTURE:
            # This is one-time clocked task
            return clocked(clocked_time=self.start_time)

        return self.to_cron()

    @staticmethod
    def earliest_possible_time():
        return timezone.now() + timedelta(seconds=15)

    @classmethod
    def get_crontab(cls, crontab):
        """
        Wrapper method translates crontab syntax to Celery crontab.

        Supports following symbols:

        • Asterisk (*) - signifies all possible values
        • Comma (,) - lists multiple values
        • Hyphen (-) - determine a range of values
        • Slash (/) - divide a value ({*/15 * * * *} runs every 15 minutes)

        No support for Last (L), Weekday (W), Number symbol (#), Question mark (?), and special @ strings.
        """
        minute, hour, day_of_month, month_of_year, day_of_week = crontab.split(" ")
        return schedules.crontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week,
        )

    def to_cron(self):
        t = self.start_time
        if self.interval == JobExecutionType.TYPE_HOURLY:
            return schedules.crontab(minute=t.minute)
        elif self.interval == JobExecutionType.TYPE_DAILY:
            return schedules.crontab(minute=t.minute, hour=t.hour)
        elif self.interval == JobExecutionType.TYPE_WEEKLY:
            return schedules.crontab(minute=t.minute, hour=t.hour, day_of_week=t.strftime("%w"))
        elif self.interval == JobExecutionType.TYPE_CUSTOM:
            return self.get_crontab(self.crontab)
        raise ValueError(f"I do not know to convert {self.interval} to a Cronjob!")


signals.pre_delete.connect(ScheduledJobs.changed, sender=ScheduledJob)
signals.pre_save.connect(ScheduledJobs.changed, sender=ScheduledJob)
signals.post_save.connect(ScheduledJobs.update_changed, sender=ScheduledJob)
