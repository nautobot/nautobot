from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, StringVar


class TestRequired(Job):
    var = StringVar(required=True)


register_jobs(TestRequired)
