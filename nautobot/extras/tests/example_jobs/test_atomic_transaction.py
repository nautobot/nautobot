from django.db import transaction

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, BooleanVar
from nautobot.extras.models import Status


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
                raise Exception("simulated failure")
        except Exception:
            self.log_failure("Job failed, all database changes have been rolled back.")
        self.log_success("Job succeeded.")


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
                    raise Exception("simulated failure")
        except Exception:
            self.log_failure("Job failed, all database changes have been rolled back.")
        self.log_success("Job succeeded.")


register_jobs(TestAtomicContextManager, TestAtomicDecorator)
