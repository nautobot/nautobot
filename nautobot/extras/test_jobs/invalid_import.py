from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, no_such_attribute  # noqa: F401  # pylint: disable=no-name-in-module


class MyJob(Job):
    pass


register_jobs(MyJob)
