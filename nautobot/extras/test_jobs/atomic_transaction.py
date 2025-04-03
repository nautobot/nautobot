from django.db import transaction

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import BooleanVar, get_task_logger, Job
from nautobot.extras.models import Status

logger = get_task_logger(__name__)


class SimulatedError(Exception):
    """I'm just a dummy exception for the purpose of testing."""


class TestAtomicDecorator(Job):
    """
    Job that uses @transaction.atomic decorator to roll back changes.
    """

    should_fail = BooleanVar()

    @transaction.atomic
    def run(self, should_fail=False):  # pylint:disable=arguments-differ
        try:
            Status.objects.create(name="Test database atomic rollback 1")
            if should_fail:
                raise SimulatedError("simulated failure")
        except Exception:
            logger.error("Job failed, all database changes have been rolled back.")
            raise
        logger.info("Job succeeded.")


class TestAtomicContextManager(Job):
    """
    Job that uses `with transaction.atomic()` context manager to roll back changes.
    """

    should_fail = BooleanVar()

    def run(self, should_fail=False):  # pylint:disable=arguments-differ
        try:
            with transaction.atomic():
                Status.objects.create(name="Test database atomic rollback 2")
                if should_fail:
                    raise SimulatedError("simulated failure")
        except Exception as err:
            logger.error("Job failed, all database changes have been rolled back.")
            raise err
        logger.info("Job succeeded.")


register_jobs(TestAtomicContextManager, TestAtomicDecorator)
