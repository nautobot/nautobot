from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import get_task_logger, Job

logger = get_task_logger(__name__)


class TestLogCountsByLevel(Job):
    class Meta:
        description = "Test counts of log entries by level."

    def run(self):  # pylint: disable=arguments-differ
        # intentionally omit debug
        logger.info("This is an info log")
        logger.info("This is an info log")
        logger.warning("This is a warning log")
        logger.warning("This is a warning log")
        logger.error("This is an error log")
        logger.critical("This is a critical log")
        logger.failure("This is a failure log")
        # success log will be added by post_run


register_jobs(TestLogCountsByLevel)
