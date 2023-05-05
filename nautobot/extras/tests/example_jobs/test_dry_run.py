from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import DryRunVar, Job
from nautobot.extras.models import Status


class TestDryRun(Job):
    """
    Job that modifies the database and supports dryrun
    """

    dryrun = DryRunVar()

    def run(self, dryrun):
        """
        Job function.
        """
        obj = Status(
            name="Test Status",
            slug="test-status",
        )
        if not dryrun:
            obj.save()
        self.log_success(obj=obj, message="Status created successfully.")


register_jobs(TestDryRun)
