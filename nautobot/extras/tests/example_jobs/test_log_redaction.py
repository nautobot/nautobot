from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, get_task_logger


logger = get_task_logger(__name__)


class TestLogRedaction(Job):
    class Meta:
        description = "Test redaction of logs"

    def run(self):
        logger.debug("The secret is supersecret123")
        logger.info("The secret is supersecret123")
        logger.warning("The secret is supersecret123")
        logger.error("The secret is supersecret123")
        logger.critical("The secret is supersecret123")


register_jobs(TestLogRedaction)
