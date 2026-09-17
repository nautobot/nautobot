from collections.abc import Mapping
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys

from celery import current_app
from celery.beat import _evaluate_entry_args, _evaluate_entry_kwargs, reraise, SchedulingError
from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from django_celery_beat.schedulers import DatabaseScheduler, ModelEntry
from kombu.utils.json import loads

from nautobot.extras.choices import (
    JobQueueTypeChoices,
    JobResultStatusChoices,
    LogLevelChoices,
    ScheduledJobStateChoices,
)
from nautobot.extras.constants import JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, JOB_LOG_MAX_LOG_OBJECT_LENGTH
from nautobot.extras.models import JobLogEntry, JobResult, ScheduledJob, ScheduledJobs
from nautobot.extras.utils import run_kubernetes_job_and_return_job_result

logger = logging.getLogger(__name__)


def _user_exists(user_id):
    """Return True if `user_id` is non-null and references an existing user row."""
    if user_id is None:
        return False
    return get_user_model().objects.filter(pk=user_id).exists()


def _record_missing_user_failure(model):
    """
    Record a failed JobResult for a ScheduledJob whose originating user is missing.

    Used when celery beat fires a schedule whose `user` FK is null or refers to a
    deleted user. We create a JobResult marked FAILURE so administrators have a
    durable record of the missed run instead of a silent failure.

    Also clears the in-memory `user_id` so that subsequent `model.save()` calls
    (e.g. from `_disable`) cannot raise an FK violation when the FK is orphaned.
    """
    # If user_id points to a row that no longer exists (FK orphan, e.g. user was deleted via
    # raw SQL bypassing on_delete=SET_NULL), any save() of this model will raise an
    # IntegrityError. Patch the DB directly via queryset update, then null in-memory.
    if model.user_id is not None:
        ScheduledJob.objects.filter(pk=model.pk).update(user=None)
        model.user_id = None

    if model.job_model is None:
        # Can't create a JobResult without a job_model FK; the scheduler will disable
        # the entry below, which is the best we can do.
        return
    err_message = (
        f"Scheduled job '{model.name}' cannot run: the originating user has been removed. "
        "Use 'Assume Ownership' on the scheduled job detail view to reassign it."
    )
    try:
        timestamp = timezone.now()
        job_result = JobResult.objects.create(
            name=model.job_model.name,
            job_model=model.job_model,
            scheduled_job=model,
            user=None,
            task_name=model.job_model.class_path,
            status=JobResultStatusChoices.STATUS_FAILURE,
            date_started=timestamp,
            date_done=timestamp,
            traceback=err_message,
            # We are intentionally omitting JobResult fields that are not necessary
            # as we only need it to create a JobLogEntry to log the failure.
        )
        log_object = str(model)[:JOB_LOG_MAX_LOG_OBJECT_LENGTH]
        absolute_url = model.get_absolute_url()[:JOB_LOG_MAX_ABSOLUTE_URL_LENGTH]
        JobLogEntry.objects.create(
            job_result=job_result,
            log_level=LogLevelChoices.LOG_ERROR,
            grouping="main",
            message=err_message,
            log_object=log_object,
            absolute_url=absolute_url,
        )
        job_result.count_logs_by_level()
        job_result.save()
    except Exception:  # pylint: disable=broad-except
        # Never let a bookkeeping failure crash celery beat itself.
        logger.exception("Failed to record missing-user JobResult for schedule %s", model.name)


class NautobotScheduleEntry(ModelEntry):
    """
    Nautobot variant of the django-celery-beat ModelEntry which uses the
    nautobot.extras.models.ScheduledJob model
    """

    def _disable(self, model):
        """
        Override of the parent ModelEntry._disable() method.

        In addition to disabling the scheduled job (via the parent implementation),
        sets the job's state to ERRORED to reflect that the schedule was disabled
        due to an error condition.
        """
        super()._disable(model)
        model.state = ScheduledJobStateChoices.ERRORED
        model.save(update_fields=["state"])

    def __init__(self, model, app=None):  # pylint:disable=super-init-not-called  # we must copy-and-paste from super
        """Initialize the model entry."""
        # copy-paste from django_celery_beat.schedulers
        self.app = app or current_app._get_current_object()

        # Nautobot-specific logic
        self.name = f"{model.name}_{model.pk}"
        if model.celery_kwargs.get("nautobot_job_console_log", False):
            self.task = "nautobot.extras.jobs.run_console_log_job_and_return_job_result"
        else:
            self.task = "nautobot.extras.jobs.run_job"
        try:
            # Nautobot scheduled jobs pass args/kwargs as constructed objects,
            # but Celery built-in jobs such as celery.backend_cleanup pass them as JSON to be parsed
            self.args = [model.task] + (
                model.args if isinstance(model.args, (tuple, list)) else loads(model.args or "[]")
            )
            self.kwargs = model.kwargs if isinstance(model.kwargs, dict) else loads(model.kwargs or "{}")
        except (TypeError, ValueError) as exc:
            logger.exception("Removing schedule %s for argument deserialization error: %s", self.name, exc)
            self._disable(model)

        # copy-paste from django_celery_beat.schedulers
        try:
            self.schedule = model.schedule
        except model.DoesNotExist:
            logger.error(
                "Disabling schedule %s that was removed from database",
                self.name,
            )
            self._disable(model)

        # Nautobot-specific logic
        self.options = {"nautobot_job_scheduled_job_id": model.id, "headers": {}}

        if _user_exists(model.user_id):
            self.options["nautobot_job_user_id"] = model.user_id
        else:
            logger.error(
                "Disabling schedule %s with missing user",
                self.name,
            )
            _record_missing_user_failure(model)
            self._disable(model)

        if model.job_model:
            self.options["nautobot_job_job_model_id"] = model.job_model.id
        else:
            logger.error(
                "Disabling schedule %s with missing job model",
                self.name,
            )
            self._disable(model)

        if isinstance(model.celery_kwargs, Mapping):
            # TODO: this allows model.celery_kwargs to override keys like `nautobot_job_user_id`; is that desirable?
            self.options.update(model.celery_kwargs)

        # copy-paste from django_celery_beat.schedulers
        self.total_run_count = model.total_run_count
        self.model = model

        if not model.last_run_at:
            model.last_run_at = self._default_now()
            if model.start_time:
                # Set last_run_at to one minute before start_time so that celery's crontab
                # remaining_delta (which uses strict less-than: last_run_at.minute < max(self.minute))
                # correctly identifies the first crontab match at/after start_time as due.
                model.last_run_at = model.start_time - timedelta(minutes=1)
                # This replaces the upstream 30-year-ago hack from django-celery-beat PR #636,
                # which was intended to avoid a "heap block" issue with interval-based schedules.
                # That fix doesn't apply to Nautobot since we use DatabaseScheduler (max_interval=5s)
                # and convert all schedules to crontab (ScheduledJob.to_cron()).
                # The 30-year trick caused crontab-scheduled jobs to run once immediately (ASAP)
                # before following their crontab schedule.
                # See: https://github.com/nautobot/nautobot/issues/8316

        self.last_run_at = model.last_run_at

    def _default_now(self):
        """Instead of using self.app.timezone, use the timezone specific to this schedule entry."""
        return datetime.now(self.model.time_zone)


class NautobotDatabaseScheduler(DatabaseScheduler):
    """
    Nautobot variant of the django-celery-beat DatabaseScheduler which uses the
    nautobot.extras.models.ScheduledJob model
    """

    Entry = NautobotScheduleEntry
    Model = ScheduledJob
    Changes = ScheduledJobs

    def apply_async(self, entry, producer=None, advance=True, **kwargs):
        """Send event to the worker to start task execution.

        This is an override of the `celery.beat.Scheduler.apply_async()` method. After executing
        original `apply_async()` call, it synchronizes `total_run_count` and saves the model. This
        prevents the same task from being started again while it is still running.
        Ref: https://github.com/celery/django-celery-beat/issues/558#issuecomment-1162730008

        A PENDING JobResult is created before publishing the task to the broker, so that the
        dispatch is visible in the database even when no Celery worker is consuming the queue
        at the scheduled time. If publishing fails, the JobResult is marked as FAILURE.
        """
        resp = None
        entry = self.reserve(entry) if advance else entry
        task = self.app.tasks.get(entry.task)

        # If the entry's options lack `nautobot_job_user_id`, the originating user is
        # missing and `__init__` already recorded a failed JobResult and disabled the
        # schedule. Skip dispatch so we don't fire a doomed task into celery for this
        # tick — the next tick will not pick the entry up (enabled=False).
        if isinstance(entry, NautobotScheduleEntry) and "nautobot_job_user_id" not in entry.options:
            return None

        job_result = None
        try:
            if entry.kwargs is None:
                raise ValueError("Job `kwargs` has to be defined. Now is set to `None`.")

            entry_args = _evaluate_entry_args(entry.args)
            entry_kwargs = _evaluate_entry_kwargs(entry.kwargs)

            scheduled_job = entry.model
            job_model = scheduled_job.job_model
            celery_kwargs = dict(entry.options)
            job_queue = scheduled_job.job_queue

            if job_queue is not None:
                celery_kwargs.setdefault("queue", job_queue.name)

            job_result = JobResult.objects.create(
                name=job_model.name,
                job_model=job_model,
                scheduled_job=scheduled_job,
                user=scheduled_job.user,
                task_name=job_model.class_path,
                celery_kwargs=celery_kwargs,
            )

            # Distinguish between Celery and Kubernetes job queues
            if task and job_queue is not None and job_queue.queue_type == JobQueueTypeChoices.TYPE_KUBERNETES:
                job_result = run_kubernetes_job_and_return_job_result(job_result, entry_kwargs)
                # Return an AsyncResult object to mimic the behavior of Celery tasks
                # after the job is finished by the Kubernetes Job Pod.
                resp = AsyncResult(job_result.id)
            else:
                dispatch_kwargs = dict(entry.options)
                dispatch_kwargs["task_id"] = str(job_result.id)
                if task:
                    resp = task.apply_async(entry_args, entry_kwargs, producer=producer, **dispatch_kwargs)
                else:
                    resp = self.send_task(entry.task, entry_args, entry_kwargs, producer=producer, **dispatch_kwargs)
        except Exception as exc:  # pylint: disable=broad-except
            if job_result is not None and job_result.status == JobResultStatusChoices.STATUS_PENDING:
                job_result.status = JobResultStatusChoices.STATUS_FAILURE
                job_result.save()
            reraise(
                SchedulingError,
                SchedulingError(f"Couldn't apply scheduled task {entry.name}: {exc}"),
                sys.exc_info()[2],
            )
        finally:
            self._tasks_since_sync += 1
            if self.should_sync():
                self._do_sync()

        if entry.total_run_count != entry.model.total_run_count:
            entry.total_run_count = entry.model.total_run_count
            entry.model.save()
        return resp

    def enabled_models_qs(self):
        """
        Replace the django-celery-beat 2.8.x implementation with a simpler (less optimal) one for now.

        This should hopefully avoid issues like:

        - https://github.com/celery/django-celery-beat/issues/894
        - https://github.com/celery/django-celery-beat/issues/922
        - https://github.com/celery/django-celery-beat/issues/927
        - https://github.com/celery/django-celery-beat/issues/956
        """
        return self.Model.objects.enabled()

    def tick(self, *args, **kwargs):
        """
        Run a tick - one iteration of the scheduler.

        This is an extension of `celery.beat.Scheduler.tick()` to touch the `CELERY_BEAT_HEARTBEAT_FILE`
        file and to guard against a single stale schedule entry crashing the whole beat process.
        """
        try:
            interval = super().tick(*args, **kwargs)
        except IntegrityError:
            # A ScheduledJob entry in beat's memory can go stale when a related record (Job,
            # user) is deleted concurrently: upstream ModelEntry.is_due() full-saves the stale
            # instance, which raises IntegrityError outside of any of our apply_async() error
            # handling. Don't let one stale entry kill the whole process — force a schedule
            # reload instead; rebuilding the entries from fresh database state lets
            # NautobotScheduleEntry.__init__() disable the orphaned schedule.
            # TODO: This works around https://github.com/celery/django-celery-beat/issues/1069
            #       (fix proposed in https://github.com/celery/django-celery-beat/pull/1070),
            #       which limits the is_due() one-off save to update_fields). Once that fix is
            #       released and Nautobot's minimum supported django-celery-beat version
            #       includes it, this except block can be removed.
            logger.warning("Database integrity error during scheduler tick; forcing a schedule reload.")
            self._initial_read = True  # DatabaseScheduler.schedule: force a full re-read from the database
            self._heap = None  # celery.beat.Scheduler.tick: force heap rebuild from the fresh schedule
            interval = self.max_interval
        if settings.CELERY_BEAT_HEARTBEAT_FILE:
            Path(settings.CELERY_BEAT_HEARTBEAT_FILE).touch(exist_ok=True)
        return interval
