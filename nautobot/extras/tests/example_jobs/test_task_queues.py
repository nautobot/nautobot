from nautobot.extras.jobs import Job


class TestWorkerQueues(Job):
    """
    Job with custom task queues.
    """

    description = "Custom task queues"

    class Meta:
        has_sensitive_variables = False
        task_queues = [
            "celery",
            "nonexistent",  # This queue doesn't exist and should have zero workers
        ]

    def run(self, data, commit):
        pass
