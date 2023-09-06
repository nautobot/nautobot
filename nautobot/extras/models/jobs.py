# Data models relating to Jobs

import contextlib
from datetime import timedelta
import logging

from celery import schedules
from celery.utils.log import get_logger, LoggingProxy
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import signals
from django.utils import timezone
from django.utils.functional import cached_property
from django_celery_beat.clockedschedule import clocked
from prometheus_client import Histogram

from nautobot.core.celery import (
    app,
    NautobotKombuJSONEncoder,
    setup_nautobot_job_logging,
)
from nautobot.core.celery.control import refresh_git_repository
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.fields import JSONArrayField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.utils.logging import sanitize
from nautobot.extras.choices import (
    ButtonClassChoices,
    JobExecutionType,
    JobResultStatusChoices,
    LogLevelChoices,
)
from nautobot.extras.constants import (
    JOB_LOG_MAX_ABSOLUTE_URL_LENGTH,
    JOB_LOG_MAX_GROUPING_LENGTH,
    JOB_LOG_MAX_LOG_OBJECT_LENGTH,
    JOB_MAX_GROUPING_LENGTH,
    JOB_MAX_NAME_LENGTH,
    JOB_OVERRIDABLE_FIELDS,
)
from nautobot.extras.models import ChangeLoggedModel, GitRepository
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.managers import JobResultManager, ScheduledJobsManager
from nautobot.extras.querysets import JobQuerySet, ScheduledJobExtendedQuerySet
from nautobot.extras.utils import (
    ChangeLoggedModelsQuery,
    extras_features,
)

from .customfields import CustomFieldModel


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
        max_length=JOB_MAX_GROUPING_LENGTH,
        help_text="Human-readable grouping that this job belongs to",
        db_index=True,
    )
    name = models.CharField(
        max_length=JOB_MAX_NAME_LENGTH,
        help_text="Human-readable name of this job",
        unique=True,
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

    is_job_button_receiver = models.BooleanField(
        default=False, editable=False, help_text="Whether this job is a job button receiver"
    )

    has_sensitive_variables = models.BooleanField(
        default=True, help_text="Whether this job contains sensitive variables"
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
    task_queues = JSONArrayField(
        base_field=models.CharField(max_length=100, blank=True),
        default=list,
        blank=True,
        help_text="Comma separated list of task queues that this job can run on. A blank list will use the default queue",
    )
    supports_dryrun = models.BooleanField(
        default=False,
        editable=False,
        help_text="If supported, allows the job to bypass approval when running with dryrun argument set to true",
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
    task_queues_override = models.BooleanField(
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

    @cached_property
    def job_class(self):
        """Get the Job class (source code) associated with this Job model."""
        if not self.installed:
            return None
        try:
            return self.job_task.__class__
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
        """Get the registered Celery task, refreshing it if necessary."""
        if self.git_repository is not None:
            # If this Job comes from a Git repository, make sure we have the correct version of said code.
            refresh_git_repository(
                state=None, repository_pk=self.git_repository.pk, head=self.git_repository.current_head
            )
        return app.tasks[f"{self.module_name}.{self.job_class_name}"]

    def clean(self):
        """For any non-overridden fields, make sure they get reset to the actual underlying class value if known."""
        if self.job_class is not None:
            for field_name in JOB_OVERRIDABLE_FIELDS:
                if not getattr(self, f"{field_name}_override", False):
                    setattr(self, field_name, getattr(self.job_class, field_name))

        # Protect against invalid input when auto-creating Job records
        if len(self.module_name) > JOB_MAX_NAME_LENGTH:
            raise ValidationError(f"Module name may not exceed {JOB_MAX_NAME_LENGTH} characters in length")
        if len(self.job_class_name) > JOB_MAX_NAME_LENGTH:
            raise ValidationError(f"Job class name may not exceed {JOB_MAX_NAME_LENGTH} characters in length")
        if len(self.grouping) > JOB_MAX_GROUPING_LENGTH:
            raise ValidationError(f"Grouping may not exceed {JOB_MAX_GROUPING_LENGTH} characters in length")
        if len(self.name) > JOB_MAX_NAME_LENGTH:
            raise ValidationError(f"Name may not exceed {JOB_MAX_NAME_LENGTH} characters in length")

        if self.has_sensitive_variables is True and self.approval_required is True:
            raise ValidationError(
                {"approval_required": "A job that may have sensitive variables cannot be marked as requiring approval"}
            )


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
    name = models.CharField(max_length=100, unique=True)
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
    created = models.DateTimeField(default=timezone.now)
    # Storing both of the below as strings instead of using GenericForeignKey to support
    # compatibility with existing JobResult logs. GFK would pose a problem with dangling foreign-key
    # references, whereas this allows us to retain all records for as long as the entry exists.
    # This also simplifies migration from the JobResult Data field as these were stored as strings.
    log_object = models.CharField(max_length=JOB_LOG_MAX_LOG_OBJECT_LENGTH, blank=True, default="")
    absolute_url = models.CharField(max_length=JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, blank=True, default="")

    documentation_static_path = "docs/user-guide/platform-functionality/jobs/models.html"

    def __str__(self):
        return self.message

    class Meta:
        ordering = ["created"]
        get_latest_by = "created"
        verbose_name_plural = "job log entries"


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
    name = models.CharField(max_length=255, db_index=True)
    task_name = models.CharField(
        max_length=255,
        null=True,
        db_index=True,
        help_text="Registered name of the Celery task for this job. Internal use only.",
    )
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
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
    worker = models.CharField(max_length=100, default=None, null=True)
    task_args = models.JSONField(blank=True, default=list, encoder=NautobotKombuJSONEncoder)
    task_kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    celery_kwargs = models.JSONField(blank=True, default=dict, encoder=NautobotKombuJSONEncoder)
    traceback = models.TextField(blank=True, null=True)
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
        return f"{self.name} started at {self.date_created} ({self.status})"

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

        duration = self.date_done - self.date_created
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
                duration = self.date_done - self.created
                JOB_RESULT_METRIC.labels(self.job_model.grouping, self.job_model.name, status).observe(
                    duration.total_seconds()
                )

    @classmethod
    def execute_job(cls, job_model, user, *job_args, celery_kwargs=None, profile=False, **job_kwargs):
        """
        Create a JobResult instance and run a job in the current process, blocking until the job finishes.

        Running tasks synchronously in celery is *NOT* supported and if possible `enqueue_job` with synchronous=False
        should be used instead.

        Args:
            job_model (Job): The Job to be enqueued for execution
            user (User): User object to link to the JobResult instance
            celery_kwargs (dict, optional): Dictionary of kwargs to pass as **kwargs to Celery when job is run
            profile (bool, optional): Whether to run cProfile on the job execution
            *job_args: positional args passed to the job task
            **job_kwargs: keyword args passed to the job task

        Returns:
            JobResult instance
        """
        return cls.enqueue_job(
            job_model, user, *job_args, celery_kwargs=celery_kwargs, profile=profile, synchronous=True, **job_kwargs
        )

    @classmethod
    def enqueue_job(
        cls,
        job_model,
        user,
        *job_args,
        celery_kwargs=None,
        profile=False,
        schedule=None,
        task_queue=None,
        synchronous=False,
        **job_kwargs,
    ):
        """Create a JobResult instance and enqueue a job to be executed asynchronously by a Celery worker.

        Args:
            job_model (Job): The Job to be enqueued for execution.
            user (User): User object to link to the JobResult instance.
            celery_kwargs (dict, optional): Dictionary of kwargs to pass as **kwargs to `apply_async()`/`apply()` when job is run.
            profile (bool, optional): If True, dump cProfile stats on the job execution.
            schedule (ScheduledJob, optional): ScheduledJob instance to link to the JobResult. Cannot be used with synchronous=True.
            task_queue (str, optional): The celery queue to send the job to. If not set, use the default celery queue.
            synchronous (bool, optional): If True, run the job in the current process, blocking until the job completes.
            *job_args: positional args passed to the job task
            **job_kwargs: keyword args passed to the job task

        Returns:
            JobResult instance
        """
        if schedule is not None and synchronous:
            raise ValueError("Scheduled jobs cannot be run synchronously")

        job_result = cls.objects.create(
            name=job_model.name,
            job_model=job_model,
            scheduled_job=schedule,
            user=user,
        )

        if task_queue is None:
            task_queue = settings.CELERY_TASK_DEFAULT_QUEUE

        job_celery_kwargs = {
            "nautobot_job_job_model_id": job_model.id,
            "nautobot_job_profile": profile,
            "nautobot_job_user_id": user.id,
            "queue": task_queue,
        }

        if schedule is not None:
            job_celery_kwargs["nautobot_job_schedule_id"] = schedule.id
        if job_model.soft_time_limit > 0:
            job_celery_kwargs["soft_time_limit"] = job_model.soft_time_limit
        if job_model.time_limit > 0:
            job_celery_kwargs["time_limit"] = job_model.time_limit

        if celery_kwargs is not None:
            job_celery_kwargs.update(celery_kwargs)

        if synchronous:
            # synchronous tasks are run before the JobResult is saved, so any fields required by
            # the job must be added before calling `apply()`
            job_result.celery_kwargs = job_celery_kwargs
            job_result.save()

            # setup synchronous task logging
            setup_nautobot_job_logging(None, None, app.conf)

            # redirect stdout/stderr to logger and run task
            redirect_logger = get_logger("celery.redirected")
            proxy = LoggingProxy(redirect_logger, app.conf.worker_redirect_stdouts_level)
            with contextlib.redirect_stdout(proxy), contextlib.redirect_stderr(proxy):
                eager_result = job_model.job_task.apply(
                    args=job_args, kwargs=job_kwargs, task_id=str(job_result.id), **job_celery_kwargs
                )

            # copy fields from eager result to job result
            job_result.refresh_from_db()
            for field in ["status", "result", "traceback", "worker"]:
                setattr(job_result, field, getattr(eager_result, field, None))
            job_result.date_done = timezone.now()
            job_result.save()
        else:
            # Jobs queued inside of a transaction need to run after the transaction completes and the JobResult is saved to the database
            transaction.on_commit(
                lambda: job_model.job_task.apply_async(
                    args=job_args, kwargs=job_kwargs, task_id=str(job_result.id), **job_celery_kwargs
                )
            )

        return job_result

    def log(
        self,
        message,
        obj=None,
        level_choice=LogLevelChoices.LOG_INFO,
        grouping="main",
    ):
        """
        General-purpose API for storing log messages in a JobResult's 'data' field.

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
        except NotImplementedError:
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


#
# Job Button
#


@extras_features("graphql")
class JobButton(BaseModel, ChangeLoggedModel, NotesMixin):
    """
    A predefined button that includes all necessary information to run a Nautobot Job based on a single object as a source.
    The button text field accepts Jinja2 template code to be rendered with an object as context.
    """

    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="job_buttons",
        verbose_name="Object types",
        help_text="The object type(s) to which this job button applies.",
    )
    name = models.CharField(max_length=100, unique=True)
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
        max_length=50,
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

    @classmethod
    def changed(cls, instance, raw=False, **kwargs):
        """This function acts as a signal handler to track changes to the scheduled job that is triggered before a change"""
        if raw:
            return
        if not instance.no_changes:
            cls.update_changed()

    @classmethod
    def update_changed(cls, raw=False, **kwargs):
        """This function acts as a signal handler to track changes to the scheduled job that is triggered after a change"""
        if raw:
            return
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
        max_length=200, verbose_name="Name", help_text="Human-readable description of this scheduled task", unique=True
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
    queue = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Queue Override",
        help_text="Queue defined in CELERY_TASK_QUEUES. Leave empty for default queuing.",
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

    objects = BaseManager.from_queryset(ScheduledJobExtendedQuerySet)()
    no_changes = False

    documentation_static_path = "docs/user-guide/platform-functionality/jobs/job-scheduling-and-approvals.html"

    def __str__(self):
        return f"{self.name}: {self.interval}"

    def save(self, *args, **kwargs):
        self.queue = self.queue or ""
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
