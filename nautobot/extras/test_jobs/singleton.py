import time

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


class TestSingletonJob(Job):
    class Meta:
        name = "Example job, only one can run at any given time."
        is_singleton = True

    def run(self):
        time.sleep(60)


register_jobs(TestSingletonJob)
