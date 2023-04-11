from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


class TestFail(Job):
    """
    Job with fail result.
    """

    description = "Validate job import"

    def run(self):
        """
        Job function.
        """
        self.log_success(obj=None)
        raise Exception("Test failure")  # pylint: disable=broad-exception-raised


register_jobs(TestFail)
