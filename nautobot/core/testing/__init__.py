import collections

from django.contrib.auth import get_user_model
from django.test import tag, TransactionTestCase as _TransactionTestCase

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
from nautobot.extras.jobs import get_job
from nautobot.extras.models import Job, JobResult

__all__ = (
    "APITestCase",
    "APIViewTestCases",
    "FilterTestCases",
    "JobClassInfo",
    "ModelTestCase",
    "ModelViewTestCase",
    "NautobotTestCaseMixin",
    "NautobotTestClient",
    "TestCase",
    "ViewTestCases",
    "create_job_result_and_run_job",
    "create_test_user",
    "disable_warnings",
    "extract_form_failures",
    "extract_page_body",
    "get_deletable_objects",
    "get_job_class_and_model",
    "post_data",
    "run_job_for_testing",
)

# Use the proper swappable User model
User = get_user_model()


def run_job_for_testing(job, username="test-user", profile=False, **kwargs):
    """
    Provide a common interface to run Nautobot jobs as part of unit tests.

    Args:
        job (Job): Job model instance (not Job class) to run
        username (str): Username of existing or to-be-created User account to own the JobResult.
        profile (bool): Whether to profile the job execution.

    Keyword Args:
        **kwargs (any): Input keyword arguments for Job run method.

    Returns:
        (JobResult): representing the executed job
    """
    # Enable the job if it wasn't enabled before
    if not job.enabled:
        job.enabled = True
        job.validated_save()

    user_instance, _ = User.objects.get_or_create(
        username=username, defaults={"is_superuser": True, "password": "password"}
    )
    # Run the job synchronously in the current thread as if it were being executed by a worker
    # TODO: in Nautobot core testing, we set `CELERY_TASK_ALWAYS_EAGER = True`, so we *could* use enqueue_job() instead,
    #       but switching now would be a potentially breaking change for apps...
    job_result = JobResult.execute_job(
        job_model=job,
        user=user_instance,
        profile=profile,
        **kwargs,
    )
    return job_result


def create_job_result_and_run_job(module, name, source="local", *args, **kwargs):
    """Test helper function to call get_job_class_and_model() then call run_job_for_testing()."""
    _job_class, job_model = get_job_class_and_model(module, name, source)
    job_result = run_job_for_testing(job=job_model, **kwargs)
    job_result.refresh_from_db()
    return job_result


#: Return value of `get_job_class_and_model()`.
JobClassInfo = collections.namedtuple("JobClassInfo", "job_class job_model")


def get_job_class_and_model(module, name, source="local"):
    """
    Test helper function to look up a job class and job model and ensure the latter is enabled.

    Args:
        module (str): Job module name
        name (str): Job class name
        source (str): Job grouping (default: "local")

    Returns:
        (JobClassInfo): Named 2-tuple of (job_class, job_model)
    """
    job_class = get_job(f"{module}.{name}")
    try:
        job_model = Job.objects.get(module_name=module, job_class_name=name)
    except Job.DoesNotExist:
        raise RuntimeError(
            f"Job database record for {module}.{name} not found. Known jobs are: {list(Job.objects.all())}"
        )
    job_model.enabled = True
    job_model.validated_save()
    return JobClassInfo(job_class, job_model)


@tag("unit")
class TransactionTestCase(NautobotTestCaseMixin, _TransactionTestCase):
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
