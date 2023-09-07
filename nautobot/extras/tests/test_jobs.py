import datetime
from io import StringIO
import json
from pathlib import Path
import re
from unittest import mock
import uuid
import tempfile

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.test.client import RequestFactory
from django.utils import timezone

from nautobot.core.testing import (
    TestCase,
    TransactionTestCase,
    create_job_result_and_run_job,
    get_job_class_and_model,
)
from nautobot.core.utils.lookup import get_changes_for_model
from nautobot.dcim.models import Device, Location, LocationType
from nautobot.extras.choices import (
    JobExecutionType,
    JobResultStatusChoices,
    LogLevelChoices,
    ObjectChangeEventContextChoices,
)
from nautobot.extras.context_managers import JobHookChangeContext, change_logging, web_request_context
from nautobot.extras.jobs import get_job
from nautobot.extras.models import CustomField, FileProxy, JobHook, JobResult, Role, ScheduledJob, Status
from nautobot.extras.models.models import JobLogEntry


class JobTest(TestCase):
    """
    Test job features that don't require a transaction test case.
    """

    def test_field_default(self):
        """
        Job test with field that is a default value that is falsey.
        https://github.com/nautobot/nautobot/issues/2039
        """
        module = "field_default"
        name = "TestFieldDefault"
        job_class = get_job(f"{module}.{name}")
        form = job_class().as_form()

        self.assertInHTML(
            """<tr><th><label for="id_var_int">Var int:</label></th><td>
<input class="form-control form-control" id="id_var_int" max="3600" name="var_int" placeholder="None" required type="number" value="0">
<br><span class="helptext">Test default of 0 Falsey</span></td></tr>
<tr><th><label for="id_var_int_no_default">Var int no default:</label></th><td>
<input class="form-control form-control" id="id_var_int_no_default" max="3600" name="var_int_no_default" placeholder="None" type="number">
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
        form = job_class().as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["var1", "var2", "var23", "_task_queue", "_profile"])

    def test_no_field_order(self):
        """
        Job test without field_order.
        """
        module = "no_field_order"
        name = "TestNoFieldOrder"
        job_class = get_job(f"{module}.{name}")
        form = job_class().as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["var23", "var2", "_task_queue", "_profile"])

    def test_no_field_order_inherited_variable(self):
        """
        Job test without field_order with a variable inherited from the base class
        """
        module = "no_field_order"
        name = "TestDefaultFieldOrderWithInheritance"
        job_class = get_job(f"{module}.{name}")
        form = job_class().as_form()
        self.assertSequenceEqual(
            list(form.fields.keys()),
            ["testvar1", "b_testvar2", "a_testvar3", "_task_queue", "_profile"],
        )

    def test_dryrun_default(self):
        """Test that dryrun_default is reflected in job form."""
        module = "dry_run"
        name = "TestDryRun"
        job_class, job_model = get_job_class_and_model(module, name)

        # not overridden on job model, initial form field value should match job class
        job_model.dryrun_default_override = False
        job_model.save()
        form = job_class().as_form()
        self.assertEqual(form.fields["dryrun"].initial, job_class.dryrun_default)

        # overridden on job model, initial form field value should match job model
        job_model.dryrun_default_override = True
        job_model.dryrun_default = not job_class.dryrun_default
        job_model.save()
        form = job_class().as_form()
        self.assertEqual(form.fields["dryrun"].initial, job_model.dryrun_default)

    @mock.patch("nautobot.extras.utils.get_celery_queues")
    def test_job_class_task_queues(self, mock_get_celery_queues):
        """
        Test job form with custom task queues defined on the job class
        """
        module = "task_queues"
        name = "TestWorkerQueues"
        mock_get_celery_queues.return_value = {"celery": 4, "irrelevant": 5}
        job_class, _ = get_job_class_and_model(module, name)
        form = job_class().as_form()
        self.assertInHTML(
            """<tr><th><label for="id__task_queue">Task queue:</label></th>
            <td><select name="_task_queue" class="form-control" placeholder="Task queue" id="id__task_queue">
            <option value="celery">celery (4 workers)</option>
            <option value="nonexistent">nonexistent (0 workers)</option></select><br>
            <span class="helptext">The task queue to route this job to</span>
            <input type="hidden" name="_profile" value="False" id="id__profile"></td></tr>""",
            form.as_table(),
        )

    @mock.patch("nautobot.extras.utils.get_celery_queues")
    def test_job_class_task_queues_override(self, mock_get_celery_queues):
        """
        Test job form with custom task queues defined on the job class and overridden on the model
        """
        module = "task_queues"
        name = "TestWorkerQueues"
        mock_get_celery_queues.return_value = {"default": 1, "irrelevant": 5}
        job_class, job_model = get_job_class_and_model(module, name)
        job_model.task_queues = ["default", "priority"]
        job_model.task_queues_override = True
        job_model.save()
        form = job_class().as_form()
        self.assertInHTML(
            """<tr><th><label for="id__task_queue">Task queue:</label></th>
            <td><select name="_task_queue" class="form-control" placeholder="Task queue" id="id__task_queue">
            <option value="default">default (1 worker)</option>
            <option value="priority">priority (0 workers)</option>
            </select><br><span class="helptext">The task queue to route this job to</span>
            <input type="hidden" name="_profile" value="False" id="id__profile"></td></tr>""",
            form.as_table(),
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

        module = "pass"
        name = "TestPass"
        job_class, job_model = get_job_class_and_model(module, name)
        self.assertFalse(job_class.supports_dryrun)
        self.assertFalse(job_model.supports_dryrun)


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

    def test_job_hard_time_limit_less_than_soft_time_limit(self):
        """
        Job test which produces a warning log message because the time_limit is less than the soft_time_limit.
        """
        module = "soft_time_limit_greater_than_time_limit"
        name = "TestSoftTimeLimitGreaterThanHardTimeLimit"
        job_result = create_job_result_and_run_job(module, name)
        log_warning = JobLogEntry.objects.filter(
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
        module = "pass"
        name = "TestPass"
        job_result = create_job_result_and_run_job(module, name)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)

    def test_job_result_manager_censor_sensitive_variables(self):
        """
        Job test with JobResult Censored Sensitive Variables.
        """
        module = "has_sensitive_variables"
        name = "TestHasSensitiveVariables"
        # This function create_job_result_and_run_job and the subsequent functions' arguments are very messy
        job_result = create_job_result_and_run_job(module, name, "local", 1, 2, "3", kwarg_1=1, kwarg_2="2")
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertEqual(job_result.task_args, [])
        self.assertEqual(job_result.task_kwargs, {})

    def test_job_fail(self):
        """
        Job test with fail result.
        """
        module = "fail"
        name = "TestFail"
        job_result = create_job_result_and_run_job(module, name)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)

    def test_atomic_transaction_decorator_job_pass(self):
        """
        Job with @transaction.atomic decorator test with pass result.
        """
        module = "atomic_transaction"
        name = "TestAtomicDecorator"
        job_result = create_job_result_and_run_job(module, name)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        # Ensure DB transaction was not aborted
        self.assertTrue(Status.objects.filter(name="Test database atomic rollback 1").exists())
        # Ensure the correct job log messages were saved
        job_logs = JobLogEntry.objects.filter(job_result=job_result).values_list("message", flat=True)
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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        # Ensure DB transaction was not aborted
        self.assertTrue(Status.objects.filter(name="Test database atomic rollback 2").exists())
        # Ensure the correct job log messages were saved
        job_logs = JobLogEntry.objects.filter(job_result=job_result).values_list("message", flat=True)
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
        job_result = create_job_result_and_run_job(module, name, fail=True)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
        # Ensure DB transaction was aborted
        self.assertFalse(Status.objects.filter(name="Test database atomic rollback 1").exists())
        # Ensure the correct job log messages were saved
        job_logs = JobLogEntry.objects.filter(job_result=job_result).values_list("message", flat=True)
        self.assertEqual(len(job_logs), 3)
        self.assertIn("Running job", job_logs)
        self.assertIn("Job failed, all database changes have been rolled back.", job_logs)
        self.assertIn("Job completed", job_logs)
        self.assertNotIn("Job succeeded.", job_logs)

    def test_atomic_transaction_context_manager_job_fail(self):
        """
        Job with `with transaction.atomic()` context manager test with fail result.
        """
        module = "atomic_transaction"
        name = "TestAtomicContextManager"
        job_result = create_job_result_and_run_job(module, name, fail=True)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
        # Ensure DB transaction was aborted
        self.assertFalse(Status.objects.filter(name="Test database atomic rollback 2").exists())
        # Ensure the correct job log messages were saved
        job_logs = JobLogEntry.objects.filter(job_result=job_result).values_list("message", flat=True)
        self.assertEqual(len(job_logs), 3)
        self.assertIn("Running job", job_logs)
        self.assertIn("Job failed, all database changes have been rolled back.", job_logs)
        self.assertIn("Job completed", job_logs)
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
        form = job_class().as_form(form_data)
        self.assertTrue(form.is_valid())

        # Prepare the job data
        data = job_class.serialize_data(form.cleaned_data)
        # Need to pass a mock request object as execute_webhooks will be called with the creation of the objects.
        job_result = create_job_result_and_run_job(module, name, **data)

        log_info = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        job_result_data = json.loads(log_info.log_object) if log_info.log_object else None

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
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

        logs = JobLogEntry.objects.filter(job_result=job_result, grouping="run")
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
        role = Role.objects.create(name="Device Role")
        role.content_types.add(device_ct)
        data = {
            "role": {"name": role.name},
            "roles": [role.pk],
        }
        job_result = create_job_result_and_run_job(module, name, **data)

        info_log = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
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

        info_log = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
        self.assertIn("location is a required field", job_result.traceback)

    def test_job_latest_result_property(self):
        """
        Job test to see if the latest_result property is indeed returning the most recent job result
        """
        module = "pass"
        name = "TestPass"
        job_result_1 = create_job_result_and_run_job(module, name)
        self.assertEqual(job_result_1.status, JobResultStatusChoices.STATUS_SUCCESS)
        job_result_2 = create_job_result_and_run_job(module, name)
        self.assertEqual(job_result_2.status, JobResultStatusChoices.STATUS_SUCCESS)
        _job_class, job_model = get_job_class_and_model(module, name)
        self.assertGreaterEqual(job_model.job_results.count(), 2)
        latest_job_result = job_model.latest_result
        self.assertEqual(job_result_2.date_done, latest_job_result.date_done)

    def test_job_profiling(self):
        module = "profiling"
        name = "TestProfilingJob"

        # The job itself contains the 'assert' by loading the resulting profiling file from the workers filesystem
        job_result = create_job_result_and_run_job(module, name, profile=True)

        self.assertEqual(
            job_result.status,
            JobResultStatusChoices.STATUS_SUCCESS,
            msg="Profiling test job errored, this indicates that either no profiling file was created or it is malformed.",
        )

        profiling_result = Path(f"{tempfile.gettempdir()}/nautobot-jobresult-{job_result.id}.pstats")
        self.assertTrue(profiling_result.exists())
        profiling_result.unlink()


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
        form = job_class().as_form(files=data)
        self.assertTrue(form.is_valid())
        serialized_data = job_class.serialize_data(form.cleaned_data)

        # Assert that the file was serialized to a FileProxy
        self.assertTrue(isinstance(serialized_data["file"], uuid.UUID))
        self.assertEqual(serialized_data["file"], FileProxy.objects.latest().pk)
        self.assertEqual(FileProxy.objects.count(), 1)

        # Run the job
        job_result = create_job_result_and_run_job(module, name, **serialized_data)

        warning_log = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_WARNING, grouping="run"
        ).first()

        # Assert that file contents were correctly read
        self.assertEqual(warning_log.message, f"File contents: {self.file_contents}")  # "File contents: ..."

        # Assert that FileProxy was cleaned up
        self.assertEqual(FileProxy.objects.count(), 0)

    def test_run_job_fail(self):
        """Test that file upload succeeds; job FAILS; files deleted."""
        module = "file_upload_fail"
        name = "TestFileUploadFail"
        job_class, _job_model = get_job_class_and_model(module, name)

        # Serialize the file to FileProxy
        data = {"file": self.test_file}
        form = job_class().as_form(files=data)
        self.assertTrue(form.is_valid())
        serialized_data = job_class.serialize_data(form.cleaned_data)

        # Assert that the file was serialized to a FileProxy
        self.assertTrue(isinstance(serialized_data["file"], uuid.UUID))
        self.assertEqual(serialized_data["file"], FileProxy.objects.latest().pk)
        self.assertEqual(FileProxy.objects.count(), 1)

        # Run the job
        job_result = create_job_result_and_run_job(module, name, **serialized_data)
        self.assertIsNotNone(job_result.traceback)
        # TODO(jathan): If there are more use-cases for asserting class comparison for errors raised
        # by Jobs, factor this into a test case method.
        self.assertIn(job_class.exception.__name__, job_result.traceback)

        # Assert that file contents were correctly read
        self.assertEqual(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING, grouping="run")
            .first()
            .message,
            f"File contents: {self.file_contents}",
        )

        # Assert that FileProxy was cleaned up
        self.assertEqual(FileProxy.objects.count(), 0)


class RunJobManagementCommandTest(TransactionTestCase):
    """Test cases for the `nautobot-server runjob` management command."""

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
        module = "pass"
        name = "TestPass"
        _job_class, job_model = get_job_class_and_model(module, name)

        out, err = self.run_command("--local", "--no-color", "--username", self.user.username, job_model.class_path)
        self.assertIn(f"Running {job_model.class_path}...", out)
        self.assertIn("run: 0 debug, 1 info, 0 warning, 0 error, 0 critical", out)
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
        self.assertIn("run: 0 debug, 1 info, 0 warning, 0 error, 0 critical", out)
        self.assertIn(f"{job_model.class_path}: SUCCESS", out)
        self.assertEqual("", err)

        success_log = JobLogEntry.objects.filter(
            log_level=LogLevelChoices.LOG_INFO, message="Status created successfully."
        )
        self.assertTrue(success_log.exists())
        self.assertEqual(success_log.count(), 1)

        status = Status.objects.get(name="Test Status")
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

        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)

        # Test location with a value for custom_field
        location_1 = Location.objects.filter(name="Test Location One")
        self.assertEqual(location_1.count(), 1)
        location_1 = location_1.first()
        self.assertEqual(CustomField.objects.filter(label="cf1").count(), 1)
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
        form = job_class().as_form()
        self.assertSequenceEqual(
            list(form.fields.keys()), ["object_pk", "object_model_name", "_task_queue", "_profile"]
        )

    def test_hidden(self):
        module = "job_button_receiver"
        name = "TestJobButtonReceiverSimple"
        _job_class, job_model = get_job_class_and_model(module, name)
        self.assertFalse(job_model.hidden)

    def test_is_job_button(self):
        with self.subTest(expected=False):
            module = "pass"
            name = "TestPass"
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
        status = Status.objects.get_for_model(Location).first()
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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)


class JobHookReceiverTest(TestCase):
    """
    Test job hook receiver features that don't require a transaction test case.
    """

    def test_form_field(self):
        module = "job_hook_receiver"
        name = "TestJobHookReceiverLog"
        job_class, _job_model = get_job_class_and_model(module, name)
        form = job_class().as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["object_change", "_task_queue", "_profile"])

    def test_hidden(self):
        module = "job_hook_receiver"
        name = "TestJobHookReceiverLog"
        _job_class, job_model = get_job_class_and_model(module, name)
        self.assertFalse(job_model.hidden)

    def test_is_job_hook(self):
        with self.subTest(expected=False):
            module = "pass"
            name = "TestPass"
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
            status = Status.objects.get_for_model(Location).first()
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
        self.assertEqual(oc.user_id, job_result.user.pk)

    def test_missing_receive_job_hook_method(self):
        module = "job_hook_receiver"
        name = "TestJobHookReceiverFail"
        job_result = create_job_result_and_run_job(module, name, **self.data)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)


class JobHookTest(TestCase):
    """
    Test job hook features that don't require a transaction test case.
    """

    def setUp(self):
        super().setUp()

        module = "job_hook_receiver"
        name = "TestJobHookReceiverLog"
        self.job_class, self.job_model = get_job_class_and_model(module, name)
        job_hook = JobHook(
            name="JobHookTest",
            type_create=True,
            job=self.job_model,
        )
        obj_type = ContentType.objects.get_for_model(Location)
        self.location_type = LocationType.objects.create(name="Test Root Type 2")
        job_hook.save()
        job_hook.content_types.set([obj_type])

    @mock.patch.object(JobResult, "enqueue_job")
    def test_enqueue_job_hook_skipped(self, mock_enqueue_job):
        change_context = JobHookChangeContext(user=self.user)
        status = Status.objects.get_for_model(Location).first()
        with change_logging(change_context):
            Location.objects.create(name="Test Job Hook Location 2", location_type=self.location_type, status=status)

        self.assertFalse(mock_enqueue_job.called)


class JobHookTransactionTest(TransactionTestCase):  # TODO: BaseModelTestCase mixin?
    """
    Test job hook features that require a transaction test case.
    """

    def setUp(self):
        super().setUp()

        module = "job_hook_receiver"
        name = "TestJobHookReceiverLog"
        self.job_class, self.job_model = get_job_class_and_model(module, name)
        job_hook = JobHook(
            name="JobHookTest",
            type_create=True,
            job=self.job_model,
        )
        obj_type = ContentType.objects.get_for_model(Location)
        self.location_type = LocationType.objects.create(name="Test Root Type 2")
        job_hook.save()
        job_hook.content_types.set([obj_type])

    def test_enqueue_job_hook(self):
        self.assertEqual(JobLogEntry.objects.count(), 0)
        with web_request_context(user=self.user):
            status = Status.objects.get_for_model(Location).first()
            Location.objects.create(name="Test Job Hook Location 1", location_type=self.location_type, status=status)
            job_result = JobResult.objects.get(job_model=self.job_model)
            expected_log_messages = [
                ("info", "Running job"),
                ("info", f"change: dcim | location Test Job Hook Location 1 created by {self.user.username}"),
                ("info", "action: create"),
                ("info", f"jobresult.user: {self.user.username}"),
                ("info", "Test Job Hook Location 1"),
                ("info", "Job completed"),
            ]
            log_messages = JobLogEntry.objects.filter(job_result=job_result).values_list("log_level", "message")
            self.assertSequenceEqual(log_messages, expected_log_messages)


class RemoveScheduledJobManagementCommandTestCase(TestCase):
    def test_remove_stale_scheduled_jobs(self):
        for i in range(1, 7):
            ScheduledJob.objects.create(
                name=f"test{i}",
                task="pass.TestPass",
                interval=JobExecutionType.TYPE_FUTURE,
                user=self.user,
                start_time=timezone.now() - datetime.timedelta(days=i * 30),
                one_off=i % 2 == 0,  # True / False
            )

        ScheduledJob.objects.create(
            name="test7",
            task="pass.TestPass",
            interval=JobExecutionType.TYPE_DAILY,
            user=self.user,
            start_time=timezone.now() - datetime.timedelta(days=180),
        )

        out = StringIO()
        call_command("remove_stale_scheduled_jobs", 32, stdout=out)
        self.assertEqual(ScheduledJob.objects.count(), 2)
        self.assertIn("Stale scheduled jobs deleted successfully", out.getvalue())
        self.assertTrue(ScheduledJob.objects.filter(name="test7").exists())
        self.assertTrue(ScheduledJob.objects.filter(name="test1").exists())
        for i in range(2, 7):
            self.assertFalse(ScheduledJob.objects.filter(name=f"test{i}").exists())


class ScheduledJobIntervalTestCase(TestCase):
    """Test scheduled job intervals"""

    # cron schedule day_of_week starts on Sunday (Sunday = 0)
    cron_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    # datetime weekday starts on Monday (Sunday = 6)
    datetime_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def test_weekly_interval(self):
        start_time = timezone.now() + datetime.timedelta(days=6)
        scheduled_job = ScheduledJob.objects.create(
            name="weekly_interval",
            task="pass.TestPass",
            interval=JobExecutionType.TYPE_WEEKLY,
            user=self.user,
            start_time=start_time,
        )

        requested_weekday = self.datetime_days[start_time.weekday()]
        schedule_day_of_week = list(scheduled_job.schedule.day_of_week)[0]
        scheduled_job_weekday = self.cron_days[schedule_day_of_week]
        self.assertEqual(scheduled_job_weekday, requested_weekday)
