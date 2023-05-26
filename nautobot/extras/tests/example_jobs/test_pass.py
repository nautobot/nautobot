from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, get_task_logger


logger = get_task_logger(__name__)


class TestPass(Job):
    """
    Job with pass result.
    """

    description = "Validate job import"

    class Meta:
        has_sensitive_variables = False

    def run(self):
        """
        Job function.
        """
        logger.info("Success")


register_jobs(TestPass)
