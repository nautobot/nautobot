from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job
from nautobot.extras.models import Status


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
        self.log_success(obj=obj, message="Status created successfully.")


register_jobs(TestModifyDB)
