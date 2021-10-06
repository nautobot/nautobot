import logging

from celery import current_app
from django_celery_beat.schedulers import ModelEntry, DatabaseScheduler

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
        self.args = model.args
        self.kwargs = model.kwargs
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
