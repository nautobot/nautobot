from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


class TestSoftTimeLimitGreaterThanHardTimeLimit(Job):
    class Meta:
        name = "Soft Time Limit Greater Than Hard Time Limit"
        soft_time_limit = 10
        time_limit = 5

    def run(self):  # pylint: disable=arguments-differ
        pass


register_jobs(TestSoftTimeLimitGreaterThanHardTimeLimit)
