import time

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


class TestSingletonJob(Job):
    class Meta:
        name = "Example Singleton Job"
        is_singleton = True

    def run(self, *args, **kwargs):
        time.sleep(1)


register_jobs(TestSingletonJob)
