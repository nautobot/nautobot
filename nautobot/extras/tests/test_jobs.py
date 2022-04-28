import json
from io import StringIO
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model
from django.test.client import RequestFactory

from nautobot.dcim.models import DeviceRole, Site
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.jobs import get_job, run_job
from nautobot.extras.models import FileProxy, Job, Status, CustomField, JobResult
from nautobot.extras.models.models import JobLogEntry
from nautobot.utilities.testing import CeleryTestCase, TransactionTestCase, run_job_for_testing

# Use the proper swappable User model
User = get_user_model()


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
    job_class, job_model = get_job_class_and_model(module, name)
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
        self.user = User.objects.create_user(username="testuser")
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
        job_class, job_model = get_job_class_and_model(module, name)
        job_content_type = ContentType.objects.get(app_label="extras", model="job")
        job_result = JobResult.objects.create(
            name=job_model.class_path,
            obj_type=job_content_type,
            job_model=job_model,
            user=None,
            job_id=uuid.uuid4(),
        )
        run_job(data={}, request=None, commit=False, job_result_pk=job_result.pk)
        job_result = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)

    def test_job_pass(self):
        """
        Job test with pass result.
        """
        module = "test_pass"
        name = "TestPass"
        job_result = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)

    def test_job_fail(self):
        """
        Job test with fail result.
        """
        module = "test_fail"
        name = "TestFail"
        job_result = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_ERRORED)

    def test_field_order(self):
        """
        Job test with field order.
        """
        module = "test_field_order"
        name = "TestFieldOrder"
        job_class = get_job(f"local/{module}/{name}")

        form = job_class().as_form()

        self.assertHTMLEqual(
            form.as_table(),
            """<tr><th><label for="id_var1">Var1:</label></th><td>
<input class="form-control form-control" id="id_var1" name="var1" placeholder="None" required type="file">
<br><span class="helptext">Some file wants to be first</span></td></tr>
<tr><th><label for="id_var2">Var2:</label></th><td>
<input class="form-control form-control" id="id_var2" name="var2" placeholder="None" required type="text">
<br><span class="helptext">Hello</span></td></tr>
<tr><th><label for="id_var23">Var23:</label></th><td>
<input class="form-control form-control" id="id_var23" name="var23" placeholder="None" required type="text">
<br><span class="helptext">I want to be second</span></td></tr>
<tr><th><label for="id__commit">Commit changes:</label></th><td>
<input checked id="id__commit" name="_commit" placeholder="Commit changes" type="checkbox">
<br><span class="helptext">Commit changes to the database (uncheck for a dry-run)</span></td></tr>""",
        )

    def test_no_field_order(self):
        """
        Job test without field_order.
        """
        module = "test_no_field_order"
        name = "TestNoFieldOrder"
        job_class = get_job(f"local/{module}/{name}")

        form = job_class().as_form()

        self.assertHTMLEqual(
            form.as_table(),
            """<tr><th><label for="id_var23">Var23:</label></th><td>
<input class="form-control form-control" id="id_var23" name="var23" placeholder="None" required type="text">
<br><span class="helptext">I want to be second</span></td></tr>
<tr><th><label for="id_var2">Var2:</label></th><td>
<input class="form-control form-control" id="id_var2" name="var2" placeholder="None" required type="text">
<br><span class="helptext">Hello</span></td></tr>
<tr><th><label for="id__commit">Commit changes:</label></th><td>
<input checked id="id__commit" name="_commit" placeholder="Commit changes" type="checkbox">
<br><span class="helptext">Commit changes to the database (uncheck for a dry-run)</span></td></tr>""",
        )

    def test_read_only_job_pass(self):
        """
        Job read only test with pass result.
        """
        module = "test_read_only_pass"
        name = "TestReadOnlyPass"
        job_result = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)
        self.assertEqual(Site.objects.count(), 0)  # Ensure DB transaction was aborted

    def test_read_only_job_fail(self):
        """
        Job read only test with fail result.
        """
        module = "test_read_only_fail"
        name = "TestReadOnlyFail"
        job_result = create_job_result_and_run_job(module, name, commit=False)
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_ERRORED)
        self.assertEqual(Site.objects.count(), 0)  # Ensure DB transaction was aborted
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

        self.assertHTMLEqual(
            form.as_table(),
            """<tr><th><label for="id_var">Var:</label></th><td>
<input class="form-control form-control" id="id_var" name="var" placeholder="None" required type="text">
<br><span class="helptext">Hello</span><input id="id__commit" name="_commit" type="hidden" value="False"></td></tr>""",
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
        job_class, job_model = get_job_class_and_model(module, name)

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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)
        self.assertEqual(form_data, job_result_data)

    def test_object_vars(self):
        """
        Test that Object variable fields behave as expected.
        """
        module = "test_object_vars"
        name = "TestObjectVars"

        # Prepare the job data
        d = DeviceRole.objects.create(name="role", slug="role")
        data = {
            "role": {"name": "role"},
            "roles": [d.pk],
        }
        job_result = create_job_result_and_run_job(module, name, data=data, commit=False, request=self.request)

        # Test storing additional data in job
        job_result_data = job_result.data["object_vars"]

        info_log = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)
        self.assertEqual({"role": str(d.pk), "roles": [str(d.pk)]}, job_result_data)
        self.assertEqual(info_log.log_object, None)
        self.assertEqual(info_log.message, "Role: role")
        self.assertEqual(job_result.data["output"], "\nNice Roles!")

    def test_optional_object_var(self):
        """
        Test that an optional Object variable field behaves as expected.
        """
        module = "test_object_var_optional"
        name = "TestOptionalObjectVar"
        data = {"region": None}
        job_result = create_job_result_and_run_job(module, name, data=data, commit=True, request=self.request)

        info_log = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
        ).first()

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)
        self.assertEqual(info_log.log_object, None)
        self.assertEqual(info_log.message, "The Region if any that the user provided.")
        self.assertEqual(job_result.data["output"], "\nNice Region (or not)!")

    def test_required_object_var(self):
        """
        Test that a required Object variable field behaves as expected.
        """
        module = "test_object_var_required"
        name = "TestRequiredObjectVar"
        data = {"region": None}

        job_result = create_job_result_and_run_job(module, name, data=data, commit=False)

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_ERRORED)
        log_failure = JobLogEntry.objects.filter(
            grouping="initialization", log_level=LogLevelChoices.LOG_FAILURE
        ).first()
        self.assertIn("region is a required field", log_failure.message)

    def test_job_data_as_string(self):
        """
        Test that job doesn't error when not a dictionary.
        """
        module = "test_object_vars"
        name = "TestObjectVars"
        data = "BAD DATA STRING"

        job_result = create_job_result_and_run_job(module, name, data=data, commit=False)

        # Assert stuff
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_ERRORED)
        log_failure = JobLogEntry.objects.filter(
            grouping="initialization", log_level=LogLevelChoices.LOG_FAILURE
        ).first()
        self.assertIn("Data should be a dictionary", log_failure.message)


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
        self.user = User.objects.create_user(username="testuser")
        self.request.user = self.user

    def test_run_job_pass(self):
        """Test that file upload succeeds; job SUCCEEDS; and files are deleted."""
        module = "test_file_upload_pass"
        name = "TestFileUploadPass"
        job_class, job_model = get_job_class_and_model(module, name)

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
        job_class, job_model = get_job_class_and_model(module, name)

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
        job_result = create_job_result_and_run_job(module, name, data=serialized_data, commit=False)

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


class RunJobManagementCommandTest(CeleryTestCase):
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
        job_class, job_model = get_job_class_and_model(module, name)

        out, err = self.run_command(job_model.class_path)
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
        job_class, job_model = get_job_class_and_model(module, name)

        out, err = self.run_command(job_model.class_path)
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
        job_class, job_model = get_job_class_and_model(module, name)
        with self.assertRaises(CommandError):
            self.run_command("--commit", job_model.class_path)

    def test_runjob_db_change_commit_wrong_username(self):
        """A job that changes the DB, when run with commit=True and a nonexistent username, is rejected."""
        module = "test_modify_db"
        name = "TestModifyDB"
        job_class, job_model = get_job_class_and_model(module, name)
        with self.assertRaises(CommandError):
            self.run_command("--commit", "--username", "nosuchuser", job_model.class_path)

    def test_runjob_db_change_commit_and_username(self):
        """A job that changes the DB, when run with commit=True and a username, successfully updates the DB."""
        get_user_model().objects.create(username="test_user")

        module = "test_modify_db"
        name = "TestModifyDB"
        job_class, job_model = get_job_class_and_model(module, name)

        out, err = self.run_command("--commit", "--username", "test_user", job_model.class_path)
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


class JobSiteCustomFieldTest(CeleryTestCase):
    """Test a job that creates a site and a custom field."""

    databases = ("default", "job_logs")

    def setUp(self):
        super().setUp()
        user = User.objects.create(username="User1")

        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = user

    def test_run(self):
        self.clear_worker()

        module = "test_site_with_custom_field"
        name = "TestCreateSiteWithCustomField"
        job_result = create_job_result_and_run_job(module, name, request=self.request, commit=True)
        self.wait_on_active_tasks()
        job_result.refresh_from_db()

        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)

        # Test site with a value for custom_field
        site_1 = Site.objects.filter(slug="test-site-one")
        self.assertEqual(site_1.count(), 1)
        self.assertEqual(CustomField.objects.filter(name="cf1").count(), 1)
        self.assertEqual(site_1[0].cf["cf1"], "some-value")

        # Test site with default value for custom field
        site_2 = Site.objects.filter(slug="test-site-two")
        self.assertEqual(site_2.count(), 1)
        self.assertEqual(site_2[0].cf["cf1"], "-")
