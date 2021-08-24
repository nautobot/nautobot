import json
import os
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Site
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.jobs import get_job, run_job
from nautobot.extras.models import FileAttachment, FileProxy, JobResult
from nautobot.utilities.testing import TestCase


class JobTest(TestCase):
    """
    Test basic jobs to ensure importing works.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.job_content_type = ContentType.objects.get(app_label="extras", model="job")

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
                """<tr><th><label for="id_var2">Var2:</label></th><td>
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
            # Also ensure the standard log message about aborting the transaction is *not* present
            self.assertNotEqual(
                job_result.data["run"]["log"][-1][-1], "Database changes have been reverted due to error."
            )

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
            run_job(data=data, request=None, commit=False, job_result_pk=job_result.pk)
            job_result.refresh_from_db()
            job_payload = job_result.data["run"]["log"][0][2]  # Indexing makes me sad.
            job_result_data = json.loads(job_payload)

            # Assert stuff
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)
            self.assertEqual(form_data, job_result_data)


class JobFileUploadTest(TestCase):
    """Test a job that uploads/deletes files."""

    @classmethod
    def setUpTestData(cls):
        cls.file_contents = b"I am content.\n"
        cls.dummy_file = SimpleUploadedFile(name="dummy.txt", content=cls.file_contents)
        cls.job_content_type = ContentType.objects.get(app_label="extras", model="job")

    def setUp(self):
        self.dummy_file.seek(0)  # Reset cursor so we can read it again.

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
            run_job(data=serialized_data, request=None, commit=False, job_result_pk=job_result.pk)
            job_result.refresh_from_db()

            # Assert that file contents were correctly read
            self.assertEqual(
                job_result.data["run"]["log"][0][2], f"File contents: {self.file_contents}"  # "File contents: ..."
            )

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

            # Assert that file contents were correctly read
            self.assertEqual(
                job_result.data["run"]["log"][0][2], f"File contents: {self.file_contents}"  # "File contents: ..."
            )
            # Also ensure the standard log message about aborting the transaction is present
            self.assertEqual(job_result.data["run"]["log"][-1][-1], "Database changes have been reverted due to error.")

            # Assert that FileProxy was cleaned up
            self.assertEqual(FileProxy.objects.count(), 0)
