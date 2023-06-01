from django.db import transaction

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, BooleanVar, get_task_logger
from nautobot.extras.models import Status


logger = get_task_logger(__name__)


class SimulatedError(Exception):
    """I'm just a dummy exception for the purpose of testing."""


class TestAtomicDecorator(Job):
    """
    Job that uses @transaction.atomic decorator to roll back changes.
    """

    fail = BooleanVar()

    @transaction.atomic
    def run(self, fail=False):
        try:
            Status.objects.create(name="Test database atomic rollback 1")
            if fail:
                raise SimulatedError("simulated failure")
        except Exception:
            logger.error("Job failed, all database changes have been rolled back.")
            raise
        logger.info("Job succeeded.")


class TestAtomicContextManager(Job):
    """
    Job that uses `with transaction.atomic()` context manager to roll back changes.
    """

    fail = BooleanVar()

    def run(self, fail=False):
        try:
            with transaction.atomic():
                Status.objects.create(name="Test database atomic rollback 2")
                if fail:
                    raise SimulatedError("simulated failure")
        except Exception as err:
            logger.error("Job failed, all database changes have been rolled back.")
            raise err
        logger.info("Job succeeded.")


register_jobs(TestAtomicContextManager, TestAtomicDecorator)
