import os
import uuid

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

    def test_job_pass(self):
        """
        Job test with pass result.
        """
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):

            module = "test_pass"
            name = "TestPass"
            job_class = get_job(f"local/{module}/{name}")
            job_content_type = ContentType.objects.get(app_label="extras", model="job")

            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=job_content_type,
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
            job_content_type = ContentType.objects.get(app_label="extras", model="job")
            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=job_content_type,
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
            job_content_type = ContentType.objects.get(app_label="extras", model="job")

            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=job_content_type,
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
            job_content_type = ContentType.objects.get(app_label="extras", model="job")
            job_result = JobResult.objects.create(
                name=job_class.class_path,
                obj_type=job_content_type,
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


class JobFileUploadTest(TestCase):
    """Test a job that uploads/deletes files."""

    job_name = "plugins/dummy_plugin.jobs/FileUploadJob"

    @classmethod
    def setUpTestData(cls):
        cls.dummy_file = SimpleUploadedFile(name="dummy.txt", content=b"I am content.\n")
        cls.job_class = get_job(cls.job_name)

    def test_run_job_success(self):
        """Test that file upload succeeds, job succeeds, and are deleted."""
        assert False

    def test_run_job_success(self):
        """Test that file upload succeeds, job fails, files deleted."""
        assert False
