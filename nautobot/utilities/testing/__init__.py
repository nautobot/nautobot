import time
import uuid
from contextlib import contextmanager

from celery.contrib.testing.worker import start_worker
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import tag, TransactionTestCase as _TransactionTestCase

from nautobot.core.celery import app
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.jobs import run_job
from nautobot.extras.management import populate_status_choices
from nautobot.extras.models import JobResult
from nautobot.extras.utils import get_job_content_type

from .api import APITestCase, APIViewTestCases
from .utils import (
    post_data,
    create_test_user,
    extract_form_failures,
    extract_page_body,
    disable_warnings,
)
from .views import (
    TestCase,
    ModelTestCase,
    ModelViewTestCase,
    ViewTestCases,
)

__all__ = (
    "APITestCase",
    "APIViewTestCases",
    "post_data",
    "create_test_user",
    "extract_form_failures",
    "extract_page_body",
    "disable_warnings",
    "TestCase",
    "ModelTestCase",
    "ModelViewTestCase",
    "ViewTestCases",
    "run_job_for_testing",
)


def run_job_for_testing(job, data=None, commit=True, username="test-user", request=None):
    """Provide a common interface to run Nautobot jobs as part of unit tests.

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

    # If the request has a user, ignore the username argument and use that user.
    if request and request.user:
        user_instance = request.user
    else:
        User = get_user_model()
        user_instance, _ = User.objects.get_or_create(
            username=username, defaults={"is_superuser": True, "password": "password"}
        )
    job_result = JobResult.objects.create(
        name=job.class_path,
        obj_type=get_job_content_type(),
        user=user_instance,
        job_model=job,
        job_id=uuid.uuid4(),
    )

    @contextmanager
    def _web_request_context(user):
        if request:
            yield request
        else:
            yield web_request_context(user=user)

    with _web_request_context(user=user_instance) as request:
        run_job(data=data, request=request, commit=commit, job_result_pk=job_result.pk)
    return job_result


@tag("unit")
class TransactionTestCase(_TransactionTestCase):
    """
    Base test case class using the TransactionTestCase for unit testing
    """

    def setUp(self):
        """Provide a clean, post-migration state before each test case.

        django.test.TransactionTestCase truncates the database after each test runs. We need at least the default
        statuses present in the database in order to run tests."""
        super().setUp()

        # Re-populate status choices after database truncation by TransactionTestCase
        populate_status_choices(apps, None)


class CeleryTestCase(TransactionTestCase):
    """
    Test class that provides a running Celery worker for the duration of the test case
    """

    @classmethod
    def setUpClass(cls):
        """Start a celery worker"""
        super().setUpClass()
        # Special namespace loading of methods needed by start_worker, per the celery docs
        app.loader.import_module("celery.contrib.testing.tasks")
        cls.clear_worker()
        cls.celery_worker = start_worker(app, concurrency=1)
        cls.celery_worker.__enter__()

    @classmethod
    def tearDownClass(cls):
        """Stop the celery worker"""
        super().tearDownClass()
        cls.celery_worker.__exit__(None, None, None)

    @staticmethod
    def clear_worker():
        """Purge any running or queued tasks"""
        app.control.purge()

    @classmethod
    def wait_on_active_tasks(cls):
        """Wait on all active tasks to finish before returning"""
        # TODO(john): admittedly, this is not great, but it seems the standard
        # celery APIs for inspecting the worker, looping through all active tasks,
        # and calling `.get()` on them is not working when the worker is in solo mode.
        # Needs more investigation and until then, these tasks run very quickly, so
        # simply delaying the test execution provides enough time for them to complete.
        time.sleep(1)
