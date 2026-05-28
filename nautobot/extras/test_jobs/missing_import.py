from no_such_module import no_such_attribute  # noqa: F401  # pylint: disable=import-error

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


class MyJob(Job):
    pass


register_jobs(MyJob)
