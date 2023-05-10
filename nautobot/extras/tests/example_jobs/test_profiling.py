import pstats

from nautobot.extras.jobs import Job


class TestProfilingJob(Job):
    """
    Job to have profiling tested.
    """

    description = "Test profiling"

    def run(self, data, commit):
        """
        Job function.
        """

        self.log_success(obj=None, message="Profiling test.")

        return []

    def post_run(self):
        pstats.Stats(f"/tmp/nautobot-jobresult-{self.job_result.id}.pstats")
