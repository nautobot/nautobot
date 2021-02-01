import time
import os
import uuid

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import request
from django.utils import timezone

from extras.choices import JobResultStatusChoices
from extras.custom_jobs import get_custom_job, run_custom_job
from extras.models import JobResult
from utilities.testing import TestCase


class CustomJobTest(TestCase):
    """
    Test basic custom scripts to ensure importing works.
    """
    def test_customjob_pass(self):
        """
        Custom script test with pass result.
        """
        with self.settings(CUSTOM_JOBS_ROOT=os.path.join(settings.BASE_DIR, 'extras/tests/dummy_customjobs')):

            module = "test_pass"
            name = "TestPass"
            custom_job_class = get_custom_job(f"local/{module}/{name}")
            custom_job_content_type = ContentType.objects.get(app_label='extras', model='customjob')

            job_result = JobResult.objects.create(
                name=custom_job_class.class_path,
                obj_type=custom_job_content_type,
                user=None,
                job_id=uuid.uuid4()
            )

            run_custom_job(
                data={},
                request=None,
                commit=False,
                job_result=job_result
            )
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_COMPLETED)

    def test_custom_fail(self):
        """
        Custom script test with fail result.
        """
        with self.settings(CUSTOM_JOBS_ROOT=os.path.join(settings.BASE_DIR, 'extras/tests/dummy_customjobs')):

            module = "test_fail"
            name = "TestFail"
            custom_job_class = get_custom_job(f"local/{module}/{name}")
            custom_job_content_type = ContentType.objects.get(app_label='extras', model='customjob')
            job_result = JobResult.objects.create(
                name=custom_job_class.class_path,
                obj_type=custom_job_content_type,
                user=None,
                job_id=uuid.uuid4()
            )
            run_custom_job(
                data={},
                request=None,
                commit=False,
                job_result=job_result
            )
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_ERRORED)
