from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import get_task_logger, Job
from nautobot.extras.models import Status

logger = get_task_logger(__name__)


class TestModifyDB(Job):
    """
    Job that modifies the database.
    """

    def run(self):  # pylint: disable=arguments-differ
        """
        Job function.
        """
        obj = Status(
            name="Test Status",
        )
        obj.save()
        logger.info("Status created successfully.", extra={"object": obj})


register_jobs(TestModifyDB)
