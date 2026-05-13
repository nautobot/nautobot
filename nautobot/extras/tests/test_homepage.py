from datetime import timedelta

from django.test import RequestFactory
from django.utils.timezone import now

from nautobot.core.testing import TestCase
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.homepage import get_job_results
from nautobot.extras.models import JobResult


class GetJobResultsTestCase(TestCase):
    """Tests for the home page Job History panel callback."""

    def setUp(self):
        super().setUp()
        # Parent setUp creates self.user as a non-superuser; elevate it so .restrict() returns all rows.
        self.user.is_superuser = True
        self.user.save()
        self.factory = RequestFactory()

    def _build_request(self):
        request = self.factory.get("/")
        request.user = self.user
        return request

    def test_orders_null_date_done_by_date_created(self):
        """A FAILURE result with NULL date_done must not float above a more recently completed SUCCESS."""
        timestamp = now()

        old_failure = JobResult.objects.create(
            name="old failure",
            status=JobResultStatusChoices.STATUS_FAILURE,
        )
        # auto_now_add ignores manual assignment; override via queryset.update.
        JobResult.objects.filter(pk=old_failure.pk).update(
            date_done=None,
            date_created=timestamp - timedelta(days=30),
        )

        new_success = JobResult.objects.create(
            name="new success",
            status=JobResultStatusChoices.STATUS_SUCCESS,
            date_done=timestamp,
        )

        result_pks = [jr.pk for jr in get_job_results(self._build_request())]

        self.assertIn(new_success.pk, result_pks)
        self.assertIn(old_failure.pk, result_pks)
        self.assertLess(result_pks.index(new_success.pk), result_pks.index(old_failure.pk))
