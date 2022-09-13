from nautobot.extras.jobs import Job


class TestWorkerQueues(Job):
    """
    Job with custom worker queues.
    """

    description = "Custom worker queues"

    class Meta:
        has_sensitive_variables = False
        worker_queues = [
            "",  # defaults to the default celery queue
            "nonexistent",  # This queue doesn't exist and should have zero workers
        ]

    def run(self, data, commit):
        pass
