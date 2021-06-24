import os
import uuid

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.jobs import get_job, run_job
from nautobot.extras.models import JobResult
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

            run_job(data={}, request=None, commit=False, job_result=job_result)
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
            run_job(data={}, request=None, commit=False, job_result=job_result)
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
