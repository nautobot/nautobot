"""Tests for the Job Kill Switch feature."""

from django.test import TestCase
from django.utils import timezone

from nautobot.extras.choices import (
    JobResultStatusChoices,
    KillRequestStatusChoices,
)
from nautobot.extras.models import JobKillRequest, JobResult


class JobKillRequestModelTest(TestCase):
    """Test the JobKillRequest model."""

    def test_create_kill_request(self):
        jr = JobResult.objects.create(name="Test", status=JobResultStatusChoices.STATUS_STARTED)
        kr = JobKillRequest.objects.create(
            job_result=jr,
            status=KillRequestStatusChoices.STATUS_PENDING,
        )
        self.assertEqual(kr.job_result, jr)
        self.assertIsNone(kr.acknowledged_at)

    def test_one_to_one_constraint(self):
        jr = JobResult.objects.create(name="Test", status=JobResultStatusChoices.STATUS_STARTED)
        JobKillRequest.objects.create(job_result=jr, status=KillRequestStatusChoices.STATUS_PENDING)
        with self.assertRaises(Exception):
            JobKillRequest.objects.create(job_result=jr, status=KillRequestStatusChoices.STATUS_PENDING)

    def test_cascade_delete(self):
        jr = JobResult.objects.create(name="Test", status=JobResultStatusChoices.STATUS_STARTED)
        JobKillRequest.objects.create(job_result=jr, status=KillRequestStatusChoices.STATUS_PENDING)
        jr.delete()
        self.assertEqual(JobKillRequest.objects.count(), 0)
