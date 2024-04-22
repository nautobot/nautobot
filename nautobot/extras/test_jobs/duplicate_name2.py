from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


class TestDuplicateNameNoMeta(Job):
    pass


register_jobs(TestDuplicateNameNoMeta)
