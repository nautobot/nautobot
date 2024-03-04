from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import get_task_logger, Job, RunJobTaskFailed

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


class TestFailWithSanitization(Job):
    """
    Job with fail result that should be sanitized.

    This raises an exception that appears to have a password in it.
    """

    description = "Validate job failure sanitization"

    def run(self):
        logger.info("I'm a test job that fails and sanitizes the exception!")
        exc = RunJobTaskFailed(
            "fatal: could not read Password for 'https://abc123@github.com': terminal prompts disabled"
        )
        exc.args = (
            [
                "git",
                "clone",
                "-v",
                "--",
                "https://*****@github.com/jathanism/nautobot-git-example",
                "/Users/jathan/.nautobot/git/git_test",
            ],
            128,
            b"Cloning into '/Users/jathan/.nautobot/git/git_test'...\nfatal: could not read Password for https://abc123@github.com': terminal prompts disabled\n",
        )
        raise exc


register_jobs(TestFail, TestFailWithSanitization)
