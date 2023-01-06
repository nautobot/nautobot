from celery.utils.log import get_task_logger
from celery import Task


logger = get_task_logger(__name__)


class NautobotTask(Task):
    """Nautobot extensions to tasks for integrating with Job machinery."""

    def before_start(self, task_id, args, kwargs):
        logger.debug(">>> TASK_ID = %s", task_id)
        logger.debug(">>>    ARGS = %s", args)
        logger.debug(">>>  KWARGS = %s", kwargs)


Task = NautobotTask  # noqa: So that the class path resolves.
