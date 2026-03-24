"""Tests for the Job Kill Switch feature."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from nautobot.core.testing import APITestCase, TestCase as NautobotTestCase
from nautobot.extras.choices import (
    JobResultStatusChoices,
    KillRequestStatusChoices,
    KillTypeChoices,
)
from nautobot.extras.kill import reap_dead_jobs, terminate_job
from nautobot.extras.models import JobKillRequest, JobResult


class JobResultIsKillableTest(TestCase):
    """Test the is_killable property."""

    def test_pending_is_killable(self):
        jr = JobResult(status=JobResultStatusChoices.STATUS_PENDING)
        self.assertTrue(jr.is_killable)

    def test_started_is_killable(self):
        jr = JobResult(status=JobResultStatusChoices.STATUS_STARTED)
        self.assertTrue(jr.is_killable)

    def test_success_not_killable(self):
        jr = JobResult(status=JobResultStatusChoices.STATUS_SUCCESS)
        self.assertFalse(jr.is_killable)

    def test_failure_not_killable(self):
        jr = JobResult(status=JobResultStatusChoices.STATUS_FAILURE)
        self.assertFalse(jr.is_killable)

    def test_revoked_not_killable(self):
        jr = JobResult(status=JobResultStatusChoices.STATUS_REVOKED)
        self.assertFalse(jr.is_killable)


class TerminateJobTest(TestCase):
    """Test the terminate_job service function."""

    def setUp(self):
        self.job_result = JobResult.objects.create(
            name="Test Running Job",
            status=JobResultStatusChoices.STATUS_STARTED,
            celery_kwargs={"queue": "default"},
        )

    @mock.patch("nautobot.core.celery.app")
    def test_terminate_success(self, mock_app):
        """Successful termination creates a kill request and marks job as REVOKED."""
        result = terminate_job(self.job_result, user=None)

        self.assertIn("kill_request", result)
        self.assertNotIn("error", result)

        kill_request = result["kill_request"]
        self.assertEqual(kill_request.status, KillRequestStatusChoices.STATUS_ACKNOWLEDGED)
        self.assertIsNotNone(kill_request.acknowledged_at)

        self.job_result.refresh_from_db()
        self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_REVOKED)
        self.assertEqual(self.job_result.kill_type, KillTypeChoices.TERMINATE)
        self.assertIsNotNone(self.job_result.killed_at)
        self.assertIsNotNone(self.job_result.date_done)

        mock_app.control.revoke.assert_called_once_with(str(self.job_result.pk), terminate=True, signal="SIGKILL")

    @mock.patch("nautobot.core.celery.app")
    def test_terminate_revoke_failure(self, mock_app):
        """If revoke raises, kill request is marked as failed and job status is unchanged."""
        mock_app.control.revoke.side_effect = Exception("Broker unreachable")

        result = terminate_job(self.job_result, user=None)

        self.assertIn("error", result)
        self.assertIn("Broker unreachable", result["error"])

        kill_request = JobKillRequest.objects.get(job_result=self.job_result)
        self.assertEqual(kill_request.status, KillRequestStatusChoices.STATUS_FAILED)
        self.assertIn("Broker unreachable", kill_request.error_detail)

        self.job_result.refresh_from_db()
        self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_STARTED)

    @mock.patch("nautobot.core.celery.app")
    def test_terminate_retry_after_failure(self, mock_app):
        """A failed kill request can be retried — the existing record is updated in place."""
        mock_app.control.revoke.side_effect = Exception("Broker unreachable")
        terminate_job(self.job_result, user=None)

        kill_request = JobKillRequest.objects.get(job_result=self.job_result)
        self.assertEqual(kill_request.status, KillRequestStatusChoices.STATUS_FAILED)
        original_pk = kill_request.pk

        mock_app.control.revoke.side_effect = None
        result = terminate_job(self.job_result, user=None)

        self.assertIn("kill_request", result)
        kill_request = result["kill_request"]
        self.assertEqual(kill_request.pk, original_pk)
        self.assertEqual(kill_request.status, KillRequestStatusChoices.STATUS_ACKNOWLEDGED)
        self.assertIsNone(kill_request.error_detail)

    @mock.patch("nautobot.core.celery.app")
    def test_terminate_sets_reap_type(self, mock_app):
        """Termination with reap kill type sets correct kill_type."""
        terminate_job(self.job_result, user=None, reason=KillTypeChoices.REAP)

        self.job_result.refresh_from_db()
        self.assertIsNone(self.job_result.killed_by)
        self.assertEqual(self.job_result.kill_type, KillTypeChoices.REAP)


class ReapDeadJobsTest(TestCase):
    """Test the reap_dead_jobs service function."""

    def setUp(self):
        self.running_job = JobResult.objects.create(
            name="Running Job",
            status=JobResultStatusChoices.STATUS_STARTED,
            celery_kwargs={"queue": "default"},
        )
        self.pending_job = JobResult.objects.create(
            name="Pending Job",
            status=JobResultStatusChoices.STATUS_PENDING,
            celery_kwargs={"queue": "default"},
        )
        self.completed_job = JobResult.objects.create(
            name="Completed Job",
            status=JobResultStatusChoices.STATUS_SUCCESS,
        )

    @mock.patch("nautobot.extras.kill._get_active_celery_task_ids")
    def test_reap_dead_job(self, mock_active):
        """A job with no active worker is reaped."""
        mock_active.return_value = set()

        result = reap_dead_jobs()

        self.assertEqual(result["cancelled"], 2)
        self.assertEqual(result["skipped"], 0)

        self.running_job.refresh_from_db()
        self.assertEqual(self.running_job.status, JobResultStatusChoices.STATUS_REVOKED)
        self.assertEqual(self.running_job.kill_type, KillTypeChoices.REAP)

    @mock.patch("nautobot.extras.kill._get_active_celery_task_ids")
    def test_reap_skips_active_job(self, mock_active):
        """A job with an active worker is not reaped."""
        mock_active.return_value = {str(self.running_job.pk)}

        result = reap_dead_jobs()

        self.assertEqual(result["cancelled"], 1)
        self.assertEqual(result["skipped"], 1)

        self.running_job.refresh_from_db()
        self.assertEqual(self.running_job.status, JobResultStatusChoices.STATUS_STARTED)

    @mock.patch("nautobot.extras.kill._get_active_celery_task_ids")
    def test_reap_skips_all_when_inspection_fails(self, mock_active):
        """If Celery inspection fails, no jobs are reaped."""
        mock_active.return_value = None

        result = reap_dead_jobs()

        self.assertEqual(result["cancelled"], 0)
        self.assertEqual(result["skipped"], 2)
        self.assertEqual(len(result["errors"]), 1)

    @mock.patch("nautobot.extras.kill._get_active_celery_task_ids")
    def test_reap_with_queryset(self, mock_active):
        """Reap can be scoped to a specific queryset."""
        mock_active.return_value = set()

        result = reap_dead_jobs(queryset=JobResult.objects.filter(pk=self.running_job.pk))

        self.assertEqual(result["cancelled"], 1)

        self.pending_job.refresh_from_db()
        self.assertEqual(self.pending_job.status, JobResultStatusChoices.STATUS_PENDING)

    @mock.patch("nautobot.extras.kill._get_active_celery_task_ids")
    def test_reap_idempotent(self, mock_active):
        """Running reap twice doesn't fail or change already-reaped jobs."""
        mock_active.return_value = set()

        reap_dead_jobs()
        result = reap_dead_jobs()

        self.assertEqual(result["cancelled"], 0)
        self.assertEqual(result["skipped"], 0)


class TerminateAPIEndpointTest(APITestCase):
    """Test the POST /api/extras/job-results/{id}/terminate/ endpoint."""

    model = JobResult

    def setUp(self):
        super().setUp()
        self.job_result = JobResult.objects.create(
            name="API Test Job",
            status=JobResultStatusChoices.STATUS_STARTED,
            celery_kwargs={"queue": "default"},
        )

    @mock.patch("nautobot.core.celery.app")
    def test_terminate_returns_202(self, mock_app):
        self.user.is_superuser = True
        self.user.save()
        url = reverse("extras-api:jobresult-terminate", kwargs={"pk": self.job_result.pk})
        response = self.client.post(url, format="json", **self.header)
        self.assertEqual(response.status_code, 202)

    def test_terminate_completed_job_returns_200(self):
        self.user.is_superuser = True
        self.user.save()
        self.job_result.status = JobResultStatusChoices.STATUS_SUCCESS
        self.job_result.save()
        url = reverse("extras-api:jobresult-terminate", kwargs={"pk": self.job_result.pk})
        response = self.client.post(url, format="json", **self.header)
        self.assertEqual(response.status_code, 200)

    def test_terminate_without_permission_returns_403(self):
        """Users without extras.change_jobresult cannot terminate jobs."""
        self.user.is_superuser = False
        self.user.save()
        url = reverse("extras-api:jobresult-terminate", kwargs={"pk": self.job_result.pk})
        response = self.client.post(url, format="json", **self.header)
        self.assertEqual(response.status_code, 403)


class TerminateUIViewTest(NautobotTestCase):
    """Test the UI terminate action."""

    def setUp(self):
        super().setUp()
        self.add_permissions("extras.view_jobresult", "extras.change_jobresult")
        self.job_result = JobResult.objects.create(
            name="UI Test Job",
            status=JobResultStatusChoices.STATUS_STARTED,
            celery_kwargs={"queue": "default"},
        )

    @mock.patch("nautobot.core.celery.app")
    def test_terminate_redirects(self, mock_app):
        url = reverse("extras:jobresult_terminate", kwargs={"pk": self.job_result.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

    @mock.patch("nautobot.core.celery.app")
    def test_terminate_marks_job_revoked(self, mock_app):
        url = reverse("extras:jobresult_terminate", kwargs={"pk": self.job_result.pk})
        self.client.post(url)
        self.job_result.refresh_from_db()
        self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_REVOKED)

    def test_terminate_completed_job_is_noop(self):
        self.job_result.status = JobResultStatusChoices.STATUS_SUCCESS
        self.job_result.save()
        url = reverse("extras:jobresult_terminate", kwargs={"pk": self.job_result.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)


class ReapUIViewTest(NautobotTestCase):
    """Test the UI reap action."""

    def setUp(self):
        super().setUp()
        self.add_permissions("extras.view_jobresult", "extras.change_jobresult")
        self.job_result = JobResult.objects.create(
            name="Reap Test Job",
            status=JobResultStatusChoices.STATUS_STARTED,
            celery_kwargs={"queue": "default"},
        )

    @mock.patch("nautobot.extras.kill._get_active_celery_task_ids")
    def test_reap_dead_job(self, mock_active):
        mock_active.return_value = set()
        url = reverse("extras:jobresult_reap", kwargs={"pk": self.job_result.pk})
        self.client.post(url)
        self.job_result.refresh_from_db()
        self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_REVOKED)
        self.assertEqual(self.job_result.kill_type, KillTypeChoices.REAP)

    @mock.patch("nautobot.extras.kill._get_active_celery_task_ids")
    def test_reap_active_job_skipped(self, mock_active):
        mock_active.return_value = {str(self.job_result.pk)}
        url = reverse("extras:jobresult_reap", kwargs={"pk": self.job_result.pk})
        self.client.post(url)
        self.job_result.refresh_from_db()
        self.assertEqual(self.job_result.status, JobResultStatusChoices.STATUS_STARTED)


class JobKillRequestModelTest(TestCase):
    """Test the JobKillRequest model."""

    def test_create_kill_request(self):
        jr = JobResult.objects.create(name="Test", status=JobResultStatusChoices.STATUS_STARTED)
        kr = JobKillRequest.objects.create(
            job_result=jr,
            status=KillRequestStatusChoices.STATUS_PENDING,
        )
        self.assertEqual(kr.job_result, jr)
        self.assertTrue(kr.is_pending)
        self.assertIsNone(kr.acknowledged_at)

    def test_is_pending_property(self):
        jr = JobResult.objects.create(name="Test", status=JobResultStatusChoices.STATUS_STARTED)
        kr = JobKillRequest.objects.create(
            job_result=jr,
            status=KillRequestStatusChoices.STATUS_ACKNOWLEDGED,
            acknowledged_at=timezone.now(),
        )
        self.assertFalse(kr.is_pending)

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


class WorkerStatusViewTest(NautobotTestCase):
    """Test the Worker Status view."""

    def setUp(self):
        super().setUp()
        self.add_permissions("extras.view_jobresult")

    def test_worker_status_view_returns_200(self):
        url = reverse("worker_status")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
