import logging

from celery import current_app
from django_celery_beat.schedulers import ModelEntry, DatabaseScheduler
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
        self.app = app or current_app._get_current_object()
        self.name = "{}_{}".format(model.name, model.pk)
        self.task = model.task
        try:
            # Nautobot scheduled jobs pass args/kwargs as constructed objects,
            # but Celery built-in jobs such as celery.backend_cleanup pass them as JSON to be parsed
            self.args = model.args if isinstance(model.args, (tuple, list)) else loads(model.args or "[]")
            self.kwargs = model.kwargs if isinstance(model.kwargs, dict) else loads(model.kwargs or "{}")
        except (TypeError, ValueError) as exc:
            logger.exception("Removing schedule %s for argument deserialization error: %s", self.name, exc)
            self._disable(model)
        try:
            self.schedule = model.schedule
        except model.DoesNotExist:
            logger.error(
                "Disabling schedule %s that was removed from database",
                self.name,
            )
            self._disable(model)

        self.options = {}
        if model.queue:
            self.options["queue"] = model.queue

        self.options["headers"] = {}
        self.total_run_count = model.total_run_count
        self.model = model

        if not model.last_run_at:
            model.last_run_at = self._default_now()

        self.last_run_at = model.last_run_at


class NautobotDatabaseScheduler(DatabaseScheduler):
    """
    Nautobot variant of the django-celery-beat DatabaseScheduler which uses the
    nautobot.extras.models.ScheduledJob model
    """

    Entry = NautobotScheduleEntry
    Model = ScheduledJob
    Changes = ScheduledJobs
