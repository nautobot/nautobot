import uuid

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TransactionTestCase as _TransactionTestCase
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
from nautobot.core.utils.requests import copy_safe_request
from nautobot.extras.jobs import run_job
from nautobot.extras.models import JobResult
from nautobot.extras.utils import get_job_content_type

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


def run_job_for_testing(job, data=None, commit=True, username="test-user", request=None):
    """
    Provide a common interface to run Nautobot jobs as part of unit tests.

    The Celery task result will be stored at the `JobResult.celery_result` attribute.

    Args:
      job (Job): Job model instance (not Job class) to run
      data (dict): Input data values for any Job variables.
      commit (bool): Whether to commit changes to the database or rollback when done.
      username (str): Username of existing or to-be-created User account to own the JobResult. Ignored if `request.user`
        exists.
      request (HttpRequest): Existing request (if any) to own the JobResult.

    Returns:
      JobResult: representing the executed job
    """
    if data is None:
        data = {}

    # Enable the job if it wasn't enabled before
    if not job.enabled:
        job.enabled = True
        job.validated_save()

    # If the request has a user, ignore the username argument and use that user.
    if request and request.user:
        user_instance = request.user
    else:
        user_instance, _ = User.objects.get_or_create(
            username=username, defaults={"is_superuser": True, "password": "password"}
        )
    job_result = JobResult.objects.create(
        name=job.class_path,
        task_kwargs={"data": data, "commit": commit},
        obj_type=get_job_content_type(),
        user=user_instance,
        job_model=job,
        task_id=uuid.uuid4(),
    )

    if request is None:
        factory = RequestFactory()
        request = factory.request()
        request.user = user_instance

    # Instead of a context manager, we're just explicitly creating a `NautobotFakeRequest`.
    wrapped_request = copy_safe_request(request)

    # This runs the job synchronously in the current thread as if it were being executed by a
    # worker, therefore resulting in updating the `JobResult` as expected.
    celery_result = run_job.apply(
        kwargs=dict(data=data, request=wrapped_request, commit=commit, job_result_pk=job_result.pk),
        task_id=job_result.task_id,
    )
    job_result.celery_result = celery_result
    job_result.refresh_from_db()
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
