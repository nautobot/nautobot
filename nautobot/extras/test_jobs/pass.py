from nautobot.core.celery import register_jobs
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.jobs import get_task_logger, Job

logger = get_task_logger(__name__)


class TestPassJob(Job):
    """
    Job with pass result.
    """

    description = "Validate job import"

    class Meta:
        has_sensitive_variables = False

    def before_start(self, task_id, args, kwargs):
        if task_id != self.request.id:
            raise RuntimeError(f"Expected task_id {task_id} to equal self.request.id {self.request.id}")
        if args:
            raise RuntimeError(f"Expected args to be empty, but it was {args!r}")
        if kwargs:
            raise RuntimeError(f"Expected kwargs to be empty, but it was {kwargs!r}")
        logger.info("before_start() was called as expected")

    def run(self):  # pylint: disable=arguments-differ
        """
        Job function.
        """
        logger.info("Success")
        return True

    def on_success(self, retval, task_id, args, kwargs):
        if retval is not True:
            raise RuntimeError(f"Expected retval to be True, but it was {retval!r}")
        if task_id != self.request.id:
            raise RuntimeError(f"Expected task_id {task_id} to equal self.request.id {self.request.id}")
        if args:
            raise RuntimeError(f"Expected args to be empty, but it was {args!r}")
        if kwargs:
            raise RuntimeError(f"Expected kwargs to be empty, but it was {kwargs!r}")
        logger.info("on_success() was called as expected")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        raise RuntimeError("on_failure() was unexpectedly called!")

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if status is not JobResultStatusChoices.STATUS_SUCCESS:
            raise RuntimeError(f"Expected status to be {JobResultStatusChoices.STATUS_SUCCESS}, but it was {status!r}")
        if retval is not True:
            raise RuntimeError(f"Expected retval to be True, but it was {retval!r}")
        if task_id != self.request.id:
            raise RuntimeError(f"Expected task_id {task_id} to equal self.request.id {self.request.id}")
        if args:
            raise RuntimeError(f"Expected args to be empty, but it was {args!r}")
        if kwargs:
            raise RuntimeError(f"Expected kwargs to be empty, but it was {kwargs!r}")
        if einfo is not None:
            raise RuntimeError(f"Expected einfo to be None, but it was {einfo!r}")
        logger.info("after_return() was called as expected")


register_jobs(TestPassJob)
