from billiard.einfo import ExceptionInfo

from nautobot.core.celery import register_jobs
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.jobs import get_task_logger, Job, RunJobTaskFailed

logger = get_task_logger(__name__)


class TestFailJob(Job):
    """
    Job with fail result.
    """

    description = "Validate job import"

    def before_start(self, task_id, args, kwargs):
        if task_id != self.request.id:  # pylint: disable=no-member
            raise RuntimeError(f"Expected task_id {task_id} to equal self.request.id {self.request.id}")
        if args:
            raise RuntimeError(f"Expected args to be empty, but it was {args!r}")
        if kwargs:
            raise RuntimeError(f"Expected kwargs to be empty, but it was {kwargs!r}")
        logger.info("before_start() was called as expected")

    def run(self):  # pylint:disable=arguments-differ
        """
        Job function.
        """
        logger.info("I'm a test job that fails!")
        raise RunJobTaskFailed("Test failure")

    def on_success(self, retval, task_id, args, kwargs):
        raise RuntimeError("on_success() was unexpectedly called!")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if not isinstance(exc, RunJobTaskFailed):
            raise RuntimeError(f"Expected exc to be a RunJobTaskFailed, but it was {exc!r}")
        if task_id != self.request.id:
            raise RuntimeError(f"Expected task_id {task_id} to equal self.request.id {self.request.id}")
        if args:
            raise RuntimeError(f"Expected args to be empty, but it was {args!r}")
        if kwargs:
            raise RuntimeError(f"Expected kwargs to be empty, but it was {kwargs!r}")
        if not isinstance(einfo, ExceptionInfo):
            raise RuntimeError(f"Expected einfo to be an ExceptionInfo, but it was {einfo!r}")
        logger.info("on_failure() was called as expected")

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if status is not JobResultStatusChoices.STATUS_FAILURE:
            raise RuntimeError(f"Expected status to be {JobResultStatusChoices.STATUS_FAILURE}, but it was {status!r}")
        if not isinstance(retval, RunJobTaskFailed):
            raise RuntimeError(f"Expected retval to be a RunJobTaskFailed, but it was {retval!r}")
        if task_id != self.request.id:
            raise RuntimeError(f"Expected task_id {task_id} to equal self.request.id {self.request.id}")
        if args:
            raise RuntimeError(f"Expected args to be empty, but it was {args!r}")
        if kwargs:
            raise RuntimeError(f"Expected kwargs to be empty, but it was {kwargs!r}")
        if not isinstance(einfo, ExceptionInfo):
            raise RuntimeError(f"Expected einfo to be an ExceptionInfo, but it was {einfo!r}")
        logger.info("after_return() was called as expected")


class TestFailInBeforeStart(TestFailJob):
    """
    Job that raises an exception in before_start().
    """

    def before_start(self, task_id, args, kwargs):
        super().before_start(task_id, args, kwargs)
        logger.info("I'm a test job that fails!")
        raise RunJobTaskFailed("Setup failure")

    def run(self):
        raise RuntimeError("run() was unexpectedly called after a failure in before_start()")


class TestFailWithSanitization(Job):
    """
    Job with fail result that should be sanitized.

    This raises an exception that appears to have a password in it.
    """

    description = "Validate job failure sanitization"

    def run(self):  # pylint:disable=arguments-differ
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


class TestFailCleanly(TestFailJob):
    """
    Job that fails "cleanly" through self.fail() instead of raising an exception.
    """

    def run(self):  # pylint: disable=arguments-differ
        logger.info("I'm a test job that fails!")
        self.fail("Failure")
        return "We failed"

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if exc != "We failed":
            raise RuntimeError(f"Expected exc to be the message returned from run(), but it was {exc!r}")
        if task_id != self.request.id:  # pylint: disable=no-member
            raise RuntimeError(f"Expected task_id {task_id} to equal self.request.id {self.request.id}")  # pylint: disable=no-member
        if args:
            raise RuntimeError(f"Expected args to be empty, but it was {args!r}")
        if kwargs:
            raise RuntimeError(f"Expected kwargs to be empty, but it was {kwargs!r}")
        if einfo is not None:
            raise RuntimeError(f"Expected einfo to be None, but it was {einfo!r}")
        logger.info("on_failure() was called as expected")

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if status is not JobResultStatusChoices.STATUS_FAILURE:
            raise RuntimeError(f"Expected status to be {JobResultStatusChoices.STATUS_FAILURE}, but it was {status!r}")
        if retval != "We failed":
            raise RuntimeError(f"Expected retval to be the message returned from run(), but it was {retval!r}")
        if task_id != self.request.id:  # pylint: disable=no-member
            raise RuntimeError(f"Expected task_id {task_id} to equal self.request.id {self.request.id}")  # pylint: disable=no-member
        if args:
            raise RuntimeError(f"Expected args to be empty, but it was {args!r}")
        if kwargs:
            raise RuntimeError(f"Expected kwargs to be empty, but it was {kwargs!r}")
        if einfo is not None:
            raise RuntimeError(f"Expected einfo to be None, but it was {einfo!r}")
        logger.info("after_return() was called as expected")


class TestFailCleanlyInBeforeStart(TestFailCleanly):
    """
    Job that fails "cleanly" during before_start() through self.fail() instead of raising an exception.
    """

    def before_start(self, task_id, args, kwargs):
        super().before_start(task_id, args, kwargs)
        logger.info("I'm a test job that fails!")
        self.fail("We failed")
        return "We failed"

    def run(self):
        raise RuntimeError("run() was unexpectedly called after a failure in before_start()")


register_jobs(
    TestFailJob,
    TestFailInBeforeStart,
    TestFailWithSanitization,
    TestFailCleanly,
    TestFailCleanlyInBeforeStart,
)
