from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


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
        self.log_success(obj=None)


register_jobs(TestHasSensitiveVariables)
