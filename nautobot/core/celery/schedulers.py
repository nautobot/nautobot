from collections.abc import Mapping
from datetime import datetime, timedelta
import logging
from pathlib import Path

from celery import current_app
from django.conf import settings
from django_celery_beat.schedulers import DatabaseScheduler, ModelEntry
from kombu.utils.json import loads

from nautobot.extras.models import ScheduledJob, ScheduledJobs

logger = logging.getLogger(__name__)


class NautobotScheduleEntry(ModelEntry):
    """
    Nautobot variant of the django-celery-beat ModelEntry which uses the
    nautobot.extras.models.ScheduledJob model
    """

    def __init__(self, model, app=None):
        """Initialize the model entry."""
        # copy-paste from django_celery_beat.schedulers
        self.app = app or current_app._get_current_object()

        # Nautobot-specific logic
        self.name = f"{model.name}_{model.pk}"
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

        if model.user:
            self.options["nautobot_job_user_id"] = model.user.id
        else:
            logger.error(
                "Disabling schedule %s with missing user",
                self.name,
            )
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
            self.options.update(model.celery_kwargs)

        # copy-paste from django_celery_beat.schedulers
        self.total_run_count = model.total_run_count
        self.model = model

        if not model.last_run_at:
            model.last_run_at = self._default_now()
            # if last_run_at is not set and
            # model.start_time last_run_at should be in way past.
            # This will trigger the job to run at start_time
            # and avoid the heap block.
            if model.start_time:
                model.last_run_at = model.last_run_at - timedelta(days=365 * 30)

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
        """
        resp = super().apply_async(entry, producer=producer, advance=advance, **kwargs)
        if entry.total_run_count != entry.model.total_run_count:
            entry.total_run_count = entry.model.total_run_count
            entry.model.save()
        return resp

    def tick(self, *args, **kwargs):
        """
        Run a tick - one iteration of the scheduler.

        This is an extension of `celery.beat.Scheduler.tick()` to touch the `CELERY_BEAT_HEARTBEAT_FILE` file.
        """
        interval = super().tick(*args, **kwargs)
        if settings.CELERY_BEAT_HEARTBEAT_FILE:
            Path(settings.CELERY_BEAT_HEARTBEAT_FILE).touch(exist_ok=True)
        return interval
