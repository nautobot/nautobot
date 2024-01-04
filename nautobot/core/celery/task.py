from celery import Task

from nautobot.extras.jobs import get_task_logger

logger = get_task_logger(__name__)


class NautobotTask(Task):
    """Nautobot extensions to tasks for integrating with Job machinery."""


Task = NautobotTask  # So that the class path resolves.
