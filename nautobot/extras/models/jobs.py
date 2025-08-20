# Data models relating to Jobs

import contextlib
from datetime import datetime, timedelta
import json
import logging
import signal
from typing import Optional, TYPE_CHECKING, Union

from billiard.exceptions import SoftTimeLimitExceeded
from celery.exceptions import NotRegistered
from celery.utils.log import get_logger, LoggingProxy
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import ProtectedError, signals
from django.utils import timezone
from django.utils.functional import cached_property
from django_celery_beat.clockedschedule import clocked
from django_celery_beat.tzcrontab import TzAwareCrontab
from prometheus_client import Histogram
from timezone_field import TimeZoneField

from nautobot.core.celery import (
    app,
    NautobotKombuJSONEncoder,
    setup_nautobot_job_logging,
)
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.utils.logging import sanitize
from nautobot.extras.choices import (
    ButtonClassChoices,
    JobExecutionType,
    JobQueueTypeChoices,
    JobResultStatusChoices,
    LogLevelChoices,
)
from nautobot.extras.constants import (
    JOB_LOG_MAX_ABSOLUTE_URL_LENGTH,
    JOB_LOG_MAX_GROUPING_LENGTH,
    JOB_LOG_MAX_LOG_OBJECT_LENGTH,
    JOB_MAX_NAME_LENGTH,
    JOB_OVERRIDABLE_FIELDS,
)
from nautobot.extras.managers import JobResultManager, ScheduledJobsManager
from nautobot.extras.models import ChangeLoggedModel, GitRepository
from nautobot.extras.models.mixins import ContactMixin, DynamicGroupsModelMixin, NotesMixin
from nautobot.extras.querysets import JobQuerySet, ScheduledJobExtendedQuerySet
from nautobot.extras.utils import (
    ChangeLoggedModelsQuery,
    extras_features,
    get_job_queue_worker_count,
    run_kubernetes_job_and_return_job_result,
)

from .customfields import CustomFieldModel

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()

logger = logging.getLogger(__name__)


# The JOB_LOGS variable is used to tell the JobLogEntry model the database to store to.
# We default this to job_logs, and creating at the Global level allows easy override
# during testing. This needs to point to the same physical database so that the
# foreign key relationship works, but needs its own connection to avoid JobLogEntry
# objects being created within transaction.atomic().
JOB_LOGS = "job_logs"

# The JOB_RESULT_METRIC variable is a counter metric that counts executions of jobs,
# including information beyond what a tool like flower could get by introspecting
# the celery task queue. This is accomplished by looking one abstraction deeper into
# the job model of Nautobot.
JOB_RESULT_METRIC = Histogram(
    "nautobot_job_duration_seconds", "Results of Nautobot jobs.", ["grouping", "name", "status"]
)


@extras_features(
    "custom_links",
    "graphql",
    "job_results",
    "webhooks",
)
class Job(PrimaryModel):
    """
    Database model representing an installed Job class.
    """

    # Information used to locate the Job source code
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

    # Human-readable information, potentially inherited from the source code
    # See also the docstring of nautobot.extras.jobs.BaseJob.Meta.
    grouping = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        help_text="Human-readable grouping that this job belongs to",
        db_index=True,
    )
    name = models.CharField(
        max_length=JOB_MAX_NAME_LENGTH,
        help_text="Human-readable name of this job",
        unique=True,
    )
    description = models.TextField(
        blank=True,
        help_text="Markdown formatting and a limited subset of HTML are supported",
    )

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

    is_job_button_receiver = models.BooleanField(
        default=False, editable=False, help_text="Whether this job is a job button receiver"
    )

    has_sensitive_variables = models.BooleanField(
        default=True, help_text="Whether this job contains sensitive variables"
    )

    is_singleton = models.BooleanField(
        default=False,
        help_text="Whether this job should fail to run if another instance of this job is already running",
    )

    # Additional properties, potentially inherited from the source code
    # See also the docstring of nautobot.extras.jobs.BaseJob.Meta.
    approval_required = models.BooleanField(
        default=False, help_text="Whether the job requires approval from another user before running"
    )
    hidden = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the job defaults to not being shown in the UI",
    )
    # Job.Meta.field_order is not overridable in this model
    dryrun_default = models.BooleanField(
        default=False, help_text="Whether the job defaults to running with dryrun argument set to true"
    )
    read_only = models.BooleanField(
        default=False, editable=False, help_text="Set to true if the job does not make any changes to the environment"
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
    supports_dryrun = models.BooleanField(
        default=False,
        editable=False,
        help_text="If supported, allows the job to bypass approval when running with dryrun argument set to true",
    )
    job_queues = models.ManyToManyField(
        to="extras.JobQueue",
        related_name="jobs",
        verbose_name="Job Queues",
        help_text="The job queues that this job can be run on",
        through="extras.JobQueueAssignment",
    )
    default_job_queue = models.ForeignKey(
        to="extras.JobQueue",
        related_name="default_for_jobs",
        on_delete=models.PROTECT,
        verbose_name="Default Job Queue",
        null=False,
        blank=False,
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
    dryrun_default_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    hidden_override = models.BooleanField(
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
    job_queues_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    default_job_queue_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    is_singleton_override = models.BooleanField(
        default=False,
        help_text="If set, the configured value will remain even if the underlying Job source code changes",
    )
    objects = BaseManager.from_queryset(JobQuerySet)()

    documentation_static_path = "docs/user-guide/platform-functionality/jobs/models.html"

    class Meta:
        managed = True
        ordering = ["grouping", "name"]
        unique_together = ["module_name", "job_class_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._latest_result = None

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.module_name.startswith("nautobot."):
            raise ProtectedError(
                f"Unable to delete Job {self}. System Job cannot be deleted",
                [],
            )
        super().delete(*args, **kwargs)

    @property
    def job_class(self):
        """
        Get the Job class (source code) associated with this Job model.

        CAUTION: if the Job is provided by a Git Repository or is installed in JOBS_ROOT, you may need or wish to
        call `get_job(self.class_path, reload=True)` to ensure that you have the latest Job code...
        """
        from nautobot.extras.jobs import get_job

        if not self.installed:
            return None
        try:
            return get_job(self.class_path)
        except Exception as exc:
            logger.error(str(exc))
            return None

    @property
    def class_path(self):
        return f"{self.module_name}.{self.job_class_name}"

    @property
    def latest_result(self):
        """
        Return the most recent JobResult object associated with this Job.

        Note that, as a performance optimization for this function's repeated use in
        JobListview, the returned object only includes its `status` field.
        """
        if self._latest_result is None:
            self._latest_result = self.job_results.only("status").first()
        return self._latest_result

    @property
    def description_first_line(self):
        return self.description.splitlines()[0]

    @property
    def runnable(self):
        return self.enabled and self.installed and not (self.has_sensitive_variables and self.approval_required)

    @cached_property
    def git_repository(self):
        """GitRepository record, if any, that owns this Job."""
        try:
            return GitRepository.objects.get(slug=self.module_name.split(".")[0])
        except GitRepository.DoesNotExist:
            return None

    @property
    def job_task(self):
        """Get an instance of the associated Job class, refreshing it if necessary."""
        from nautobot.extras.jobs import get_job

        try:
            return get_job(self.class_path, reload=True)()
        except TypeError as err:  # keep 2.0-2.2.2 exception behavior
            raise NotRegistered from err

    @property
    def task_queues(self) -> list[str]:
        """Deprecated backward-compatibility property for the list of queue names for this Job."""
        return self.job_queues.values_list("name", flat=True)

    @task_queues.setter
    def task_queues(self, value: Union[str, list[str]]):
        job_queues = []
        # value is going to be a comma separated list of queue names
        if isinstance(value, str):
            value = value.split(",")
        for queue in value:
            try:
                job_queues.append(JobQueue.objects.get(name=queue))
            except JobQueue.DoesNotExist:
                raise ValidationError(f"Job Queue {queue} does not exist in the database.")
        self.job_queues.set(job_queues)

    @property
    def task_queues_override(self):
        return self.job_queues_override

    @task_queues_override.setter
    def task_queues_override(self, value):
        if isinstance(value, bool):
            raise ValidationError(
                {
                    "task_queues_override": f"{value} is invalid for field task_queues_override, use a boolean value instead"
                }
            )
        self.job_queues_override = value

    def clean(self):
        """For any non-overridden fields, make sure they get reset to the actual underlying class value if known."""
        from nautobot.extras.jobs import get_job

        job_class = get_job(self.class_path, reload=True)
        if job_class is not None:
            for field_name in JOB_OVERRIDABLE_FIELDS:
                if not getattr(self, f"{field_name}_override", False):
                    setattr(self, field_name, getattr(job_class, field_name))

            if not self.job_queues_override:
                self.task_queues = job_class.task_queues or [settings.CELERY_TASK_DEFAULT_QUEUE]

        # Protect against invalid input when auto-creating Job records
        if len(self.module_name) > JOB_MAX_NAME_LENGTH:
            raise ValidationError(f"Module name may not exceed {JOB_MAX_NAME_LENGTH} characters in length")
        if len(self.job_class_name) > JOB_MAX_NAME_LENGTH:
            raise ValidationError(f"Job class name may not exceed {JOB_MAX_NAME_LENGTH} characters in length")
        if len(self.grouping) > CHARFIELD_MAX_LENGTH:
            raise ValidationError(f"Grouping may not exceed {CHARFIELD_MAX_LENGTH} characters in length")
        if len(self.name) > JOB_MAX_NAME_LENGTH:
            raise ValidationError(f"Name may not exceed {JOB_MAX_NAME_LENGTH} characters in length")

        if self.has_sensitive_variables is True and self.approval_required is True:
            raise ValidationError(
                {"approval_required": "A job that may have sensitive variables cannot be marked as requiring approval"}
            )

    def save(self, *args, **kwargs):
        """When a Job is uninstalled, auto-disable all associated JobButtons, JobHooks, and ScheduledJobs."""
        super().save(*args, **kwargs)
        if not self.installed:
            if self.is_job_button_receiver:
                for jb in JobButton.objects.filter(job=self, enabled=True):
                    logger.info("Disabling JobButton %s derived from %s", jb, self)
                    jb.enabled = False
                    jb.save()
            if self.is_job_hook_receiver:
                for jh in JobHook.objects.filter(job=self, enabled=True):
                    logger.info("Disabling JobHook %s derived from %s", jh, self)
                    jh.enabled = False
                    jh.save()
            for sj in ScheduledJob.objects.filter(job_model=self, enabled=True):
                logger.info("Disabling ScheduledJob %s derived from %s", sj, self)
                sj.enabled = False
                sj.save()


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
        related_name="job_hooks",
        verbose_name="Job",
        help_text="The job that this job hook will initiate",
        on_delete=models.CASCADE,
        limit_choices_to={"is_job_hook_receiver": True},
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    type_create = models.BooleanField(default=False, help_text="Call this job hook when a matching object is created.")
    type_delete = models.BooleanField(default=False, help_text="Call this job hook when a matching object is deleted.")
    type_update = models.BooleanField(default=False, help_text="Call this job hook when a matching object is updated.")

    documentation_static_path = "docs/user-guide/platform-functionality/jobs/jobhook.html"

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        # At least one action type must be selected
        if not self.type_create and not self.type_delete and not self.type_update:
            raise ValidationError("You must select at least one type: create, update, and/or delete.")

        if self.enabled and not (self.job.installed and self.job.enabled):
            raise ValidationError({"enabled": "The selected Job is not installed and enabled"})

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

    job_result = models.ForeignKey(to="extras.JobResult", on_delete=models.CASCADE, related_name="job_log_entries")
    log_level = models.CharField(
        max_length=32, choices=LogLevelChoices, default=LogLevelChoices.LOG_INFO, db_index=True
    )
    grouping = models.CharField(max_length=JOB_LOG_MAX_GROUPING_LENGTH, default="main")
    message = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now, db_index=True)
    # Storing both of the below as strings instead of using GenericForeignKey to support
    # compatibility with existing JobResult logs. GFK would pose a problem with dangling foreign-key
    # references, whereas this allows us to retain all records for as long as the entry exists.
    # This also simplifies migration from the JobResult Data field as these were stored as strings.
    log_object = models.CharField(max_length=JOB_LOG_MAX_LOG_OBJECT_LENGTH, blank=True, default="")
    absolute_url = models.CharField(max_length=JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, blank=True, default="")

    is_metadata_associable_model = False

    documentation_static_path = "docs/user-guide/platform-functionality/jobs/models.html"

    def __str__(self):
        return self.message

    class Meta:
        ordering = ["created"]
        get_latest_by = "created"
        verbose_name_plural = "job log entries"
        indexes = [
            models.Index(
                name="extras_joblog_jr_created_idx",
                fields=["job_result", "created"],
            )
        ]


#
# Job Queues
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class JobQueue(PrimaryModel):
    """
    A Job Queue represents a structure that is used to manage, organize and schedule jobs for Nautobot workers.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    queue_type = models.CharField(
        max_length=50,
        choices=JobQueueTypeChoices,
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="job_queues",
        blank=True,
        null=True,
    )

    documentation_static_path = "docs/user-guide/platform-functionality/jobs/jobqueue.html"

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.queue_type}: {self.name}"

    @property
    def display(self):
        if self.queue_type != JobQueueTypeChoices.TYPE_CELERY:
            return f"{self.queue_type}: {self.name}"
        worker_count = get_job_queue_worker_count(job_queue=self)
        workers = "worker" if worker_count == 1 else "workers"
        return f"{self.queue_type}: {self.name} ({worker_count} {workers})"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class JobQueueAssignment(BaseModel):
    """
    Through table model that represents the m2m relationship between jobs and job queues.
    """

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="job_queue_assignments")
    job_queue = models.ForeignKey(JobQueue, on_delete=models.CASCADE, related_name="job_assignments")
    is_metadata_associable_model = False

    class Meta:
        unique_together = ["job", "job_queue"]
        ordering = ["job", "job_queue"]

    def __str__(self):
        return f"{self.job}: {self.job_queue}"


#
# Job results
#


@extras_features(
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
        to="extras.Job", null=True, blank=True, on_delete=models.SET_NULL, related_name="job_results"
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    task_name = models.CharField(  # noqa: DJ001  # django-nullable-model-string-field
        max_length=CHARFIELD_MAX_LENGTH,
        null=True,  # TODO: should this be blank=True instead?
        db_index=True,
        help_text="Registered name of the Celery task for this job. Internal use only.",
    )
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    date_started = models.DateTimeField(null=True, blank=True, db_index=True)
    date_done = models.DateTimeField(null=True, blank=True, db_index=True)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", blank=True, null=True
    )
    status = models.CharField(
        max_length=30,
        choices=JobResultStatusChoices,
        default=JobResultStatusChoices.STATUS_PENDING,
        help_text="Current state of the Job being run",
        db_index=True,
    )
    result = models.JSONField(
        encoder=NautobotKombuJSONEncoder,
        null=True,
        blank=True,
        editable=False,
        verbose_name="Result Data",
        help_text="The data returned by the task",
    )
    worker = models.CharField(  # noqa: DJ001  # django-nullable-model-string-field
        max_length=100,
        default=None,
        null=True,  # TODO: should this be default="", blank=True instead?
    )
    task_args = models.JSONField(blank=True, default=list, encoder=NautobotKombuJSONEncoder)
    task_kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    celery_kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    traceback = models.TextField(blank=True, null=True)  # noqa: DJ001  # django-nullable-model-string-field -- TODO: can we remove null=True?
    meta = models.JSONField(null=True, default=None, editable=False)
    scheduled_job = models.ForeignKey(to="extras.ScheduledJob", on_delete=models.SET_NULL, null=True, blank=True)

    objects = JobResultManager()

    documentation_static_path = "docs/user-guide/platform-functionality/jobs/models.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_job_logs_db = True

    class Meta:
        ordering = ["-date_created"]
        get_latest_by = "date_created"
        indexes = [
            models.Index(
                name="extras_jobresult_rcreated_idx",
                fields=["-date_created"],
            ),
            models.Index(
                name="extras_jr_rdone_idx",
                fields=["-date_done"],
            ),
            models.Index(
                name="extras_jr_statrcreate_idx",
                fields=["status", "-date_created"],
            ),
            models.Index(
                name="extras_jr_statrdone_idx",
                fields=["status", "-date_done"],
            ),
        ]

    natural_key_field_names = ["id"]

    def __str__(self):
        return f"{self.name} created at {self.date_created} ({self.status})"

    def as_dict(self):
        """This is required by the django-celery-results DB backend."""
        return {
            "id": self.id,
            "task_name": self.task_name,
            "task_args": self.task_args,
            "task_kwargs": self.task_kwargs,
            "status": self.status,
            "result": self.result,
            "date_done": self.date_done,
            "traceback": self.traceback,
            "meta": self.meta,
            "worker": self.worker,
        }

    @property
    def duration(self):
        if not self.date_done:
            return None

        # Older records may not have a date_started value, so we use date_created as a fallback.
        duration = self.date_done - (self.date_started or self.date_created)
        minutes, seconds = divmod(duration.total_seconds(), 60)

        return f"{int(minutes)} minutes, {seconds:.2f} seconds"

    # FIXME(jathan): This needs to go away. Need to think about that the impact
    # will be in the JOB_RESULT_METRIC and how to compensate for it.
    def set_status(self, status):
        """
        Helper method to change the status of the job result. If the target status is terminal, the  completion
        time is also set.
        """
        self.status = status
        if status in JobResultStatusChoices.READY_STATES:
            self.date_done = timezone.now()
            # Only add metrics if we have a related job model. If we are moving to a terminal state we should always
            # have a related job model, so this shouldn't be too tight of a restriction.
            if self.job_model:
                # Older records may not have a date_started value, so we use date_created as a fallback.
                duration = self.date_done - (self.date_started or self.date_created)
                JOB_RESULT_METRIC.labels(self.job_model.grouping, self.job_model.name, status).observe(
                    duration.total_seconds()
                )

    set_status.alters_data = True

    @classmethod
    def execute_job(cls, *args, **kwargs):
        """
        Create a JobResult instance and run a job in the current process, blocking until the job finishes.

        Running tasks synchronously in celery is *NOT* supported and if possible `enqueue_job` with synchronous=False
        should be used instead.

        Args: see `enqueue_job()`

        Returns:
            JobResult instance
        """
        return cls.enqueue_job(*args, **kwargs, synchronous=True)

    execute_job.__func__.alters_data = True

    @classmethod
    def enqueue_job(
        cls,
        job_model: Job,
        user: "User",
        *job_args,
        celery_kwargs: Optional[dict] = None,
        profile: bool = False,
        schedule: Optional["ScheduledJob"] = None,
        job_queue: Optional["JobQueue"] = None,
        task_queue: Optional[str] = None,  # deprecated!
        job_result: Optional["JobResult"] = None,
        synchronous: bool = False,
        ignore_singleton_lock: bool = False,
        **job_kwargs,
    ):
        """Create/Modify a JobResult instance and enqueue a job to be executed asynchronously by a Celery worker.

        Args:
            job_model (Job): The Job to be enqueued for execution.
            user (User): User object to link to the JobResult instance.
            celery_kwargs (dict): Dictionary of kwargs to pass as **kwargs to `apply_async()`/`apply()` when job is run.
            profile (bool): If True, dump cProfile stats on the job execution.
            schedule (ScheduledJob): ScheduledJob instance to link to the JobResult.
                Cannot be used with synchronous=True.
            job_queue (JobQueue): Job queue to send the job to. If not set, use the default queue for the given Job.
            task_queue (str): The celery queue name to send the job to. **Deprecated, prefer `job_queue` instead.**
            job_result (JobResult): Existing JobResult with status PENDING, to be modified and to be used
                in kubernetes job execution.
            synchronous (bool): If True, run the job in the current process, blocking until the job completes.
            ignore_singleton_lock (bool): If True, invalidate the singleton lock before running the job.
              This allows singleton jobs to run twice, or makes it possible to remove the lock when the first instance
              of the job failed to remove it for any reason.
            *job_args: positional args passed to the job task (UNUSED)
            **job_kwargs: keyword args passed to the job task

        Returns:
            JobResult instance
        """
        from nautobot.extras.jobs import run_job  # TODO circular import

        if schedule is not None and synchronous:
            raise ValueError("Scheduled jobs cannot be run synchronously")

        if job_queue is not None and task_queue is not None and job_queue.name != task_queue:
            raise ValueError("task_queue and job_queue are mutually exclusive")
        if job_queue is not None and task_queue is None:
            task_queue = job_queue.name
        elif task_queue is not None and job_queue is None:
            job_queue = JobQueue.objects.get(name=task_queue)
        else:  # both none
            if celery_kwargs is not None and "queue" in celery_kwargs:
                task_queue = celery_kwargs["queue"]
                job_queue = JobQueue.objects.get(name=task_queue)
            else:
                job_queue = job_model.default_job_queue
                task_queue = job_queue.name

        if job_result is None:
            job_result = cls.objects.create(
                name=job_model.name,
                job_model=job_model,
                scheduled_job=schedule,
                user=user,
            )
        else:
            if job_result.user != user:
                raise ValueError(
                    f"There is a mismatch between the user specified {user} and the user associated with the job result {job_result.user}"
                )
            if job_result.job_model != job_model:
                raise ValueError(
                    f"There is a mismatch between the job specified {job_model} and the job associated with the job result {job_result.job_model}"
                )

        # Kubernetes Job Queue logic
        # As we execute Kubernetes jobs, we want to execute `run_kubernetes_job_and_return_job_result`
        # the first time the kubernetes job is enqueued to spin up the kubernetes pod.
        # And from the kubernetes pod, we specify "--local"/synchronous=True
        # so that `run_kubernetes_job_and_return_job_result` is not executed again and the job will be run locally.
        if job_queue.queue_type == JobQueueTypeChoices.TYPE_KUBERNETES and not synchronous:
            return run_kubernetes_job_and_return_job_result(job_queue, job_result, json.dumps(job_kwargs))

        job_celery_kwargs = {
            "nautobot_job_job_model_id": job_model.id,
            "nautobot_job_profile": profile,
            "nautobot_job_user_id": user.id,
            "nautobot_job_ignore_singleton_lock": ignore_singleton_lock,
            "queue": task_queue,
        }

        if schedule is not None:
            job_celery_kwargs["nautobot_job_schedule_id"] = schedule.id
        if job_model.soft_time_limit > 0:
            job_celery_kwargs["soft_time_limit"] = job_model.soft_time_limit
        if job_model.time_limit > 0:
            job_celery_kwargs["time_limit"] = job_model.time_limit

        if celery_kwargs is not None:
            # TODO: this lets celery_kwargs override keys like `queue` and `nautobot_job_user_id`; is that desirable?
            job_celery_kwargs.update(celery_kwargs)

        if synchronous:
            # synchronous tasks are run before the JobResult is saved, so any fields required by
            # the job must be added before calling `apply()`
            job_result.celery_kwargs = job_celery_kwargs
            job_result.date_started = timezone.now()
            job_result.save()

            # setup synchronous task logging
            setup_nautobot_job_logging(None, None, app.conf)

            # redirect stdout/stderr to logger and run task
            redirect_logger = get_logger("celery.redirected")
            proxy = LoggingProxy(redirect_logger, app.conf.worker_redirect_stdouts_level)
            with contextlib.redirect_stdout(proxy), contextlib.redirect_stderr(proxy):

                def alarm_handler(*args, **kwargs):
                    raise SoftTimeLimitExceeded()

                # Set alarm_handler to be called on a SIGALRM, and schedule a SIGALRM based on the soft time limit
                signal.signal(signal.SIGALRM, alarm_handler)
                signal.alarm(int(job_model.soft_time_limit) or settings.CELERY_TASK_SOFT_TIME_LIMIT)

                try:
                    eager_result = run_job.apply(
                        args=[job_model.class_path, *job_args],
                        kwargs=job_kwargs,
                        task_id=str(job_result.id),
                        **job_celery_kwargs,
                    )
                finally:
                    # Cancel the scheduled SIGALRM if it hasn't fired already
                    signal.alarm(0)

            job_result.refresh_from_db()
            # copy from eager result to job result if and only if the job result isn't already in a proper state.
            if JobResultStatusChoices.precedence(job_result.status) > JobResultStatusChoices.precedence(
                eager_result.status
            ):
                if eager_result.status in JobResultStatusChoices.EXCEPTION_STATES and isinstance(
                    eager_result.result, Exception
                ):
                    job_result.result = {
                        "exc_type": type(eager_result.result).__name__,
                        "exc_message": sanitize(str(eager_result.result)),
                    }
                elif eager_result.result is not None:
                    job_result.result = sanitize(eager_result.result)
                job_result.status = eager_result.status
                if (
                    eager_result.status in JobResultStatusChoices.EXCEPTION_STATES
                    and eager_result.traceback is not None
                ):
                    job_result.traceback = sanitize(eager_result.traceback)
            if not job_result.date_done:
                job_result.date_done = timezone.now()
            job_result.save()
        else:
            # Jobs queued inside of a transaction need to run after the transaction completes and the JobResult is saved to the database
            transaction.on_commit(
                lambda: run_job.apply_async(
                    args=[job_model.class_path, *job_args],
                    kwargs=job_kwargs,
                    task_id=str(job_result.id),
                    **job_celery_kwargs,
                )
            )

        return job_result

    enqueue_job.__func__.alters_data = True

    def log(
        self,
        message,
        obj=None,
        level_choice=LogLevelChoices.LOG_INFO,
        grouping="main",
    ):
        """
        General-purpose API for creating JobLogEntry records associated with a JobResult.

        message (str): Message to log (an attempt will be made to sanitize sensitive information from this message)
        obj (object): Object associated with this message, if any
        level_choice (LogLevelChoices): Message severity level
        grouping (str): Grouping to store the log message under
        """
        if level_choice not in LogLevelChoices.as_dict():
            raise ValueError(f"Unknown logging level: {level_choice}")

        message = sanitize(str(message))

        try:
            log = JobLogEntry(
                job_result=self,
                log_level=level_choice,
                grouping=grouping[:JOB_LOG_MAX_GROUPING_LENGTH],
                message=message,
                created=timezone.now().isoformat(),
                log_object=str(obj)[:JOB_LOG_MAX_LOG_OBJECT_LENGTH] if obj else "",
                absolute_url=obj.get_absolute_url()[:JOB_LOG_MAX_ABSOLUTE_URL_LENGTH]
                if hasattr(obj, "get_absolute_url")
                else "",
            )
        except (AttributeError, NotImplementedError):
            log = JobLogEntry(
                job_result=self,
                log_level=level_choice,
                grouping=grouping[:JOB_LOG_MAX_GROUPING_LENGTH],
                message=message,
                created=timezone.now().isoformat(),
                log_object=str(obj)[:JOB_LOG_MAX_LOG_OBJECT_LENGTH] if obj else "",
                absolute_url="",
            )
        # If the override is provided, we want to use the default database(pass no using argument)
        # Otherwise we want to use a separate database here so that the logs are created immediately
        # instead of within transaction.atomic(). This allows us to be able to report logs when the jobs
        # are running, and allow us to rollback the database without losing the log entries.
        if not self.use_job_logs_db or not JOB_LOGS:
            log.save()
        else:
            log.save(using=JOB_LOGS)

    log.alters_data = True


#
# Job Button
#


@extras_features("graphql")
class JobButton(ContactMixin, ChangeLoggedModel, DynamicGroupsModelMixin, NotesMixin, BaseModel):
    """
    A predefined button that includes all information to run a Nautobot Job based on a single object as a source.

    The button text field accepts Jinja2 template code to be rendered with an object as context.
    """

    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="job_buttons",
        verbose_name="Object types",
        help_text="The object type(s) to which this job button applies.",
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    enabled = models.BooleanField(default=True)
    text = models.CharField(
        max_length=500,
        help_text="Jinja2 template code for button text. Reference the object as <code>{{ obj }}</code> such as <code>{{ obj.platform.name }}</code>. Buttons which render as empty text will not be displayed.",
    )
    job = models.ForeignKey(
        to="extras.Job",
        on_delete=models.CASCADE,
        help_text="Job this button will run",
        limit_choices_to={"is_job_button_receiver": True},
    )
    weight = models.PositiveSmallIntegerField(default=100)
    group_name = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        help_text="Buttons with the same group will appear as a dropdown menu. Group dropdown buttons will inherit the button class from the button with the lowest weight in the group.",
    )
    button_class = models.CharField(
        max_length=30,
        choices=ButtonClassChoices,
        default=ButtonClassChoices.CLASS_DEFAULT,
    )
    confirmation = models.BooleanField(
        help_text="Enable confirmation pop-up box. <span class='text-danger'>WARNING: unselecting this option will allow the Job to run (and commit changes) with a single click!</span>",
        default=True,
    )

    documentation_static_path = "docs/user-guide/platform-functionality/jobs/jobbutton.html"

    class Meta:
        ordering = ["group_name", "weight", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.enabled and not (self.job.installed and self.job.enabled):
            raise ValidationError({"enabled": "The selected Job is not installed and enabled"})


class ScheduledJobs(models.Model):
    """Helper table for tracking updates to scheduled tasks.
    This stores a single row with ident=1.  last_update is updated
    via django signals whenever anything is changed in the ScheduledJob model.
    Basically this acts like a DB data audit trigger.
    Doing this so we also track deletions, and not just insert/update.
    """

    ident = models.SmallIntegerField(default=1, primary_key=True, unique=True)
    last_update = models.DateTimeField(null=False)

    objects = ScheduledJobsManager()

    def __str__(self):
        return str(self.ident)

    @classmethod
    def changed(cls, instance, raw=False, **kwargs):
        """This function acts as a signal handler to track changes to the scheduled job that is triggered before a change"""
        if raw:
            return
        if not instance.no_changes:
            cls.update_changed()

    changed.__func__.alters_data = True

    @classmethod
    def update_changed(cls, raw=False, **kwargs):
        """This function acts as a signal handler to track changes to the scheduled job that is triggered after a change"""
        if raw:
            return
        cls.objects.update_or_create(ident=1, defaults={"last_update": timezone.now()})

    update_changed.__func__.alters_data = True

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
        max_length=CHARFIELD_MAX_LENGTH,
        verbose_name="Name",
        help_text="Human-readable description of this scheduled task",
        unique=True,
    )
    task = models.CharField(
        # JOB_MAX_NAME_LENGTH is the longest permitted module name as well as the longest permitted class name,
        # so we need to permit a task name of MAX.MAX at a minimum:
        max_length=JOB_MAX_NAME_LENGTH + 1 + JOB_MAX_NAME_LENGTH,
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
    interval = models.CharField(choices=JobExecutionType, max_length=255)
    args = models.JSONField(blank=True, default=list, encoder=NautobotKombuJSONEncoder)
    kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    celery_kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    job_queue = models.ForeignKey(
        to="extras.JobQueue",
        on_delete=models.SET_NULL,
        related_name="scheduled_jobs",
        null=True,
        blank=True,
        verbose_name="Job Queue Override",
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
    # Django always stores DateTimeField as UTC internally, but we want scheduled jobs to respect DST and similar,
    # so we need to store the time zone the job was scheduled under as well.
    time_zone = TimeZoneField(default=timezone.get_default_timezone_name)
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
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        verbose_name="Custom cronjob",
        help_text="Cronjob syntax string for custom scheduling",
    )

    objects = BaseManager.from_queryset(ScheduledJobExtendedQuerySet)()
    no_changes = False

    documentation_static_path = "docs/user-guide/platform-functionality/jobs/job-scheduling-and-approvals.html"

    def __str__(self):
        return f"{self.name}: {self.interval}"

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        # make sure non-valid crontab doesn't get saved
        if self.interval == JobExecutionType.TYPE_CUSTOM:
            try:
                self.get_crontab(self.crontab, tz=self.time_zone)
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

    @property
    def queue(self) -> str:
        """Deprecated backward-compatibility property for the queue name this job is scheduled for."""
        return self.job_queue.name if self.job_queue else ""

    @queue.setter
    def queue(self, value: str):
        if value:
            try:
                self.job_queue = JobQueue.objects.get(name=value)
            except JobQueue.DoesNotExist:
                raise ValidationError(f"Job Queue {value} does not exist in the database.")

    @staticmethod
    def earliest_possible_time():
        return timezone.now() + timedelta(seconds=15)

    @classmethod
    def get_crontab(cls, crontab, tz=None):
        """
        Wrapper method translates crontab syntax to Celery crontab.

        Supports following symbols:

        • Asterisk (*) - signifies all possible values
        • Comma (,) - lists multiple values
        • Hyphen (-) - determine a range of values
        • Slash (/) - divide a value ({*/15 * * * *} runs every 15 minutes)

        No support for Last (L), Weekday (W), Number symbol (#), Question mark (?), and special @ strings.
        """
        if not tz:
            tz = timezone.get_default_timezone()
        minute, hour, day_of_month, month_of_year, day_of_week = crontab.split(" ")

        return TzAwareCrontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week,
            tz=tz,
        )

    @classmethod
    def create_schedule(
        cls,
        job_model,
        user,
        name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        interval: str = JobExecutionType.TYPE_IMMEDIATELY,
        crontab: str = "",
        profile: bool = False,
        approval_required: bool = False,
        job_queue: Optional[JobQueue] = None,
        task_queue: Optional[str] = None,  # deprecated!
        ignore_singleton_lock: bool = False,
        **job_kwargs,
    ):
        """
        Schedule a job with the specified parameters.

        This method creates a schedule for a job to be executed at a specific time
        or interval. It handles immediate execution, custom start times, and
        crontab-based scheduling.

        Parameters:
            job_model (JobModel): The job model instance.
            user (User): The user who is scheduling the job.
            name (str): The name of the scheduled job. Automatically derived from the job_model and start_time if unset.
            start_time (datetime): The start time for the job. Defaults to the current time if unset.
            interval (JobExecutionType): The interval type for the job execution.
                Defaults to JobExecutionType.TYPE_IMMEDIATELY.
            crontab (str): The crontab string for the schedule. Defaults to "".
            profile (bool): Flag indicating whether to profile the job. Defaults to False.
            approval_required (bool): Flag indicating if approval is required. Defaults to False.
            job_queue (JobQueue): The Job queue to use. If unset, use the configured default celery queue.
            task_queue (str): The queue name to use. **Deprecated, prefer `job_queue`.**
            ignore_singleton_lock (bool): Whether to ignore singleton locks. Defaults to False.
            **job_kwargs: Additional keyword arguments to pass to the job.

        Returns:
            ScheduledJob instance
        """

        if job_queue is not None and task_queue is not None and job_queue.name != task_queue:
            raise ValueError("task_queue and job_queue are mutually exclusive")
        if job_queue is not None and task_queue is None:
            task_queue = job_queue.name
        elif task_queue is not None and job_queue is None:
            job_queue = JobQueue.objects.get(name=task_queue)
        else:  # both None
            job_queue = job_model.default_job_queue
            task_queue = job_queue.name

        if interval == JobExecutionType.TYPE_IMMEDIATELY:
            start_time = timezone.localtime()
            name = name or f"{job_model.name} - {start_time}"
        elif interval == JobExecutionType.TYPE_CUSTOM:
            if start_time is None:
                # "start_time" is checked against models.ScheduledJob.earliest_possible_time()
                # which returns timezone.now() + timedelta(seconds=15)
                start_time = timezone.localtime() + timedelta(seconds=20)

        celery_kwargs = {
            "nautobot_job_profile": profile,
            "queue": task_queue,
            "nautobot_job_ignore_singleton_lock": ignore_singleton_lock,
        }
        if job_model.soft_time_limit > 0:
            celery_kwargs["soft_time_limit"] = job_model.soft_time_limit
        if job_model.time_limit > 0:
            celery_kwargs["time_limit"] = job_model.time_limit

        # We do this because when a job creates an approval workflow, a scheduled job is also created.
        # If the scheduled job has an "immediate" interval, the scheduler will not send this task.
        # since TYPE_IMMEDIATELY is not a valid value in JobExecutionType.SCHEDULE_CHOICES
        if interval == JobExecutionType.TYPE_IMMEDIATELY:
            interval = JobExecutionType.TYPE_FUTURE
        # 2.0 TODO: To revisit this as part of a larger Jobs cleanup in 2.0.
        #
        # We pass in task and job_model here partly for forward/backward compatibility logic, and
        # part fallback safety. It's mildly useful to store both the task module/class name and the JobModel
        # FK on the ScheduledJob, as in the case where the JobModel gets deleted (and the FK becomes
        # null) you still have a bit of context on the ScheduledJob as to what it was originally
        # scheduled for.
        scheduled_job = cls(
            name=name,
            task=job_model.class_path,
            job_model=job_model,
            start_time=start_time,
            time_zone=start_time.tzinfo,
            description=f"Nautobot job {name} scheduled by {user} for {start_time}",
            kwargs=job_kwargs,
            celery_kwargs=celery_kwargs,
            interval=interval,
            one_off=(interval == JobExecutionType.TYPE_FUTURE),
            user=user,
            approval_required=approval_required,
            crontab=crontab,
            job_queue=job_queue,
        )
        scheduled_job.validated_save()
        return scheduled_job

    create_schedule.__func__.alters_data = True

    def to_cron(self):
        tz = self.time_zone
        t = self.start_time.astimezone(tz)  # pylint: disable=no-member
        if self.interval == JobExecutionType.TYPE_HOURLY:
            return TzAwareCrontab(minute=t.minute, tz=tz)
        elif self.interval == JobExecutionType.TYPE_DAILY:
            return TzAwareCrontab(minute=t.minute, hour=t.hour, tz=tz)
        elif self.interval == JobExecutionType.TYPE_WEEKLY:
            return TzAwareCrontab(minute=t.minute, hour=t.hour, day_of_week=t.strftime("%w"), tz=tz)
        elif self.interval == JobExecutionType.TYPE_CUSTOM:
            return self.get_crontab(self.crontab, tz=tz)
        raise ValueError(f"I do not know to convert {self.interval} to a Cronjob!")


signals.pre_delete.connect(ScheduledJobs.changed, sender=ScheduledJob)
signals.pre_save.connect(ScheduledJobs.changed, sender=ScheduledJob)
signals.post_save.connect(ScheduledJobs.update_changed, sender=ScheduledJob)
