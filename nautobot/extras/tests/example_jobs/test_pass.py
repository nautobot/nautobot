from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


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
        self.log_success(obj=None)
        self.status = "complete"


register_jobs(TestPass)
