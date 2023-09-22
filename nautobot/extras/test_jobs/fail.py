from nautobot.extras.jobs import Job, RunJobTaskFailed, get_task_logger


logger = get_task_logger(__name__)


class TestFail(Job):
    """
    Job with fail result.
    """

    description = "Validate job import"

    def run(self):
        """
        Job function.
        """
        logger.info("I'm a test job that fails!")
        raise RunJobTaskFailed("Test failure")
