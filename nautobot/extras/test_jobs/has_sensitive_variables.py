from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import get_task_logger, Job

logger = get_task_logger(__name__)


class TestHasSensitiveVariables(Job):
    """
    Job with JobResult Sensitive Variables censored.
    """

    description = "Job with has_sensitive_variables set to True"

    class Meta:
        has_sensitive_variables = True

    def run(self, *args, **kwargs):
        """
        Job function.
        """
        logger.info("Success")


register_jobs(TestHasSensitiveVariables)
