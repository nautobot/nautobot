from celery.utils.log import get_task_logger
from celery import Task


logger = get_task_logger(__name__)


class NautobotTask(Task):
    """Nautobot extensions to tasks for integrating with Job machinery."""


Task = NautobotTask  # noqa: So that the class path resolves.


# TODO(jathan): Remove this once this body of work is done. This is just useful for debugging but it
# results int a lot of noise and slows things down.
# from celery import signals
# @signals.task_prerun.connect
def debug_task_prerun(sender, task_id, task, args, kwargs, **extra):
    logger.error(">>>    SENDER = %s", sender)
    logger.error(">>>      TASK = %s", task)
    logger.error(">>>   REQUEST = %s", task.request)
    logger.error(">>>   TASK_NAME = %s", task.request.task)
    logger.error(">>>   TASK_ID = %s", task_id)
    logger.error(">>>      ARGS = %s", args)
    logger.error(">>>    KWARGS = %s", kwargs)
    logger.error(">>>     EXTRA = %s", extra)
