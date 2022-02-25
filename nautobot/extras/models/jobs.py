# Data models relating to Jobs

from datetime import timedelta
import logging
import uuid

from celery import schedules

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import signals
from django.urls import reverse
from django.utils import timezone

from django_celery_beat.clockedschedule import clocked
from django_celery_beat.managers import ExtendedManager

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.models import BaseModel
from nautobot.extras.choices import LogLevelChoices, JobExecutionType, JobResultStatusChoices
from nautobot.extras.constants import (
    JOB_LOG_MAX_ABSOLUTE_URL_LENGTH,
    JOB_LOG_MAX_GROUPING_LENGTH,
    JOB_LOG_MAX_LOG_OBJECT_LENGTH,
)
from nautobot.extras.querysets import ScheduledJobExtendedQuerySet
from nautobot.extras.utils import extras_features, FeatureQuery

from .customfields import CustomFieldModel

# The JOB_LOGS variable is used to tell the JobLogEntry model the database to store to.
# We default this to job_logs, and creating at the Global level allows easy override
# during testing. This needs to point to the same physical database so that the
# foreign key relationship works, but needs its own connection to avoid JobLogEntry
# objects being created within transaction.atomic().
JOB_LOGS = "job_logs"


@extras_features("job_results")
class Job(models.Model):
    """
    Virtual model used to generate permissions for jobs. Does not exist in the database.
    """

    class Meta:
        managed = False


@extras_features(
    "graphql",
)
class JobLogEntry(BaseModel):
    """Stores each log entry for the JobResult."""

    job_result = models.ForeignKey(to="extras.JobResult", on_delete=models.CASCADE, related_name="logs")
    log_level = models.CharField(max_length=32, choices=LogLevelChoices, default=LogLevelChoices.LOG_DEFAULT)
    grouping = models.CharField(max_length=JOB_LOG_MAX_GROUPING_LENGTH, default="main")
    message = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)
    # Storing both of the below as strings instead of using GenericForeignKey to support
    # compatibility with existing JobResult logs. GFK would pose a problem with dangling foreign-key
    # references, whereas this allows us to retain all records for as long as the entry exists.
    # This also simplifies migration from the JobResult Data field as these were stored as strings.
    log_object = models.CharField(max_length=JOB_LOG_MAX_LOG_OBJECT_LENGTH, null=True, blank=True)
    absolute_url = models.CharField(max_length=JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, null=True, blank=True)

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
    "custom_fields",
    "custom_links",
    "graphql",
)
class JobResult(BaseModel, CustomFieldModel):
    """
    This model stores the results from running a user-defined report.
    """

    name = models.CharField(max_length=255)
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
    status = models.CharField(
        max_length=30,
        choices=JobResultStatusChoices,
        default=JobResultStatusChoices.STATUS_PENDING,
    )
    data = models.JSONField(encoder=DjangoJSONEncoder, null=True, blank=True)
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
        """
        from nautobot.extras.jobs import get_job  # needed here to avoid a circular import issue

        if self.obj_type == ContentType.objects.get(app_label="extras", model="job"):
            # Related object is an extras.Job subclass, our `name` matches its `class_path`
            return get_job(self.name)

        model_class = self.obj_type.model_class()

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
        """
        related_object = self.related_object
        if not related_object:
            return self.name
        if hasattr(related_object, "name"):
            return related_object.name
        return str(related_object)

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
    def enqueue_job(cls, func, name, obj_type, user, celery_kwargs=None, *args, schedule=None, **kwargs):
        """
        Create a JobResult instance and enqueue a job using the given callable

        func: The callable object to be enqueued for execution
        name: Name for the JobResult instance
        obj_type: ContentType to link to the JobResult instance obj_type
        user: User object to link to the JobResult instance
        celery_kwargs: Dictionary of kwargs to pass as **kwargs to Celery when job is queued
        args: additional args passed to the callable
        schedule: Optional ScheduledJob instance to link to the JobResult
        kwargs: additional kwargs passed to the callable
        """
        from nautobot.extras.jobs import get_job  # needed here to avoid a circular import issue

        job_result = cls.objects.create(name=name, obj_type=obj_type, user=user, job_id=uuid.uuid4(), schedule=schedule)

        kwargs["job_result_pk"] = job_result.pk

        # Prepare kwargs that will be sent to Celery
        if celery_kwargs is None:
            celery_kwargs = {}

        job = get_job(name)
        if job is not None:
            if hasattr(job.Meta, "soft_time_limit"):
                celery_kwargs["soft_time_limit"] = job.Meta.soft_time_limit
            if hasattr(job.Meta, "time_limit"):
                celery_kwargs["time_limit"] = job.Meta.time_limit

        func.apply_async(args=args, kwargs=kwargs, task_id=str(job_result.job_id), **celery_kwargs)

        return job_result

    def log(
        self,
        message,
        obj=None,
        level_choice=LogLevelChoices.LOG_DEFAULT,
        grouping="main",
        logger=None,
    ):
        """
        General-purpose API for storing log messages in a JobResult's 'data' field.

        message (str): Message to log
        obj (object): Object associated with this message, if any
        level_choice (LogLevelChoices): Message severity level
        grouping (str): Grouping to store the log message under
        logger (logging.logger): Optional logger to also output the message to
        """
        if level_choice not in LogLevelChoices.as_dict():
            raise Exception(f"Unknown logging level: {level_choice}")

        log = JobLogEntry(
            job_result=self,
            log_level=level_choice,
            grouping=grouping[:JOB_LOG_MAX_GROUPING_LENGTH],
            message=str(message),
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
            logger.log(log_level, str(message))


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
        max_length=200,
        verbose_name="Name",
        help_text="Short Description For This Task",
    )
    task = models.CharField(
        max_length=200,
        verbose_name="Task Name",
        help_text='The name of the Celery task that should be run. (Example: "proj.tasks.import_contacts")',
    )
    job_class = models.CharField(
        max_length=255, verbose_name="Job Class", help_text="Name of the fully qualified Nautobot Job class path"
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
    approval_required = models.BooleanField(default=False)
    approved_at = models.DateTimeField(
        editable=False,
        blank=True,
        null=True,
        verbose_name="Approval date/time",
        help_text="Datetime that the schedule was approved",
    )

    objects = ScheduledJobExtendedQuerySet.as_manager()
    no_changes = False

    def __str__(self):
        return f"{self.name}: {self.interval}"

    def get_absolute_url(self):
        return reverse("extras:scheduledjob", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        self.queue = self.queue or None
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

    def to_cron(self):
        t = self.start_time
        if self.interval == JobExecutionType.TYPE_HOURLY:
            return schedules.crontab(minute=t.minute)
        elif self.interval == JobExecutionType.TYPE_DAILY:
            return schedules.crontab(minute=t.minute, hour=t.hour)
        elif self.interval == JobExecutionType.TYPE_WEEKLY:
            return schedules.crontab(minute=t.minute, hour=t.hour, day_of_week=t.weekday())
        raise ValueError(f"I do not know to convert {self.interval} to a Cronjob!")


signals.pre_delete.connect(ScheduledJobs.changed, sender=ScheduledJob)
signals.pre_save.connect(ScheduledJobs.changed, sender=ScheduledJob)
signals.post_save.connect(ScheduledJobs.update_changed, sender=ScheduledJob)
