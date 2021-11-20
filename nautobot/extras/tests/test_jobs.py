import json
from io import StringIO
import os
from unittest import mock
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test.client import RequestFactory

from nautobot.dcim.models import DeviceRole, Site
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.jobs import get_job, run_job
from nautobot.extras.models import FileProxy, JobResult, Status
from nautobot.extras.models.models import JobLogEntry
from nautobot.utilities.testing import CeleryTestCase, TestCase


# Use the proper swappable User model
User = get_user_model()


# Override the job_db to None so that the Log Objects are created in the default database.
# This change is required as job_db is a `fake` database pointed at the default. The django
# database cleanup will fail and cause tests to fail as this is not a real database.
@mock.patch("nautobot.extras.models.models.job_db", None)
class JobTest(TestCase):
    """
    Test basic jobs to ensure importing works.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.job_content_type = ContentType.objects.get(app_label="extras", model="job")

    def setUp(self):
        super().setUp()
        self.user = User.objects.create(username="Super User", is_active=True, is_superuser=True)

        # Initialize fake request that will be required to execute Webhooks (in jobs.)
        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

    def test_job_pass(self):
        """
        Job test with pass result.
        """
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

            module = "test_pass"
            name = "TestPass"
            job_class = get_job(f"local/{module}/{name}")

            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=self.job_content_type,
                user=None,
                job_id=uuid.uuid4(),
            )

            run_job(data={}, request=None, commit=False, job_result_pk=job_result.pk)
            job_result.refresh_from_db()
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)

    def test_job_fail(self):
        """
        Job test with fail result.
        """
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

            module = "test_fail"
            name = "TestFail"
            job_class = get_job(f"local/{module}/{name}")
            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=self.job_content_type,
                user=None,
                job_id=uuid.uuid4(),
            )
            run_job(data={}, request=None, commit=False, job_result_pk=job_result.pk)
            job_result.refresh_from_db()
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_ERRORED)

    def test_field_order(self):
        """
        Job test with field order.
        """
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

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
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

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

    def test_ready_only_job_pass(self):
        """
        Job read only test with pass result.
        """
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

            module = "test_read_only_pass"
            name = "TestReadOnlyPass"
            job_class = get_job(f"local/{module}/{name}")

            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=self.job_content_type,
                user=None,
                job_id=uuid.uuid4(),
            )

            run_job(data={}, request=None, commit=False, job_result_pk=job_result.pk)
            job_result.refresh_from_db()
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)
            self.assertEqual(Site.objects.count(), 0)  # Ensure DB transaction was aborted

    def test_read_only_job_fail(self):
        """
        Job read only test with fail result.
        """
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

            module = "test_read_only_fail"
            name = "TestReadOnlyFail"
            job_class = get_job(f"local/{module}/{name}")
            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=self.job_content_type,
                user=None,
                job_id=uuid.uuid4(),
            )
            run_job(data={}, request=None, commit=False, job_result_pk=job_result.pk)
            job_result.refresh_from_db()
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_ERRORED)
            self.assertEqual(Site.objects.count(), 0)  # Ensure DB transaction was aborted

    def test_read_only_no_commit_field(self):
        """
        Job read only test commit field is not shown.
        """
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

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
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

            module = "test_ipaddress_vars"
            name = "TestIPAddresses"
            job_class = get_job(f"local/{module}/{name}")

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
            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=self.job_content_type,
                user=None,
                job_id=uuid.uuid4(),
            )
            data = job_class.serialize_data(form.cleaned_data)

            # Run the job and extract the job payload data
            # Changing commit=True as commit=False will rollback database changes including the
            # logs that we are trying to read. See above note on why we are using the default database.
            # Also need to pass a mock request object as execute_webhooks will be called with the creation
            # of the objects.
            run_job(data=data, request=self.request, commit=True, job_result_pk=job_result.pk)
            job_result.refresh_from_db()

            log_info = JobLogEntry.objects.filter(
                job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
            ).first()

            job_result_data = json.loads(log_info.log_object)

            # Assert stuff
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)
            self.assertEqual(form_data, job_result_data)

    def test_object_vars(self):
        """
        Test that Object variable fields behave as expected.
        """
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

            module = "test_object_vars"
            name = "TestObjectVars"
            job_class = get_job(f"local/{module}/{name}")

            d = DeviceRole.objects.create(name="role", slug="role")

            # Prepare the job data
            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=self.job_content_type,
                user=None,
                job_id=uuid.uuid4(),
            )
            data = {
                "role": {"name": "role"},
                "roles": [d.pk],
            }

            # Run the job and extract the job payload data
            # See test_ip_address_vars as to why we are changing commit=True and request=self.request.
            run_job(data=data, request=self.request, commit=True, job_result_pk=job_result.pk)
            job_result.refresh_from_db()
            # Test storing additional data in job
            job_result_data = job_result.data["object_vars"]

            info_log = JobLogEntry.objects.filter(
                job_result=job_result, log_level=LogLevelChoices.LOG_INFO, grouping="run"
            ).first()

            # Assert stuff
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)
            self.assertEqual({"role": str(d.pk), "roles": [str(d.pk)]}, job_result_data)
            self.assertEqual(info_log.log_object, "Role: role")
            self.assertEqual(job_result.data["output"], "\nNice Roles, bro.")

    def test_job_data_as_string(self):
        """
        Test that job doesn't error when not a dictionary.
        """
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):
            module = "test_object_vars"
            name = "TestObjectVars"
            job_class = get_job(f"local/{module}/{name}")

            # Prepare the job data
            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=self.job_content_type,
                user=None,
                job_id=uuid.uuid4(),
            )
            data = "BAD DATA STRING"
            run_job(data=data, request=None, commit=False, job_result_pk=job_result.pk)
            job_result.refresh_from_db()

            # Assert stuff
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_ERRORED)
            self.assertIn(
                "Data should be a dictionary",
                next(
                    log[-1]  # actual log message in the logging tuple
                    for log in job_result.data["initialization"]["log"]
                ),
            )


@mock.patch("nautobot.extras.models.models.job_db", None)
class JobFileUploadTest(TestCase):
    """Test a job that uploads/deletes files."""

    @classmethod
    def setUpTestData(cls):
        cls.file_contents = b"I am content.\n"
        cls.dummy_file = SimpleUploadedFile(name="dummy.txt", content=cls.file_contents)
        cls.job_content_type = ContentType.objects.get(app_label="extras", model="job")

    def setUp(self):
        self.dummy_file.seek(0)  # Reset cursor so we can read it again.
        self.user = User.objects.create(username="Super User", is_active=True, is_superuser=True)

        # Initialize fake request that will be required to execute Webhooks (in jobs.)
        self.request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        self.request.id = uuid.uuid4()
        self.request.user = self.user

    def test_run_job_pass(self):
        """Test that file upload succeeds; job SUCCEEDS; and files are deleted."""
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):
            job_name = "local/test_file_upload_pass/TestFileUploadPass"
            job_class = get_job(job_name)

            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=self.job_content_type,
                user=None,
                job_id=uuid.uuid4(),
            )

            # Serialize the file to FileProxy
            data = {"file": self.dummy_file}
            form = job_class().as_form(files=data)
            self.assertTrue(form.is_valid())
            serialized_data = job_class.serialize_data(form.cleaned_data)

            # Assert that the file was serialized to a FileProxy
            self.assertTrue(isinstance(serialized_data["file"], uuid.UUID))
            self.assertEqual(serialized_data["file"], FileProxy.objects.latest().pk)
            self.assertEqual(FileProxy.objects.count(), 1)

            # Run the job
            # See test_ip_address_vars as to why we are changing commit=True and request=self.request.
            run_job(data=serialized_data, request=self.request, commit=True, job_result_pk=job_result.pk)
            job_result.refresh_from_db()

            warning_log = JobLogEntry.objects.filter(
                job_result=job_result, log_level=LogLevelChoices.LOG_WARNING, grouping="run"
            ).first()

            # Assert that file contents were correctly read
            self.assertEqual(warning_log.message, f"File contents: {self.file_contents}")  # "File contents: ..."

            # Assert that FileProxy was cleaned up
            self.assertEqual(FileProxy.objects.count(), 0)

    def test_run_job_fail(self):
        """Test that file upload succeeds; job FAILS; files deleted."""
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):
            job_name = "local/test_file_upload_fail/TestFileUploadFail"
            job_class = get_job(job_name)

            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=self.job_content_type,
                user=None,
                job_id=uuid.uuid4(),
            )

            # Serialize the file to FileProxy
            data = {"file": self.dummy_file}
            form = job_class().as_form(files=data)
            self.assertTrue(form.is_valid())
            serialized_data = job_class.serialize_data(form.cleaned_data)

            # Assert that the file was serialized to a FileProxy
            self.assertTrue(isinstance(serialized_data["file"], uuid.UUID))
            self.assertEqual(serialized_data["file"], FileProxy.objects.latest().pk)
            self.assertEqual(FileProxy.objects.count(), 1)

            # Run the job
            run_job(data=serialized_data, request=None, commit=False, job_result_pk=job_result.pk)
            job_result.refresh_from_db()

            # Can't check log objects when jobs are reverted (within tests anyways.)
            # This is due to the fake job_logs db not being available for tests.

            # Assert that FileProxy was cleaned up
            self.assertEqual(FileProxy.objects.count(), 0)


@mock.patch("nautobot.extras.models.models.job_db", None)
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
        # I had to change this test, unfortunately with no commit, the logs revert since we can't
        # use the fake job_logs db here.
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):
            out, err = self.run_command("local/test_pass/TestPass")
            self.assertIn("Running local/test_pass/TestPass...", out)
            self.assertIn("test_pass: 0 success, 1 info, 0 warning, 0 failure", out)
            self.assertIn("info: Database changes have been reverted automatically.", out)
            self.assertIn("local/test_pass/TestPass: SUCCESS", out)
            self.assertEqual("", err)

    def test_runjob_db_change_no_commit(self):
        """A job that changes the DB, when run with commit=False, doesn't modify the database."""
        with self.assertRaises(ObjectDoesNotExist):
            Status.objects.get(slug="test-status")

        # I had to change this test, unfortunately with no commit, the logs revert since we can't
        # use the fake job_logs db here.
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):
            out, err = self.run_command("local/test_modify_db/TestModifyDB")
            self.assertIn("Running local/test_modify_db/TestModifyDB...", out)
            self.assertIn("test_modify_db: 0 success, 1 info, 0 warning, 0 failure", out)
            self.assertIn("info: Database changes have been reverted automatically.", out)
            self.assertIn("local/test_modify_db/TestModifyDB: SUCCESS", out)
            self.assertEqual("", err)

        with self.assertRaises(ObjectDoesNotExist):
            Status.objects.get(slug="test-status")

    def test_runjob_db_change_commit_no_username(self):
        """A job that changes the DB, when run with commit=True but no username, is rejected."""
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):
            with self.assertRaises(CommandError):
                self.run_command("--commit", "local/test_modify_db/TestModifyDB")

    def test_runjob_db_change_commit_wrong_username(self):
        """A job that changes the DB, when run with commit=True and a nonexistent username, is rejected."""
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):
            with self.assertRaises(CommandError):
                self.run_command("--commit", "--username", "nosuchuser", "local/test_modify_db/TestModifyDB")

    def test_runjob_db_change_commit_and_username(self):
        """A job that chagnes the DB, when run with commit=True and a username, successfully updates the DB."""
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):
            get_user_model().objects.create(username="dummy_user")

            out, err = self.run_command("--commit", "--username", "dummy_user", "local/test_modify_db/TestModifyDB")
            self.assertIn("Running local/test_modify_db/TestModifyDB...", out)
            # Changed job to actually log data. Can't display empty results if no logs were created.
            self.assertIn("test_modify_db: 1 success, 0 info, 0 warning, 0 failure", out)
            self.assertIn("local/test_modify_db/TestModifyDB: SUCCESS", out)
            self.assertEqual("", err)

        success_log = JobLogEntry.objects.filter(log_level=LogLevelChoices.LOG_SUCCESS).first()
        self.assertEqual(success_log.message, "Status created successfully.")

        status = Status.objects.get(slug="test-status")
        self.assertEqual(status.name, "Test Status")

        status.delete()
