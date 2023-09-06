from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import DryRunVar, Job, StringVar


class TestReadOnlyJob(Job):
    """My job demo."""

    dryrun = DryRunVar()
    var = StringVar(description="Hello")

    class Meta:
        read_only = True


register_jobs(TestReadOnlyJob)
