from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import get_task_logger, Job

logger = get_task_logger(__name__)


class TestProfilingJob(Job):
    """
    Job to have profiling tested.
    """

    description = "Test profiling"

    def run(self):  # pylint: disable=arguments-differ
        """
        Job function.
        """

        logger.info("Profiling test.")

        return []


register_jobs(TestProfilingJob)
