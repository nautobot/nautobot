import datetime
from io import StringIO
import json
import os
from pathlib import Path
import re
import tempfile
from unittest import mock
import uuid

from constance.test import override_config
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.test.client import RequestFactory
from django.utils import timezone

from nautobot.core.testing import (
    create_job_result_and_run_job,
    get_job_class_and_model,
    TestCase,
    TransactionTestCase,
)
from nautobot.core.utils.lookup import get_changes_for_model
from nautobot.dcim.models import Device, Location, LocationType
from nautobot.extras import models
from nautobot.extras.choices import (
    JobExecutionType,
    JobQueueTypeChoices,
    JobResultStatusChoices,
    LogLevelChoices,
    ObjectChangeEventContextChoices,
)
from nautobot.extras.context_managers import change_logging, JobHookChangeContext, web_request_context
from nautobot.extras.jobs import BaseJob, get_job, get_jobs
from nautobot.extras.models import Job, JobQueue
from nautobot.extras.models.jobs import JobLogEntry


class JobTest(TestCase):
    """
    Test job features that don't require a transaction test case.
    """

    def test_as_form_no_job_model(self):
        """Job.as_form() test with no corresponding job_model (https://github.com/nautobot/nautobot/issues/6773)."""
        form = BaseJob.as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["_job_queue", "_profile"])

    def test_field_default(self):
        """
        Job test with field that is a default value that is falsey.
        https://github.com/nautobot/nautobot/issues/2039
        """
        module = "field_default"
        name = "TestFieldDefault"
        job_class = get_job(f"{module}.{name}")
        form = job_class.as_form()

        self.assertInHTML(
            """<tr><th><label for="id_var_int">Var int:</label></th><td>
<input class="form-control" id="id_var_int" max="3600" name="var_int" placeholder="None" required type="number" value="0">
<br><span class="helptext">Test default of 0 Falsey</span></td></tr>
<tr><th><label for="id_var_int_no_default">Var int no default:</label></th><td>
<input class="form-control" id="id_var_int_no_default" max="3600" name="var_int_no_default" placeholder="None" type="number">
<br><span class="helptext">Test default without default</span></td></tr>""",
            form.as_table(),
        )

    def test_field_order(self):
        """
        Job test with field order.
        """
        module = "field_order"
        name = "TestFieldOrder"
        job_class = get_job(f"{module}.{name}")
        form = job_class.as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["var1", "var2", "var23", "_job_queue", "_profile"])

    def test_no_field_order(self):
        """
        Job test without field_order.
        """
        module = "no_field_order"
        name = "TestNoFieldOrder"
        job_class = get_job(f"{module}.{name}")
        form = job_class.as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["var23", "var2", "_job_queue", "_profile"])

    def test_no_field_order_inherited_variable(self):
        """
        Job test without field_order with a variable inherited from the base class
        """
        module = "no_field_order"
        name = "TestDefaultFieldOrderWithInheritance"
        job_class = get_job(f"{module}.{name}")
        form = job_class.as_form()
        self.assertSequenceEqual(
            list(form.fields.keys()),
            ["testvar1", "b_testvar2", "a_testvar3", "_job_queue", "_profile"],
        )

    def test_dryrun_default(self):
        """Test that dryrun_default is reflected in job form."""
        module = "dry_run"
        name = "TestDryRun"
        job_class, job_model = get_job_class_and_model(module, name)

        # not overridden on job model, initial form field value should match job class
        job_model.dryrun_default_override = False
        job_model.save()
        form = job_class.as_form()
        self.assertEqual(form.fields["dryrun"].initial, job_class.dryrun_default)

        # overridden on job model, initial form field value should match job model
        job_model.dryrun_default_override = True
        job_model.dryrun_default = not job_class.dryrun_default
        job_model.save()
        form = job_class.as_form()
        self.assertEqual(form.fields["dryrun"].initial, job_model.dryrun_default)

    def test_job_task_queues_setter(self):
        """Test the task_queues property setter on Job."""
        module = "dry_run"
        name = "TestDryRun"
        _, job_model = get_job_class_and_model(module, name)

        invalid_queue = "Invalid job Queue"
        with self.assertRaises(ValidationError) as cm:
            job_model.task_queues = [invalid_queue]
            job_model.validated_save()
        self.assertIn(f"Job Queue {invalid_queue} does not exist in the database.", str(cm.exception))

    def test_job_class_job_queues(self):
        """
        Test job form with custom task queues defined on the job class
        """
        module = "task_queues"
        name = "TestWorkerQueues"
        job_class, job_model = get_job_class_and_model(module, name)
        jq_1, _ = models.JobQueue.objects.get_or_create(
            name="celery", defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY}
        )
        jq_2, _ = models.JobQueue.objects.get_or_create(
            name="irrelevant", defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY}
        )
        job_model.job_queues.set([jq_1, jq_2])
        form = job_class.as_form()
        self.assertQuerySetEqual(
            form.fields["_job_queue"].queryset,
            models.JobQueue.objects.filter(jobs=job_model),
        )

    def test_supports_dryrun(self):
        """
        Test job class supports_dryrun field and job model supports_dryrun field
        """

        module = "dry_run"
        name = "TestDryRun"
        job_class, job_model = get_job_class_and_model(module, name)
        self.assertTrue(job_class.supports_dryrun)
        self.assertTrue(job_model.supports_dryrun)

        module = "pass_job"
        name = "TestPassJob"
        job_class, job_model = get_job_class_and_model(module, name)
        self.assertFalse(job_class.supports_dryrun)
        self.assertFalse(job_model.supports_dryrun)

    def test_submodule_in_jobs_root(self):
        """
        Test that a subdirectory/submodule in JOBS_ROOT can contain Jobs.
        """
        job_class, job_model = get_job_class_and_model("jobs_module.jobs_submodule.jobs", "ChildJob")
        self.assertIsNotNone(job_class)
        self.assertIsNotNone(job_model)

    def test_relative_import_among_files_in_jobs_root(self):
        """
        Test that a module in JOBS_ROOT can import from other modules in JOBS_ROOT.
        """
        job_class, job_model = get_job_class_and_model("relative_import", "TestReallyPass")
        self.assertIsNotNone(job_class)
        self.assertIsNotNone(job_model)

    def test_get_jobs_from_jobs_root(self):
        """
        Test that get_jobs() correctly loads jobs from JOBS_ROOT as its contents change.
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with override_settings(JOBS_ROOT=temp_dir):
                    # Create a new Job and make sure it's discovered correctly
                    with open(os.path.join(temp_dir, "my_jobs.py"), "w") as fd:
                        fd.write(
                            """\
from nautobot.apps.jobs import Job, register_jobs
class MyJob(Job):
    def run(self):
        pass
register_jobs(MyJob)
"""
                        )
                    jobs_data = get_jobs(reload=True)
                    self.assertIn("my_jobs.MyJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("my_jobs.MyJob"))
                    # Also make sure some representative previous JOBS_ROOT jobs aren't still around:
                    self.assertNotIn("dry_run.TestDryRun", jobs_data.keys())
                    self.assertNotIn("pass_job.TestPassJob", jobs_data.keys())

                    # Create a second Job in the same module
                    with open(os.path.join(temp_dir, "my_jobs.py"), "a") as fd:
                        fd.write(
                            """
class MyOtherJob(MyJob):
    pass
register_jobs(MyOtherJob)
"""
                        )
                    jobs_data = get_jobs(reload=True)
                    self.assertIn("my_jobs.MyJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("my_jobs.MyJob"))
                    self.assertIn("my_jobs.MyOtherJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("my_jobs.MyOtherJob"))

                    # Create a third Job in another module
                    with open(os.path.join(temp_dir, "their_jobs.py"), "w") as fd:
                        fd.write(
                            """
from nautobot.apps.jobs import Job, register_jobs

class MyJob(Job):
    def run(self):
        pass
register_jobs(MyJob)
"""
                        )
                    jobs_data = get_jobs(reload=True)
                    self.assertIn("my_jobs.MyJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("my_jobs.MyJob"))
                    self.assertIn("my_jobs.MyOtherJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("my_jobs.MyOtherJob"))
                    self.assertIn("their_jobs.MyJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("their_jobs.MyJob"))
                    self.assertNotEqual(get_job("my_jobs.MyJob"), get_job("their_jobs.MyJob"))

                    # Delete a module
                    os.remove(os.path.join(temp_dir, "their_jobs.py"))
                    jobs_data = get_jobs(reload=True)
                    self.assertIn("my_jobs.MyJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("my_jobs.MyJob"))
                    self.assertIn("my_jobs.MyOtherJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("my_jobs.MyOtherJob"))
                    self.assertNotIn("their_jobs", jobs_data.keys())
                    self.assertIsNone(get_job("their_jobs.MyJob"))

                    # Create a module with an inauspicious name
                    with open(os.path.join(temp_dir, "traceback.py"), "w") as fd:
                        fd.write(
                            """
from nautobot.apps.jobs import Job, register_jobs

class BadJob(Job):
    def run(self):
        raise RuntimeError("You ran a bad job!")
register_jobs(BadJob)
"""
                        )
                    jobs_data = get_jobs(reload=True)
                    self.assertIn("my_jobs.MyJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("my_jobs.MyJob"))
                    self.assertIn("my_jobs.MyOtherJob", jobs_data.keys())
                    self.assertIsNotNone(get_job("my_jobs.MyOtherJob"))
                    # Since `traceback` conflicts with a system module, it should not get loaded
                    self.assertNotIn("traceback.BadJob", jobs_data.keys())
                    self.assertIsNone(get_job("traceback.BadJob"))

                    # TODO: testing with subdirectories/submodules under JOBS_ROOT...
        finally:
            # Clean up back to normal behavior
            get_jobs(reload=True)

    def test_app_dynamic_jobs(self):
        """
        Test that get_job() correctly reloads dynamic jobs when `NautobotAppConfig.provides_dynamic_jobs` is True.
        """
        with mock.patch("nautobot.extras.jobs.get_jobs", autospec=True) as mock_get_jobs:
            # example_app_with_view_override provides dynamic jobs
            get_job("example_app_with_view_override.jobs.ExampleHiddenJob", reload=True)
            mock_get_jobs.assert_called_once_with(reload=True)
            mock_get_jobs.reset_mock()
            # example_app does NOT provide dynamic jobs
            get_job("example_app.jobs.ExampleEverythingJob", reload=True)
            mock_get_jobs.assert_called_once_with(reload=False)


class JobTransactionTest(TransactionTestCase):
    """
    Test job features that require a transaction test case.
    """

    databases = ("default", "job_logs")
    maxDiff = None

    def setUp(self):
        super().setUp()

        # Initialize fake request that will be required to execute Webhooks (in jobs.)
        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

    def test_bulk_delete_system_jobs_fail(self):
        system_job_queryset = Job.objects.filter(module_name__startswith="nautobot.")
        pk_list = [str(pk) for pk in system_job_queryset.values_list("pk", flat=True)[:3]]
        initial_count = Job.objects.all().count()
        self.add_permissions("extras.delete_job")
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=ContentType.objects.get_for_model(Job).id,
            delete_all=False,
            filter_query_params={},
            pk_list=pk_list,
            username=self.user.username,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        error_log = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertIn(
            f"Unable to delete Job {system_job_queryset.first()}. System Job cannot be deleted", error_log.message
        )
        self.assertEqual(initial_count, Job.objects.all().count())

    def test_job_bulk_edit_default_queue_stays_default_after_one_field_update(self):
        self.add_permissions("extras.change_job", "extras.view_job")
        job_class_to_test = "TestPassJob"
        job_description = "default job queue test"
        job_to_test = Job.objects.get(job_class_name=job_class_to_test)
        queryset = Job.objects.filter(installed=True, hidden=False, job_class_name=job_class_to_test)
        default_job_queue = job_to_test.default_job_queue
        pk_list = list(queryset.values_list("pk", flat=True))

        job_ct = ContentType.objects.get_for_model(Job)
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=job_ct.id,
            edit_all=False,
            filter_query_params={},
            form_data={
                "pk": pk_list,
                "description": job_description,
            },
            username=self.user.username,
        )
        self.assertJobResultStatus(job_result)
        self.assertEqual(Job.objects.filter(description=job_description).count(), queryset.count())
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING).exists()
        )
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR).exists()
        )
        instance = Job.objects.get(job_class_name=job_class_to_test)
        self.assertEqual(instance.description, job_description)
        self.assertEqual(instance.default_job_queue, default_job_queue)

    def test_job_bulk_edit_preserve_job_queues_after_one_field_update(self):
        self.add_permissions("extras.change_job", "extras.view_job")
        job_class_to_test = "TestPassJob"
        job_description = "job queues test"
        job_to_test = Job.objects.get(job_class_name=job_class_to_test)

        # Simulate 3 job queues set
        job_queues = JobQueue.objects.all()[:3]
        job_to_test.job_queues.set(job_queues)
        job_to_test.job_queues.add(job_to_test.default_job_queue)
        job_to_test.job_queues_override = True
        job_to_test.save()

        expected_job_queues = list(job_to_test.job_queues.values_list("pk", flat=True))

        queryset = Job.objects.filter(installed=True, hidden=False, job_class_name=job_class_to_test)
        pk_list = list(queryset.values_list("pk", flat=True))

        job_ct = ContentType.objects.get_for_model(Job)
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=job_ct.id,
            edit_all=False,
            filter_query_params={},
            form_data={
                "pk": pk_list,
                "description": job_description,
            },
            username=self.user.username,
        )
        self.assertJobResultStatus(job_result)
        self.assertEqual(Job.objects.filter(description=job_description).count(), queryset.count())
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING).exists()
        )
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR).exists()
        )

        instance = Job.objects.get(job_class_name=job_class_to_test)
        self.assertEqual(instance.description, job_description)
        self.assertQuerySetEqual(instance.job_queues.all(), JobQueue.objects.filter(pk__in=expected_job_queues))

    def test_job_hard_time_limit_less_than_soft_time_limit(self):
        """
        Job test which produces a warning log message because the time_limit is less than the soft_time_limit.
        """
        module = "soft_time_limit_greater_than_time_limit"
        name = "TestSoftTimeLimitGreaterThanHardTimeLimit"
        job_result = create_job_result_and_run_job(module, name)
        log_warning = models.JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_WARNING, grouping="initialization"
        ).first()
        self.assertEqual(
            log_warning.message,
            "The hard time limit of 5.0 seconds is less than "
            "or equal to the soft time limit of 10.0 seconds. "
            "This job will fail silently after 5.0 seconds.",
        )

    def test_job_pass(self):
        """
        Job test with pass result.
        """
        module = "pass_job"
        name = "TestPassJob"
        job_result = create_job_result_and_run_job(module, name)
        self.assertJobResultStatus(job_result)
        self.assertEqual(job_result.result, True)
        logs = job_result.job_log_entries
        self.assertGreater(logs.count(), 0)
        try:
            logs.get(message="before_start() was called as expected")
            logs.get(message="Success")
            logs.get(message="on_success() was called as expected")
            logs.get(message="after_return() was called as expected")
        except models.JobLogEntry.DoesNotExist:
            for log in logs.all():
                print(log.message)
            print(job_result.traceback)
            raise

    def test_job_result_manager_censor_sensitive_variables(self):
        """
        Job test with JobResult Censored Sensitive Variables.
        """
        module = "has_sensitive_variables"
        name = "TestHasSensitiveVariables"
        # This function create_job_result_and_run_job and the subsequent functions' arguments are very messy
        job_result = create_job_result_and_run_job(module, name, "local", 1, 2, "3", kwarg_1=1, kwarg_2="2")
        self.assertJobResultStatus(job_result)
        self.assertEqual(job_result.task_args, [])
        self.assertEqual(job_result.task_kwargs, {})

    def test_job_fail(self):
        """
        Job test with fail result.
        """
        module = "fail"
        for name in ["TestFailJob", "TestFailInBeforeStart", "TestFailCleanly", "TestFailCleanlyInBeforeStart"]:
            with self.subTest(job=name):
                job_result = create_job_result_and_run_job(module, name)
                self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
                logs = job_result.job_log_entries
                self.assertGreater(logs.count(), 0)
                try:
                    logs.get(message="before_start() was called as expected")
                    logs.get(message="I'm a test job that fails!")
                    logs.get(message="on_failure() was called as expected")
                    logs.get(message="after_return() was called as expected")
                except models.JobLogEntry.DoesNotExist:
                    for log in logs.all():
                        print(log.message)
                    print(job_result.traceback)
                    raise

    def test_job_fail_with_sanitization(self):
        """
        Job test with fail result that is sanitized.
        """
        module = "fail"
        name = "TestFailWithSanitization"
        job_result = create_job_result_and_run_job(module, name)
        json_result = json.dumps(job_result.result)
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertIn("(redacted)@github.com", json_result)
        self.assertNotIn("abc123@github.com", json_result)
        self.assertIn("(redacted)@github.com", job_result.traceback)
        self.assertNotIn("abc123@github.com", job_result.traceback)

    def test_atomic_transaction_decorator_job_pass(self):
        """
        Job with @transaction.atomic decorator test with pass result.
        """
        module = "atomic_transaction"
        name = "TestAtomicDecorator"
        job_result = create_job_result_and_run_job(module, name)
        self.assertJobResultStatus(job_result)
        # Ensure DB transaction was not aborted
        self.assertTrue(models.Status.objects.filter(name="Test database atomic rollback 1").exists())
        # Ensure the correct job log messages were saved
        job_logs = models.JobLogEntry.objects.filter(job_result=job_result).values_list("message", flat=True)
        self.assertEqual(len(job_logs), 3)
        self.assertIn("Running job", job_logs)
        self.assertIn("Job succeeded.", job_logs)
        self.assertIn("Job completed", job_logs)
        self.assertNotIn("Job failed, all database changes have been rolled back.", job_logs)

    def test_atomic_transaction_context_manager_job_pass(self):
        """
        Job with `with transaction.atomic()` context manager test with pass result.
        """
        module = "atomic_transaction"
        name = "TestAtomicContextManager"
        job_result = create_job_result_and_run_job(module, name)
        self.assertJobResultStatus(job_result)
        # Ensure DB transaction was not aborted
        self.assertTrue(models.Status.objects.filter(name="Test database atomic rollback 2").exists())
        # Ensure the correct job log messages were saved
        job_logs = models.JobLogEntry.objects.filter(job_result=job_result).values_list("message", flat=True)
        self.assertEqual(len(job_logs), 3)
        self.assertIn("Running job", job_logs)
        self.assertIn("Job succeeded.", job_logs)
        self.assertIn("Job completed", job_logs)
        self.assertNotIn("Job failed, all database changes have been rolled back.", job_logs)

    def test_atomic_transaction_decorator_job_fail(self):
        """
        Job with @transaction.atomic decorator test with fail result.
        """
        module = "atomic_transaction"
        name = "TestAtomicDecorator"
        job_result = create_job_result_and_run_job(module, name, should_fail=True)
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        # Ensure DB transaction was aborted
        self.assertFalse(models.Status.objects.filter(name="Test database atomic rollback 1").exists())
        # Ensure the correct job log messages were saved
        job_logs = models.JobLogEntry.objects.filter(job_result=job_result).values_list("message", flat=True)
        self.assertEqual(len(job_logs), 2)
        self.assertIn("Running job", job_logs)
        self.assertIn("Job failed, all database changes have been rolled back.", job_logs)
        self.assertNotIn("Job succeeded.", job_logs)

    def test_atomic_transaction_context_manager_job_fail(self):
        """
        Job with `with transaction.atomic()` context manager test with fail result.
        """
        module = "atomic_transaction"
        name = "TestAtomicContextManager"
        job_result = create_job_result_and_run_job(module, name, should_fail=True)
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        # Ensure DB transaction was aborted
        self.assertFalse(models.Status.objects.filter(name="Test database atomic rollback 2").exists())
        # Ensure the correct job log messages were saved
        job_logs = models.JobLogEntry.objects.filter(job_result=job_result).values_list("message", flat=True)
        self.assertEqual(len(job_logs), 2)
        self.assertIn("Running job", job_logs)
        self.assertIn("Job failed, all database changes have been rolled back.", job_logs)
        self.assertNotIn("Job succeeded.", job_logs)

    def test_ip_address_vars(self):
        """
        Test that IPAddress variable fields behave as expected.

        This test case exercises the following types for both IPv4 and IPv6:

        - IPAddressVar
        - IPAddressWithMaskVar
        - IPNetworkVar
        """
        module = "ipaddress_vars"
        name = "TestIPAddresses"
        job_class, _job_model = get_job_class_and_model(module, name)

        # Fill out the form
        form_data = {
            "ipv4_address": "1.2.3.4",
            "ipv4_with_mask": "1.2.3.4/32",
            "ipv4_network": "1.2.3.0/24",
            "ipv6_address": "2001:db8::1",
            "ipv6_with_mask": "2001:db8::1/64",
            "ipv6_network": "2001:db8::/64",
        }
        form = job_class.as_form(form_data)
        self.assertTrue(form.is_valid())

        # Prepare the job data
        data = job_class.serialize_data(form.cleaned_data)
        # Need to pass a mock request object as execute_webhooks will be called with the creation of the objects.
        job_result = create_job_result_and_run_job(module, name, **data)

        log_info = models.JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        job_result_data = json.loads(log_info.log_object) if log_info.log_object else None

        # Assert stuff
        self.assertJobResultStatus(job_result)
        self.assertEqual(form_data, job_result_data)

    @override_settings(
        SANITIZER_PATTERNS=((re.compile(r"(secret is )\S+"), r"\1{replacement}"),),
    )
    def test_log_redaction(self):
        """
        Test that an attempt is made at log redaction.
        """
        module = "log_redaction"
        name = "TestLogRedaction"
        job_result = create_job_result_and_run_job(module, name)

        logs = models.JobLogEntry.objects.filter(job_result=job_result, grouping="run")
        self.assertGreater(logs.count(), 0)
        for log in logs:
            if log.message != "Job completed":
                self.assertEqual(log.message, "The secret is (redacted)")

    def test_log_skip_db_logging(self):
        """
        Test that an attempt is made at log redaction.
        """
        module = "log_skip_db_logging"
        name = "TestLogSkipDBLogging"
        job_result = create_job_result_and_run_job(module, name)

        logs = job_result.job_log_entries
        self.assertGreater(logs.count(), 0)
        self.assertFalse(logs.filter(message="I should NOT be logged to the database").exists())
        self.assertTrue(logs.filter(message="I should be logged to the database").exists())

    def test_object_vars(self):
        """
        Test that Object variable fields behave as expected.
        """
        module = "object_vars"
        name = "TestObjectVars"

        # Prepare the job data
        device_ct = ContentType.objects.get_for_model(Device)
        role = models.Role.objects.create(name="Device Role")
        role.content_types.add(device_ct)
        data = {
            "role": {"name": role.name},
            "roles": [role.pk],
        }
        job_result = create_job_result_and_run_job(module, name, **data)

        info_log = models.JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        # Assert stuff
        self.assertJobResultStatus(job_result)
        self.assertEqual(info_log.log_object, "")
        self.assertEqual(info_log.message, f"Role: {role.name}")
        self.assertEqual(job_result.result, "Nice Roles!")

    def test_optional_object_var(self):
        """
        Test that an optional Object variable field behaves as expected.
        """
        module = "object_var_optional"
        name = "TestOptionalObjectVar"
        data = {"location": None}
        job_result = create_job_result_and_run_job(module, name, **data)

        info_log = models.JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        # Assert stuff
        self.assertJobResultStatus(job_result)
        self.assertEqual(info_log.log_object, "")
        self.assertEqual(info_log.message, "The Location if any that the user provided.")
        self.assertEqual(job_result.result, "Nice Location (or not)!")

    def test_required_object_var(self):
        """
        Test that a required Object variable field behaves as expected.
        """
        module = "object_var_required"
        name = "TestRequiredObjectVar"
        data = {"location": None}
        job_result = create_job_result_and_run_job(module, name, **data)

        # Assert stuff
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertIn("location is a required field", job_result.traceback)

    def test_job_latest_result_property(self):
        """
        Job test to see if the latest_result property is indeed returning the most recent job result
        """
        module = "pass_job"
        name = "TestPassJob"
        job_result_1 = create_job_result_and_run_job(module, name)
        self.assertJobResultStatus(job_result_1)
        job_result_2 = create_job_result_and_run_job(module, name)
        self.assertJobResultStatus(job_result_2)
        _job_class, job_model = get_job_class_and_model(module, name)
        self.assertGreaterEqual(job_model.job_results.count(), 2)
        latest_job_result = job_model.latest_result
        self.assertEqual(job_result_2.date_done, latest_job_result.date_done)

    def test_job_profiling(self):
        module = "profiling"
        name = "TestProfilingJob"

        # The job itself contains the 'assert' by loading the resulting profiling file from the workers filesystem
        job_result = create_job_result_and_run_job(module, name, profile=True)

        self.assertJobResultStatus(job_result)

        profiling_result = Path(f"{tempfile.gettempdir()}/nautobot-jobresult-{job_result.id}.pstats")
        self.assertTrue(profiling_result.exists())
        profiling_result.unlink()

    def test_job_singleton(self):
        module = "singleton"
        name = "TestSingletonJob"

        job_class, _ = get_job_class_and_model(module, name, "local")
        self.assertTrue(job_class.is_singleton)
        cache.set(job_class.singleton_cache_key, 1)
        try:
            failed_job_result = create_job_result_and_run_job(module, name)

            self.assertEqual(
                failed_job_result.status,
                JobResultStatusChoices.STATUS_FAILURE,
                msg="Duplicate singleton job didn't error.",
            )
        finally:
            # Clean up after ourselves
            cache.delete(job_class.singleton_cache_key)

    def test_job_ignore_singleton(self):
        module = "singleton"
        name = "TestSingletonJob"

        job_class, _ = get_job_class_and_model(module, name, "local")
        self.assertTrue(job_class.is_singleton)
        cache.set(job_class.singleton_cache_key, 1)
        try:
            passed_job_result = create_job_result_and_run_job(
                module, name, celery_kwargs={"nautobot_job_ignore_singleton_lock": True}
            )

            self.assertEqual(
                passed_job_result.status,
                JobResultStatusChoices.STATUS_SUCCESS,
                msg="Duplicate singleton job didn't succeed with nautobot_job_ignore_singleton_lock=True.",
            )
            # Singleton cache key should be cleared when the job completes
            self.assertIsNone(cache.get(job_class.singleton_cache_key, None))
        finally:
            # Clean up after ourselves, just in case
            cache.delete(job_class.singleton_cache_key)

    @mock.patch("nautobot.extras.context_managers.enqueue_webhooks")
    def test_job_fires_webhooks(self, mock_enqueue_webhooks):
        module = "atomic_transaction"
        name = "TestAtomicDecorator"

        status_ct = ContentType.objects.get_for_model(models.Status)
        webhook = models.Webhook.objects.create(name="Test Webhook", type_create=True, payload_url="http://localhost/")
        webhook.content_types.set([status_ct])

        job_result = create_job_result_and_run_job(module, name)
        self.assertJobResultStatus(job_result)

        mock_enqueue_webhooks.assert_called_once()


class JobFileUploadTest(TransactionTestCase):
    """Test a job that uploads/deletes files."""

    databases = ("default", "job_logs")

    def setUp(self):
        super().setUp()

        self.file_contents = b"I am content.\n"
        self.test_file = SimpleUploadedFile(name="test_file.txt", content=self.file_contents)

        # Initialize fake request that will be required to execute Webhooks (in jobs.)
        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

    def test_run_job_pass(self):
        """Test that file upload succeeds; job SUCCEEDS; and files are deleted."""
        module = "file_upload_pass"
        name = "TestFileUploadPass"
        job_class, _job_model = get_job_class_and_model(module, name)

        # Serialize the file to FileProxy
        data = {"file": self.test_file}
        form = job_class.as_form(files=data)
        self.assertTrue(form.is_valid())
        serialized_data = job_class.serialize_data(form.cleaned_data)

        # Assert that the file was serialized to a FileProxy
        self.assertTrue(isinstance(serialized_data["file"], uuid.UUID))
        self.assertEqual(serialized_data["file"], models.FileProxy.objects.latest().pk)
        self.assertEqual(models.FileProxy.objects.count(), 1)

        # Run the job
        job_result = create_job_result_and_run_job(module, name, **serialized_data)

        warning_log = models.JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_WARNING, grouping="run"
        ).first()

        # Assert that file contents were correctly read
        self.assertEqual(warning_log.message, f"File contents: {self.file_contents}")  # "File contents: ..."

        # Assert that FileProxy was cleaned up
        self.assertEqual(models.FileProxy.objects.count(), 0)

    def test_run_job_fail(self):
        """Test that file upload succeeds; job FAILS; files deleted."""
        module = "file_upload_fail"
        name = "TestFileUploadFail"
        job_class, _job_model = get_job_class_and_model(module, name)

        # Serialize the file to FileProxy
        data = {"file": self.test_file}
        form = job_class.as_form(files=data)
        self.assertTrue(form.is_valid())
        serialized_data = job_class.serialize_data(form.cleaned_data)

        # Assert that the file was serialized to a FileProxy
        self.assertTrue(isinstance(serialized_data["file"], uuid.UUID))
        self.assertEqual(serialized_data["file"], models.FileProxy.objects.latest().pk)
        self.assertEqual(models.FileProxy.objects.count(), 1)

        # Run the job
        job_result = create_job_result_and_run_job(module, name, **serialized_data)
        self.assertIsNotNone(job_result.traceback)
        # TODO(jathan): If there are more use-cases for asserting class comparison for errors raised
        # by Jobs, factor this into a test case method.
        self.assertIn(job_class.exception.__name__, job_result.traceback)

        # Assert that file contents were correctly read
        self.assertEqual(
            models.JobLogEntry.objects.filter(
                job_result=job_result, log_level=LogLevelChoices.LOG_WARNING, grouping="run"
            )
            .first()
            .message,
            f"File contents: {self.file_contents}",
        )

        # Assert that FileProxy was cleaned up
        self.assertEqual(models.FileProxy.objects.count(), 0)


class JobFileOutputTest(TransactionTestCase):
    """Test a job that outputs files."""

    databases = ("default", "job_logs")

    @override_settings(
        MEDIA_ROOT=tempfile.gettempdir(),
    )
    def test_output_file_to_database(self):
        module = "file_output"
        name = "FileOutputJob"
        data = {"lines": 3}
        job_result = create_job_result_and_run_job(module, name, **data)

        self.assertJobResultStatus(job_result)
        # JobResult should have one attached file
        self.assertEqual(1, job_result.files.count())
        self.assertEqual(job_result.files.first().name, "output.txt")
        self.assertEqual(job_result.files.first().file.read().decode("utf-8"), "Hello World!\n" * 3)
        # File shouldn't exist on filesystem
        self.assertFalse(Path(settings.MEDIA_ROOT, "files", "output.txt").exists())
        self.assertFalse(Path(settings.MEDIA_ROOT, "files", f"{job_result.files.first().pk}-output.txt").exists())
        # File should exist in DB
        # `filename` value is weird, see https://github.com/victor-o-silva/db_file_storage/issues/22
        models.FileAttachment.objects.get(filename="extras.FileAttachment/bytes/filename/mimetype/output.txt")

        # Make sure cleanup is successful
        job_result.delete()
        with self.assertRaises(models.FileProxy.DoesNotExist):
            models.FileProxy.objects.get(name="output.txt")
        with self.assertRaises(models.FileAttachment.DoesNotExist):
            models.FileAttachment.objects.get(filename="extras.FileAttachment/bytes/filename/mimetype/output.txt")

    # It would be great to also test the output-to-filesystem case when using JOB_FILE_IO_STORAGE=FileSystemStorage;
    # unfortunately with FileField(storage=callable), the callable gets evaluated only at declaration time, not at
    # usage/runtime, so override_settings(JOB_FILE_IO_STORAGE) doesn't work the way you'd hope it would.

    def test_output_file_too_large(self):
        module = "file_output"
        name = "FileOutputJob"
        data = {"lines": 1}

        # Exactly JOB_CREATE_FILE_MAX_SIZE bytes should be okay:
        with override_config(JOB_CREATE_FILE_MAX_SIZE=len("Hello world!\n")):
            job_result = create_job_result_and_run_job(module, name, **data)
            self.assertJobResultStatus(job_result)
            self.assertEqual(1, job_result.files.count())
            self.assertEqual(job_result.files.first().name, "output.txt")
            self.assertEqual(job_result.files.first().file.read().decode("utf-8"), "Hello World!\n")

        # Even one byte over is too much:
        with override_config(JOB_CREATE_FILE_MAX_SIZE=len("Hello world!\n") - 1):
            job_result = create_job_result_and_run_job(module, name, **data)
            self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
            self.assertIn("ValueError", job_result.traceback)
            self.assertEqual(0, job_result.files.count())

        # settings takes precedence over constance config
        with override_config(JOB_CREATE_FILE_MAX_SIZE=10 << 20):
            with override_settings(JOB_CREATE_FILE_MAX_SIZE=len("Hello world!\n") - 1):
                job_result = create_job_result_and_run_job(module, name, **data)
                self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
                self.assertIn("ValueError", job_result.traceback)
                self.assertEqual(0, job_result.files.count())


class RunJobManagementCommandTest(TransactionTestCase):
    """Test cases for the `nautobot-server runjob` management command."""

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()

    def run_command(self, *args):
        out = StringIO()
        err = StringIO()
        call_command(
            "runjob",
            *args,
            stdout=out,
            stderr=err,
        )

        return (out.getvalue(), err.getvalue())

    def test_runjob_nochange_successful(self):
        """Basic success-path test for Jobs that don't modify the Nautobot database."""
        module = "pass_job"
        name = "TestPassJob"
        _job_class, job_model = get_job_class_and_model(module, name)

        out, err = self.run_command("--local", "--no-color", "--username", self.user.username, job_model.class_path)
        self.assertIn(f"Running {job_model.class_path}...", out)
        self.assertIn("run: 0 debug, 1 info, 0 success, 0 warning, 0 failure, 0 error, 0 critical", out)
        self.assertIn("info: Success", out)
        self.assertIn(f"{job_model.class_path}: SUCCESS", out)
        self.assertEqual("", err)

    def test_runjob_wrong_username(self):
        """A job when run with a nonexistent username, is rejected."""
        module = "modify_db"
        name = "TestModifyDB"
        _job_class, job_model = get_job_class_and_model(module, name)
        with self.assertRaises(CommandError):
            self.run_command("--username", "nosuchuser", job_model.class_path)

    def test_runjob_db_change(self):
        """A job that changes the DB, successfully updates the DB."""
        module = "modify_db"
        name = "TestModifyDB"
        _job_class, job_model = get_job_class_and_model(module, name)

        out, err = self.run_command("--local", "--no-color", "--username", self.user.username, job_model.class_path)
        self.assertIn(f"Running {job_model.class_path}...", out)
        # Changed job to actually log data. Can't display empty results if no logs were created.
        self.assertIn("run: 0 debug, 1 info, 0 success, 0 warning, 0 failure, 0 error, 0 critical", out)
        self.assertIn(f"{job_model.class_path}: SUCCESS", out)
        self.assertEqual("", err)

        success_log = models.JobLogEntry.objects.filter(
            log_level=LogLevelChoices.LOG_INFO, message="Status created successfully."
        )
        self.assertTrue(success_log.exists())
        self.assertEqual(success_log.count(), 1)

        status = models.Status.objects.get(name="Test Status")
        self.assertEqual(status.name, "Test Status")


class JobLocationCustomFieldTest(TransactionTestCase):
    """Test a job that creates a location and a custom field."""

    databases = ("default", "job_logs")

    def setUp(self):
        super().setUp()

        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

    def test_run(self):
        module = "location_with_custom_field"
        name = "TestCreateLocationWithCustomField"
        job_result = create_job_result_and_run_job(module, name)
        job_result.refresh_from_db()

        self.assertJobResultStatus(job_result)

        # Test location with a value for custom_field
        location_1 = Location.objects.filter(name="Test Location One")
        self.assertEqual(location_1.count(), 1)
        location_1 = location_1.first()
        self.assertEqual(models.CustomField.objects.filter(label="cf1").count(), 1)
        self.assertIn("cf1", location_1.cf)
        self.assertEqual(location_1.cf["cf1"], "some-value")

        # Test location with default value for custom field
        location_2 = Location.objects.filter(name="Test Location Two")
        self.assertEqual(location_2.count(), 1)
        location_2 = location_2.first()
        self.assertIn("cf1", location_2.cf)
        self.assertEqual(location_2.cf["cf1"], "-")


class JobButtonReceiverTest(TestCase):
    """
    Test job button receiver features that don't require a transaction test case.
    """

    def test_form_field(self):
        module = "job_button_receiver"
        name = "TestJobButtonReceiverSimple"
        job_class, _job_model = get_job_class_and_model(module, name)
        form = job_class.as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["object_pk", "object_model_name", "_job_queue", "_profile"])

    def test_hidden(self):
        module = "job_button_receiver"
        name = "TestJobButtonReceiverSimple"
        _job_class, job_model = get_job_class_and_model(module, name)
        self.assertFalse(job_model.hidden)

    def test_is_job_button(self):
        with self.subTest(expected=False):
            module = "pass_job"
            name = "TestPassJob"
            _job_class, job_model = get_job_class_and_model(module, name)
            self.assertFalse(job_model.is_job_button_receiver)

        with self.subTest(expected=True):
            module = "job_button_receiver"
            name = "TestJobButtonReceiverSimple"
            _job_class, job_model = get_job_class_and_model(module, name)
            self.assertTrue(job_model.is_job_button_receiver)


class JobButtonReceiverTransactionTest(TransactionTestCase):
    """
    Test job button receiver features that require a transaction test case.
    """

    def setUp(self):
        super().setUp()

        # Initialize fake request that will be required to run jobs
        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

        self.location_type = LocationType.objects.create(name="Test Root Type 2")
        status = models.Status.objects.get_for_model(Location).first()
        self.location = Location.objects.create(
            name="Test Job Button Location 1", location_type=self.location_type, status=status
        )
        content_type = ContentType.objects.get_for_model(Location)
        self.data = {
            "object_pk": self.location.pk,
            "object_model_name": f"{content_type.app_label}.{content_type.model}",
        }

    def test_missing_receive_job_button_method(self):
        module = "job_button_receiver"
        name = "TestJobButtonReceiverFail"
        job_result = create_job_result_and_run_job(module, name, **self.data)
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)


class JobHookReceiverTest(TestCase):
    """
    Test job hook receiver features that don't require a transaction test case.
    """

    def test_form_field(self):
        module = "job_hook_receiver"
        name = "TestJobHookReceiverLog"
        job_class, _job_model = get_job_class_and_model(module, name)
        form = job_class.as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["object_change", "_job_queue", "_profile"])

    def test_hidden(self):
        module = "job_hook_receiver"
        name = "TestJobHookReceiverLog"
        _job_class, job_model = get_job_class_and_model(module, name)
        self.assertFalse(job_model.hidden)

    def test_is_job_hook(self):
        with self.subTest(expected=False):
            module = "pass_job"
            name = "TestPassJob"
            _job_class, job_model = get_job_class_and_model(module, name)
            self.assertFalse(job_model.is_job_hook_receiver)

        with self.subTest(expected=True):
            module = "job_hook_receiver"
            name = "TestJobHookReceiverLog"
            _job_class, job_model = get_job_class_and_model(module, name)
            self.assertTrue(job_model.is_job_hook_receiver)


class JobHookReceiverTransactionTest(TransactionTestCase):
    """
    Test job hook receiver features that require a transaction test case.
    """

    def setUp(self):
        super().setUp()

        # Initialize fake request that will be required to run jobs
        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

        # generate an ObjectChange by creating a new location
        with web_request_context(self.user):
            location_type = LocationType.objects.create(name="Test Root Type 1")
            status = models.Status.objects.get_for_model(Location).first()
            location = Location(name="Test Location 1", location_type=location_type, status=status)
            location.save()
        location.refresh_from_db()
        oc = get_changes_for_model(location).first()
        self.data = {"object_change": oc.id}

    def test_object_change_context(self):
        module = "job_hook_receiver"
        name = "TestJobHookReceiverChange"
        job_result = create_job_result_and_run_job(module, name, **self.data)
        test_location = Location.objects.get(name="test_jhr")
        oc = get_changes_for_model(test_location).first()
        self.assertEqual(oc.change_context, ObjectChangeEventContextChoices.CONTEXT_JOB_HOOK)
        self.assertIsNotNone(job_result.user)
        self.assertEqual(oc.user_id, job_result.user.pk)

    def test_missing_receive_job_hook_method(self):
        module = "job_hook_receiver"
        name = "TestJobHookReceiverFail"
        job_result = create_job_result_and_run_job(module, name, **self.data)
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)


class JobHookTest(TestCase):
    """
    Test job hook features that don't require a transaction test case.
    """

    def setUp(self):
        super().setUp()

        module = "job_hook_receiver"
        name = "TestJobHookReceiverLog"
        self.job_class, self.job_model = get_job_class_and_model(module, name)
        job_hook = models.JobHook(
            name="JobHookTest",
            type_create=True,
            job=self.job_model,
        )
        obj_type = ContentType.objects.get_for_model(Location)
        self.location_type = LocationType.objects.create(name="Test Root Type 2")
        job_hook.save()
        job_hook.content_types.set([obj_type])

    @mock.patch.object(models.JobResult, "enqueue_job")
    def test_enqueue_job_hook_skipped(self, mock_enqueue_job):
        change_context = JobHookChangeContext(user=self.user)
        status = models.Status.objects.get_for_model(Location).first()
        with change_logging(change_context):
            Location.objects.create(name="Test Job Hook Location 2", location_type=self.location_type, status=status)

        self.assertFalse(mock_enqueue_job.called)


class JobHookTransactionTest(TransactionTestCase):  # TODO: BaseModelTestCase mixin?
    """
    Test job hook features that require a transaction test case.
    """

    def setUp(self):
        super().setUp()
        # Because of TransactionTestCase, and its clearing and repopulation of the database between tests,
        # the `change_logged_models_queryset` cache of ContentTypes becomes invalid.
        # We need to explicitly clear it here to have tests pass.
        # This is not a problem during normal operation of Nautobot because content-types don't normally get deleted
        # and recreated while Nautobot is running.
        cache.delete("nautobot.extras.utils.change_logged_models_queryset")

        module = "job_hook_receiver"
        name = "TestJobHookReceiverLog"
        self.job_class, self.job_model = get_job_class_and_model(module, name)
        self.assertIsNotNone(self.job_class)
        self.assertIsNotNone(self.job_model)
        job_hook = models.JobHook(
            name="JobHookTest",
            type_create=True,
            type_update=True,
            job=self.job_model,
        )
        obj_type = ContentType.objects.get_for_model(Location)
        self.location_type = LocationType.objects.create(name="Test Root Type 2")
        job_hook.save()
        job_hook.content_types.set([obj_type])

    def test_enqueue_job_hook(self):
        with web_request_context(user=self.user):
            status = models.Status.objects.get_for_model(Location).first()
            Location.objects.create(name="Test Job Hook Location 1", location_type=self.location_type, status=status)
        job_result = models.JobResult.objects.filter(job_model=self.job_model).first()
        self.assertIsNotNone(job_result)
        expected_log_messages = [
            ("info", "Running job"),
            ("info", f"change: dcim | location Test Job Hook Location 1 created by {self.user.username}"),
            ("info", "action: create"),
            ("info", f"jobresult.user: {self.user.username}"),
            ("info", "Test Job Hook Location 1"),
            ("success", "Job completed"),
        ]
        log_messages = models.JobLogEntry.objects.filter(job_result=job_result).values_list("log_level", "message")
        self.assertSequenceEqual(log_messages, expected_log_messages)

    def test_enqueue_job_hook_m2m(self):
        """
        Ensure that a change that's only M2M still triggers a JobHook.

        https://github.com/nautobot/nautobot/issues/4327
        """
        status = models.Status.objects.get_for_model(Location).first()
        loc = Location.objects.create(name="Test Job Hook Location 1", location_type=self.location_type, status=status)
        models.ObjectChange.objects.all().delete()
        tag = models.Tag.objects.create(name="A Test Tag")
        tag.content_types.add(ContentType.objects.get_for_model(Location))
        with web_request_context(user=self.user):
            loc.tags.add(tag)
        job_result = models.JobResult.objects.filter(job_model=self.job_model).first()
        self.assertIsNotNone(job_result)
        expected_log_messages = [
            ("info", "Running job"),
            ("info", f"change: dcim | location Test Job Hook Location 1 updated by {self.user.username}"),
            ("info", "action: update"),
            ("info", f"jobresult.user: {self.user.username}"),
            ("info", "Test Job Hook Location 1"),
            ("success", "Job completed"),
        ]
        log_messages = models.JobLogEntry.objects.filter(job_result=job_result).values_list("log_level", "message")
        self.assertSequenceEqual(log_messages, expected_log_messages)


class RemoveScheduledJobManagementCommandTestCase(TestCase):
    def test_remove_stale_scheduled_jobs(self):
        for i in range(1, 7):
            models.ScheduledJob.objects.create(
                name=f"test{i}",
                task="pass_job.TestPassJob",
                interval=JobExecutionType.TYPE_FUTURE,
                user=self.user,
                start_time=timezone.now() - datetime.timedelta(days=i * 30),
                one_off=i % 2 == 0,  # True / False
            )

        models.ScheduledJob.objects.create(
            name="test7",
            task="pass_job.TestPassJob",
            interval=JobExecutionType.TYPE_DAILY,
            user=self.user,
            start_time=timezone.now() - datetime.timedelta(days=180),
        )

        out = StringIO()
        call_command("remove_stale_scheduled_jobs", 32, stdout=out)
        self.assertEqual(models.ScheduledJob.objects.count(), 2)
        self.assertIn("Stale scheduled jobs deleted successfully", out.getvalue())
        self.assertTrue(models.ScheduledJob.objects.filter(name="test7").exists())
        self.assertTrue(models.ScheduledJob.objects.filter(name="test1").exists())
        for i in range(2, 7):
            self.assertFalse(models.ScheduledJob.objects.filter(name=f"test{i}").exists())


class ScheduledJobIntervalTestCase(TestCase):
    """Test scheduled job intervals"""

    # cron schedule day_of_week starts on Sunday (Sunday = 0)
    cron_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    # datetime weekday starts on Monday (Sunday = 6)
    datetime_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def test_weekly_interval(self):
        start_time = timezone.now() + datetime.timedelta(days=6)
        scheduled_job = models.ScheduledJob.objects.create(
            name="weekly_interval",
            task="pass_job.TestPassJob",
            interval=JobExecutionType.TYPE_WEEKLY,
            user=self.user,
            start_time=start_time,
        )

        requested_weekday = self.datetime_days[start_time.weekday()]
        schedule_day_of_week = next(iter(scheduled_job.schedule.day_of_week))
        scheduled_job_weekday = self.cron_days[schedule_day_of_week]
        self.assertEqual(scheduled_job_weekday, requested_weekday)
