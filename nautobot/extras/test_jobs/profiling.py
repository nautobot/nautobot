import pstats
import tempfile

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

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        super().after_return(status, retval, task_id, args, kwargs, einfo=einfo)
        pstats.Stats(f"{tempfile.gettempdir()}/nautobot-jobresult-{self.job_result.id}.pstats")


register_jobs(TestProfilingJob)
