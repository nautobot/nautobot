from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, get_task_logger
from nautobot.extras.models import Status


logger = get_task_logger(__name__)


class TestModifyDB(Job):
    """
    Job that modifies the database.
    """

    def run(self):
        """
        Job function.
        """
        obj = Status(
            name="Test Status",
        )
        obj.save()
        logger.info("Status created successfully.", extra={"object": obj})


register_jobs(TestModifyDB)
