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
