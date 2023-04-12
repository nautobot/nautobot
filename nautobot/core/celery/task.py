from celery.utils.log import get_task_logger
from celery import Task


logger = get_task_logger(__name__)


class NautobotTask(Task):
    """Nautobot extensions to tasks for integrating with Job machinery."""


Task = NautobotTask  # noqa: So that the class path resolves.
