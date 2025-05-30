from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import DryRunVar, get_task_logger, IntegerVar, Job
from nautobot.extras.models import Status

logger = get_task_logger(__name__)


class TestDryRun(Job):
    """
    Job that modifies the database and supports dryrun
    """

    dryrun = DryRunVar()
    value = IntegerVar(required=False)

    def run(self, dryrun, value=None):  # pylint:disable=arguments-differ
        """
        Job function.
        """
        obj = Status(
            name="Test Status",
        )
        if not dryrun:
            obj.save()
        logger.info("Status created successfully.", extra={"object": obj})


register_jobs(TestDryRun)
