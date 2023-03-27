import datetime
import json
import logging
import re
import uuid
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.test.client import RequestFactory
from django.utils import timezone

from nautobot.core.testing import (
    TestCase,
    TransactionTestCase,
    run_job_for_testing,
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
from nautobot.extras.jobs import get_job, run_job
from nautobot.extras.models import CustomField, FileProxy, Job, JobHook, JobResult, Role, ScheduledJob, Status
from nautobot.extras.models.models import JobLogEntry


def get_job_class_and_model(module, name):
    """Test helper function to look up a job class and job model and ensure the latter is enabled."""
    class_path = f"local/{module}/{name}"
    job_class = get_job(class_path)
    job_model = Job.objects.get_for_class_path(class_path)
    job_model.enabled = True
    job_model.validated_save()
    return (job_class, job_model)


def create_job_result_and_run_job(module, name, *, data=None, commit=True, request=None):
    """Test helper function to call get_job_class_and_model() then and call run_job_for_testing()."""
    if data is None:
        data = {}
    _job_class, job_model = get_job_class_and_model(module, name)
    job_result = run_job_for_testing(job=job_model, data=data, commit=commit, request=request)
    job_result.refresh_from_db()
    return job_result


class JobTest(TransactionTestCase):
    """
    Test basic jobs to ensure importing works.
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
        Job test which produces a log_warning because the time_limit is less than the soft_time_limit.
        """
        module = "test_soft_time_limit_greater_than_time_limit"
        name = "TestSoftTimeLimitGreaterThanHardTimeLimit"
        job_result = create_job_result_and_run_job(module, name, commit=False)
        log_warning = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_WARNING, grouping="initialization"
        ).first()
        self.assertEqual(
            log_warning.message,
            "The hard time limit of 5.0 seconds is less than "
            "or equal to the soft time limit of 10.0 seconds. "
            "This job will fail silently after 5.0 seconds.",
        )

    def test_job_pass_with_run_job_directly(self):
        """
        Job test with pass result calling run_job directly in order to test for backwards stability of its API.

        Because calling run_job directly used to be the best practice for testing jobs, we want to ensure that calling
        it still works even if we ever change the run_job call in the run_job_for_testing wrapper.
        """
        module = "test_pass"
        name = "TestPass"
        _job_class, job_model = get_job_class_and_model(module, name)
        job_model.enabled = True
        job_model.validated_save()
        job_content_type = ContentType.objects.get(app_label="extras", model="job")
        job_result = JobResult.objects.create(
            name=job_model.class_path,
            obj_type=job_content_type,
            job_model=job_model,
            user=None,
            task_id=uuid.uuid4(),
        )
        run_job(data={}, request=None, commit=False, job_result_pk=job_result.pk)
        job_result = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)

    def test_job_pass(self):
        """
        Job test with pass result.
        """
        module = "test_pass"
        name = "TestPass"
        job_result = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)

    def test_job_fail(self):
        """
        Job test with fail result.
        """
        module = "test_fail"
        name = "TestFail"
        logging.disable(logging.ERROR)
        job_result = create_job_result_and_run_job(module, name, commit=False)
        logging.disable(logging.NOTSET)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)

    def test_field_default(self):
        """
        Job test with field that is a default value that is falsey.
        https://github.com/nautobot/nautobot/issues/2039
        """
        module = "test_field_default"
        name = "TestFieldDefault"
        job_class = get_job(f"local/{module}/{name}")
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
        module = "test_field_order"
        name = "TestFieldOrder"
        job_class = get_job(f"local/{module}/{name}")
        form = job_class().as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["var1", "var2", "var23", "_task_queue", "_commit"])

    def test_no_field_order(self):
        """
        Job test without field_order.
        """
        module = "test_no_field_order"
        name = "TestNoFieldOrder"
        job_class = get_job(f"local/{module}/{name}")
        form = job_class().as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["var23", "var2", "_task_queue", "_commit"])

    def test_no_field_order_inherited_variable(self):
        """
        Job test without field_order with a variable inherited from the base class
        """
        module = "test_no_field_order"
        name = "TestDefaultFieldOrderWithInheritance"
        job_class = get_job(f"local/{module}/{name}")
        form = job_class().as_form()
        self.assertSequenceEqual(
            list(form.fields.keys()),
            ["testvar1", "b_testvar2", "a_testvar3", "_task_queue", "_commit"],
        )

    def test_read_only_job_pass(self):
        """
        Job read only test with pass result.
        """
        module = "test_read_only_pass"
        name = "TestReadOnlyPass"
        job_result = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertEqual(Location.objects.count(), 0)  # Ensure DB transaction was aborted

    def test_read_only_job_fail(self):
        """
        Job read only test with fail result.
        """
        module = "test_read_only_fail"
        name = "TestReadOnlyFail"
        logging.disable(logging.ERROR)
        job_result = create_job_result_and_run_job(module, name, commit=False)
        logging.disable(logging.NOTSET)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
        self.assertEqual(Location.objects.count(), 0)  # Ensure DB transaction was aborted
        # Also ensure the standard log message about aborting the transaction is *not* present
        run_log = JobLogEntry.objects.filter(grouping="run")
        for log in run_log:
            self.assertNotEqual(log.message, "Database changes have been reverted due to error.")

    def test_read_only_no_commit_field(self):
        """
        Job read only test commit field is not shown.
        """
        module = "test_read_only_no_commit_field"
        name = "TestReadOnlyNoCommitField"
        job_class = get_job(f"local/{module}/{name}")

        form = job_class().as_form()

        self.assertInHTML(
            "<input id='id__commit' name='_commit' type='hidden' value='False'>",
            form.as_table(),
        )

    def test_ip_address_vars(self):
        """
        Test that IPAddress variable fields behave as expected.

        This test case exercises the following types for both IPv4 and IPv6:

        - IPAddressVar
        - IPAddressWithMaskVar
        - IPNetworkVar
        """
        module = "test_ipaddress_vars"
        name = "TestIPAddresses"
        job_class, _job_model = get_job_class_and_model(module, name)

        # Fill out the form
        form_data = dict(
            ipv4_address="1.2.3.4",
            ipv4_with_mask="1.2.3.4/32",
            ipv4_network="1.2.3.0/24",
            ipv6_address="2001:db8::1",
            ipv6_with_mask="2001:db8::1/64",
            ipv6_network="2001:db8::/64",
        )
        form = job_class().as_form(form_data)
        self.assertTrue(form.is_valid())

        # Prepare the job data
        data = job_class.serialize_data(form.cleaned_data)
        # Need to pass a mock request object as execute_webhooks will be called with the creation of the objects.
        job_result = create_job_result_and_run_job(module, name, data=data, commit=False, request=self.request)

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
        module = "test_log_redaction"
        name = "TestLogRedaction"
        job_result = create_job_result_and_run_job(module, name, data=None, commit=True, request=self.request)

        logs = JobLogEntry.objects.filter(job_result=job_result, grouping="run")
        self.assertGreater(logs.count(), 0)
        for log in logs:
            self.assertEqual(log.message, "The secret is (redacted)")

    def test_object_vars(self):
        """
        Test that Object variable fields behave as expected.
        """
        module = "test_object_vars"
        name = "TestObjectVars"

        # Prepare the job data
        device_ct = ContentType.objects.get_for_model(Device)
        role = Role.objects.create(name="Device Role")
        role.content_types.add(device_ct)
        data = {
            "role": {"name": role.name},
            "roles": [role.pk],
        }
        job_result = create_job_result_and_run_job(module, name, data=data, commit=False, request=self.request)

        # Test storing additional data in job
        job_result_data = job_result.data["object_vars"]

        info_log = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertEqual({"role": str(role.pk), "roles": [str(role.pk)]}, job_result_data)
        self.assertEqual(info_log.log_object, "")
        self.assertEqual(info_log.message, f"Role: {role.name}")
        self.assertEqual(job_result.data["output"], "\nNice Roles!")

    def test_optional_object_var(self):
        """
        Test that an optional Object variable field behaves as expected.
        """
        module = "test_object_var_optional"
        name = "TestOptionalObjectVar"
        data = {"location": None}
        job_result = create_job_result_and_run_job(module, name, data=data, commit=True, request=self.request)

        info_log = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertEqual(info_log.log_object, "")
        self.assertEqual(info_log.message, "The Location if any that the user provided.")
        self.assertEqual(job_result.data["output"], "\nNice Location (or not)!")

    def test_required_object_var(self):
        """
        Test that a required Object variable field behaves as expected.
        """
        module = "test_object_var_required"
        name = "TestRequiredObjectVar"
        data = {"location": None}
        logging.disable(logging.ERROR)
        job_result = create_job_result_and_run_job(module, name, data=data, commit=False)
        logging.disable(logging.NOTSET)

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
        log_failure = JobLogEntry.objects.filter(
            grouping="initialization", log_level=LogLevelChoices.LOG_FAILURE
        ).first()
        self.assertIn("location is a required field", log_failure.message)

    def test_job_data_as_string(self):
        """
        Test that job doesn't error when not a dictionary.
        """
        module = "test_object_vars"
        name = "TestObjectVars"
        data = "BAD DATA STRING"
        logging.disable(logging.ERROR)
        job_result = create_job_result_and_run_job(module, name, data=data, commit=False)
        logging.disable(logging.NOTSET)
        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
        log_failure = JobLogEntry.objects.filter(
            grouping="initialization", log_level=LogLevelChoices.LOG_FAILURE
        ).first()
        self.assertIn("Data should be a dictionary", log_failure.message)

    def test_job_latest_result_property(self):
        """
        Job test to see if the latest_result property is indeed returning the most recent job result
        """
        module = "test_pass"
        name = "TestPass"
        job_result_1 = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result_1.status, JobResultStatusChoices.STATUS_SUCCESS)
        job_result_2 = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result_2.status, JobResultStatusChoices.STATUS_SUCCESS)
        _job_class, job_model = get_job_class_and_model(module, name)
        self.assertGreaterEqual(job_model.job_results.count(), 2)
        latest_job_result = job_model.latest_result
        self.assertEqual(job_result_2.date_done, latest_job_result.date_done)

    @mock.patch("nautobot.extras.utils.get_celery_queues")
    def test_job_class_task_queues(self, mock_get_celery_queues):
        """
        Test job form with custom task queues defined on the job class
        """
        module = "test_task_queues"
        name = "TestWorkerQueues"
        mock_get_celery_queues.return_value = {"celery": 4, "irrelevant": 5}
        job_class, _ = get_job_class_and_model(module, name)
        form = job_class().as_form()
        self.assertInHTML(
            """<tr><th><label for="id__task_queue">Task queue:</label></th>
            <td><select name="_task_queue" class="form-control" placeholder="Task queue" id="id__task_queue">
            <option value="celery">celery (4 workers)</option>
            <option value="nonexistent">nonexistent (0 workers)</option></select><br>
            <span class="helptext">The task queue to route this job to</span></td></tr>
            <tr><th><label for="id__commit">Commit changes:</label></th>
            <td><input type="checkbox" name="_commit" placeholder="Commit changes" id="id__commit" checked><br>
            <span class="helptext">Commit changes to the database (uncheck for a dry-run)</span></td></tr>""",
            form.as_table(),
        )

    @mock.patch("nautobot.extras.utils.get_celery_queues")
    def test_job_class_task_queues_override(self, mock_get_celery_queues):
        """
        Test job form with custom task queues defined on the job class and overridden on the model
        """
        module = "test_task_queues"
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
            </select><br><span class="helptext">The task queue to route this job to</span></td></tr>
            <tr><th><label for="id__commit">Commit changes:</label></th>
            <td><input type="checkbox" name="_commit" placeholder="Commit changes" id="id__commit" checked><br>
            <span class="helptext">Commit changes to the database (uncheck for a dry-run)</span></td></tr>""",
            form.as_table(),
        )


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
        module = "test_file_upload_pass"
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
        job_result = create_job_result_and_run_job(
            module, name, data=serialized_data, commit=False, request=self.request
        )

        warning_log = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_WARNING, grouping="run"
        ).first()

        # Assert that file contents were correctly read
        self.assertEqual(warning_log.message, f"File contents: {self.file_contents}")  # "File contents: ..."

        # Assert that FileProxy was cleaned up
        self.assertEqual(FileProxy.objects.count(), 0)

    def test_run_job_fail(self):
        """Test that file upload succeeds; job FAILS; files deleted."""
        module = "test_file_upload_fail"
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
        logging.disable(logging.ERROR)
        job_result = create_job_result_and_run_job(module, name, data=serialized_data, commit=False)
        self.assertIsNotNone(job_result.traceback)
        # TODO(jathan): If there are more use-cases for asserting class comparison for errors raised
        # by Jobs, factor this into a test case method.
        self.assertIn(job_class.exception.__name__, job_result.traceback)
        logging.disable(logging.NOTSET)

        # Assert that file contents were correctly read
        self.assertEqual(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING, grouping="run")
            .first()
            .message,
            f"File contents: {self.file_contents}",
        )
        # Also ensure the standard log message about aborting the transaction is present
        self.assertEqual(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run")
            .first()
            .message,
            "Database changes have been reverted due to error.",
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
        module = "test_pass"
        name = "TestPass"
        _job_class, job_model = get_job_class_and_model(module, name)

        out, err = self.run_command("--no-color", job_model.class_path)
        self.assertIn(f"Running {job_model.class_path}...", out)
        self.assertIn(f"{module}: 1 success, 1 info, 0 warning, 0 failure", out)
        self.assertIn("success: None", out)
        self.assertIn("info: Database changes have been reverted automatically.", out)
        self.assertIn(f"{job_model.class_path}: SUCCESS", out)
        self.assertEqual("", err)

    def test_runjob_db_change_no_commit(self):
        """A job that changes the DB, when run with commit=False, doesn't modify the database."""
        with self.assertRaises(ObjectDoesNotExist):
            Status.objects.get(slug="test-status")

        module = "test_modify_db"
        name = "TestModifyDB"
        _job_class, job_model = get_job_class_and_model(module, name)

        out, err = self.run_command("--no-color", job_model.class_path)
        self.assertIn(f"Running {job_model.class_path}...", out)
        self.assertIn(f"{module}: 1 success, 1 info, 0 warning, 0 failure", out)
        self.assertIn("success: Test Status: Status created successfully.", out)
        self.assertIn("info: Database changes have been reverted automatically.", out)
        self.assertIn(f"{job_model.class_path}: SUCCESS", out)
        self.assertEqual("", err)

        with self.assertRaises(ObjectDoesNotExist):
            Status.objects.get(slug="test-status")

        info_log = JobLogEntry.objects.filter(log_level=LogLevelChoices.LOG_INFO).first()
        self.assertEqual("Database changes have been reverted automatically.", info_log.message)

    def test_runjob_db_change_commit_no_username(self):
        """A job that changes the DB, when run with commit=True but no username, is rejected."""
        module = "test_modify_db"
        name = "TestModifyDB"
        _job_class, job_model = get_job_class_and_model(module, name)
        with self.assertRaises(CommandError):
            self.run_command("--commit", job_model.class_path)

    def test_runjob_db_change_commit_wrong_username(self):
        """A job that changes the DB, when run with commit=True and a nonexistent username, is rejected."""
        module = "test_modify_db"
        name = "TestModifyDB"
        _job_class, job_model = get_job_class_and_model(module, name)
        with self.assertRaises(CommandError):
            self.run_command("--commit", "--username", "nosuchuser", job_model.class_path)

    def test_runjob_db_change_commit_and_username(self):
        """A job that changes the DB, when run with commit=True and a username, successfully updates the DB."""
        get_user_model().objects.create(username="test_user")

        module = "test_modify_db"
        name = "TestModifyDB"
        _job_class, job_model = get_job_class_and_model(module, name)

        out, err = self.run_command("--no-color", "--commit", "--username", "test_user", job_model.class_path)
        self.assertIn(f"Running {job_model.class_path}...", out)
        # Changed job to actually log data. Can't display empty results if no logs were created.
        self.assertIn(f"{module}: 1 success, 0 info, 0 warning, 0 failure", out)
        self.assertIn(f"{job_model.class_path}: SUCCESS", out)
        self.assertEqual("", err)

        success_log = JobLogEntry.objects.filter(log_level=LogLevelChoices.LOG_SUCCESS).first()
        self.assertEqual(success_log.message, "Status created successfully.")

        status = Status.objects.get(slug="test-status")
        self.assertEqual(status.name, "Test Status")

        status.delete()


class JobLocationCustomFieldTest(TransactionTestCase):
    """Test a job that creates a location and a custom field."""

    databases = ("default", "job_logs")

    def setUp(self):
        super().setUp()

        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

    def test_run(self):
        module = "test_location_with_custom_field"
        name = "TestCreateLocationWithCustomField"
        job_result = create_job_result_and_run_job(module, name, request=self.request, commit=True)
        job_result.refresh_from_db()

        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)

        # Test location with a value for custom_field
        location_1 = Location.objects.filter(slug="test-location-one")
        self.assertEqual(location_1.count(), 1)
        self.assertEqual(CustomField.objects.filter(label="cf1").count(), 1)
        self.assertEqual(location_1[0].cf["cf1"], "some-value")

        # Test location with default value for custom field
        location_2 = Location.objects.filter(slug="test-location-two")
        self.assertEqual(location_2.count(), 1)
        self.assertEqual(location_2[0].cf["cf1"], "-")


class JobButtonReceiverTest(TransactionTestCase):
    """
    Test job button receiver.
    """

    def setUp(self):
        super().setUp()

        # Initialize fake request that will be required to run jobs
        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

        self.location_type = LocationType.objects.create(name="Test Root Type 2")
        self.location = Location.objects.create(name="Test Job Button Location 1", location_type=self.location_type)
        content_type = ContentType.objects.get_for_model(Location)
        self.data = {
            "object_pk": self.location.pk,
            "object_model_name": f"{content_type.app_label}.{content_type.model}",
        }

    def test_form_field(self):
        module = "test_job_button_receiver"
        name = "TestJobButtonReceiverSimple"
        job_class, _job_model = get_job_class_and_model(module, name)
        form = job_class().as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["object_pk", "object_model_name", "_task_queue", "_commit"])

    def test_hidden(self):
        module = "test_job_button_receiver"
        name = "TestJobButtonReceiverSimple"
        _job_class, job_model = get_job_class_and_model(module, name)
        self.assertFalse(job_model.hidden)

    def test_is_job_button(self):

        with self.subTest(expected=False):
            module = "test_pass"
            name = "TestPass"
            _job_class, job_model = get_job_class_and_model(module, name)
            self.assertFalse(job_model.is_job_button_receiver)

        with self.subTest(expected=True):
            module = "test_job_button_receiver"
            name = "TestJobButtonReceiverSimple"
            _job_class, job_model = get_job_class_and_model(module, name)
            self.assertTrue(job_model.is_job_button_receiver)

    def test_missing_receive_job_button_method(self):
        module = "test_job_button_receiver"
        name = "TestJobButtonReceiverFail"
        logging.disable(logging.ERROR)
        job_result = create_job_result_and_run_job(module, name, data=self.data, commit=False)
        logging.disable(logging.NOTSET)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)


class JobHookReceiverTest(TransactionTestCase):
    """
    Test job hook receiver.
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
            location = Location(name="Test Location 1", location_type=location_type)
            location.save()
        location.refresh_from_db()
        oc = get_changes_for_model(location).first()
        self.data = {"object_change": oc.id}

    def test_form_field(self):
        module = "test_job_hook_receiver"
        name = "TestJobHookReceiverLog"
        job_class, _job_model = get_job_class_and_model(module, name)
        form = job_class().as_form()
        self.assertSequenceEqual(list(form.fields.keys()), ["object_change", "_task_queue", "_commit"])

    def test_hidden(self):
        module = "test_job_hook_receiver"
        name = "TestJobHookReceiverLog"
        _job_class, job_model = get_job_class_and_model(module, name)
        self.assertFalse(job_model.hidden)

    def test_is_job_hook(self):
        with self.subTest(expected=False):
            module = "test_pass"
            name = "TestPass"
            _job_class, job_model = get_job_class_and_model(module, name)
            self.assertFalse(job_model.is_job_hook_receiver)

        with self.subTest(expected=True):
            module = "test_job_hook_receiver"
            name = "TestJobHookReceiverLog"
            _job_class, job_model = get_job_class_and_model(module, name)
            self.assertTrue(job_model.is_job_hook_receiver)

    def test_object_change_context(self):
        module = "test_job_hook_receiver"
        name = "TestJobHookReceiverChange"
        create_job_result_and_run_job(module, name, data=self.data, request=self.request)
        test_location = Location.objects.get(name="test_jhr")
        oc = get_changes_for_model(test_location).first()
        self.assertEqual(oc.change_context, ObjectChangeEventContextChoices.CONTEXT_JOB_HOOK)
        self.assertEqual(oc.user_id, self.user.pk)

    def test_missing_receive_job_hook_method(self):
        module = "test_job_hook_receiver"
        name = "TestJobHookReceiverFail"
        logging.disable(logging.ERROR)
        job_result = create_job_result_and_run_job(module, name, data=self.data, commit=False)
        logging.disable(logging.NOTSET)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)


class JobHookTest(TransactionTestCase):  # TODO: BaseModelTestCase mixin?
    """
    Test job hooks.
    """

    def setUp(self):
        super().setUp()

        module = "test_job_hook_receiver"
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
        with web_request_context(user=self.user):
            Location.objects.create(name="Test Job Hook Location 1", location_type=self.location_type)
            job_result = JobResult.objects.get(job_model=self.job_model)
            expected_log_messages = [
                ("info", f"change: dcim | location Test Job Hook Location 1 created by {self.user.username}"),
                ("info", "action: create"),
                ("info", f"request.user: {self.user.username}"),
                ("success", "Test Job Hook Location 1"),
            ]
            log_messages = JobLogEntry.objects.filter(job_result=job_result).values_list("log_level", "message")
            self.assertSequenceEqual(log_messages, expected_log_messages)

    @mock.patch.object(JobResult, "enqueue_job")
    def test_enqueue_job_hook_skipped(self, mock_enqueue_job):
        change_context = JobHookChangeContext(user=self.user)
        with change_logging(change_context):
            Location.objects.create(name="Test Job Hook Location 2", location_type=self.location_type)

        self.assertFalse(mock_enqueue_job.called)


class RemoveScheduledJobManagementCommandTestCase(TestCase):
    def test_remove_stale_scheduled_jobs(self):
        for i in range(1, 7):
            ScheduledJob.objects.create(
                name=f"test{i}",
                task="nautobot.extras.jobs.scheduled_job_handler",
                job_class="local/test_pass/TestPass",
                interval=JobExecutionType.TYPE_FUTURE,
                user=self.user,
                start_time=timezone.now() - datetime.timedelta(days=i * 30),
                one_off=i % 2 == 0,  # True / False
            )

        ScheduledJob.objects.create(
            name="test7",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="local/test_pass/TestPass",
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
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class="local/test_pass/TestPass",
            interval=JobExecutionType.TYPE_WEEKLY,
            user=self.user,
            start_time=start_time,
        )

        requested_weekday = self.datetime_days[start_time.weekday()]
        schedule_day_of_week = list(scheduled_job.schedule.day_of_week)[0]
        scheduled_job_weekday = self.cron_days[schedule_day_of_week]
        self.assertEqual(scheduled_job_weekday, requested_weekday)
