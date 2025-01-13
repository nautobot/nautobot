from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


class TestWorkerQueues(Job):
    """
    Job with custom task queues.
    """

    class Meta:
        description = "Custom task queues"
        has_sensitive_variables = False
        task_queues = [
            "celery",
            "nonexistent",  # This queue doesn't exist and should have zero workers
        ]

    def run(self):  # pylint: disable=arguments-differ
        pass


register_jobs(TestWorkerQueues)
