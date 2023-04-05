from django.contrib.auth import get_user_model
from django.test import TransactionTestCase as _TransactionTestCase
from django.test import tag

from nautobot.core.testing.api import APITestCase, APIViewTestCases
from nautobot.core.testing.filters import FilterTestCases
from nautobot.core.testing.mixins import NautobotTestCaseMixin, NautobotTestClient
from nautobot.core.testing.utils import (
    create_test_user,
    disable_warnings,
    extract_form_failures,
    extract_page_body,
    get_deletable_objects,
    post_data,
)
from nautobot.core.testing.views import ModelTestCase, ModelViewTestCase, TestCase, ViewTestCases
from nautobot.extras.models import JobResult

__all__ = (
    "APITestCase",
    "APIViewTestCases",
    "create_test_user",
    "disable_warnings",
    "extract_form_failures",
    "extract_page_body",
    "FilterTestCases",
    "get_deletable_objects",
    "ModelTestCase",
    "ModelViewTestCase",
    "NautobotTestCaseMixin",
    "NautobotTestClient",
    "post_data",
    "run_job_for_testing",
    "TestCase",
    "ViewTestCases",
)

# Use the proper swappable User model
User = get_user_model()


def run_job_for_testing(job, username="test-user", **kwargs):
    """
    Provide a common interface to run Nautobot jobs as part of unit tests.

    Args:
      job (Job): Job model instance (not Job class) to run
      username (str): Username of existing or to-be-created User account to own the JobResult. Ignored if `request.user`
        exists.
      **kwargs: Input keyword arguments for Job run method.

    Returns:
      JobResult: representing the executed job
    """
    # Enable the job if it wasn't enabled before
    if not job.enabled:
        job.enabled = True
        job.validated_save()

    user_instance, _ = User.objects.get_or_create(
        username=username, defaults={"is_superuser": True, "password": "password"}
    )
    # Run the job synchronously in the current thread as if it were being executed by a worker
    job_result = JobResult.apply_job(
        job_model=job,
        user=user_instance,
        **kwargs,
    )
    return job_result


@tag("unit")
class TransactionTestCase(_TransactionTestCase, NautobotTestCaseMixin):
    """
    Base test case class using the TransactionTestCase for unit testing
    """

    # 'job_logs' is a proxy connection to the same (default) database that's used exclusively for Job logging
    databases = ("default", "job_logs")

    def setUp(self):
        """Provide a clean, post-migration state before each test case.

        django.test.TransactionTestCase truncates the database after each test runs. We need at least the default
        statuses present in the database in order to run tests."""
        super().setUp()
        self.setUpNautobot(client=True, populate_status=True)
