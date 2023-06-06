from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, get_task_logger


logger = get_task_logger(__name__)


class TestLogSkipDBLogging(Job):
    class Meta:
        description = "Test logs not being saved to the database"

    def run(self):
        logger.debug("I should NOT be logged to the database", extra={"skip_db_logging": True})
        logger.info("I should be logged to the database")


register_jobs(TestLogSkipDBLogging)
