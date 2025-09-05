from io import StringIO

from django.core.management import call_command
from django.utils.timezone import now
import yaml

from nautobot.core.management.commands.check_job_approval_status import ApprovalRequiredScheduledJobsError
from nautobot.core.testing import TestCase
from nautobot.extras.choices import JobExecutionType
from nautobot.extras.models import Job, ScheduledJob


class ManagementCommandTestCase(TestCase):
    """Test case for core management commands."""

    def setUp(self):
        """Initialize user and client."""
        super().setUpNautobot()
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

    def test_generate_performance_test_endpoints(self):
        """Test the generate_performance_test_endpoints management command."""
        out = StringIO()
        call_command("generate_performance_test_endpoints", stdout=out)
        endpoints_dict = yaml.safe_load(out.getvalue())["endpoints"]
        # status_code_to_endpoints = collections.defaultdict(list)
        for view_name, value in endpoints_dict.items():
            for endpoint in value:
                response = self.client.get(endpoint, follow=True)
                self.assertHttpStatus(
                    response, 200, f"{view_name}: {endpoint} returns status Code {response.status_code} instead of 200"
                )

    def test_check_job_approval_status_no_jobs(self):
        out = StringIO()
        # update all jobs to not have approval_required=True
        Job.objects.update(approval_required=False)
        call_command("check_job_approval_status", stdout=out)
        output = out.getvalue()
        self.assertIn("No approval_required jobs or scheduled jobs found.", output)

    def test_check_job_approval_status_with__with_approval_required_jobs(self):
        out = StringIO()
        self.assertTrue(Job.objects.filter(approval_required=True).exists())
        self.assertFalse(ScheduledJob.objects.filter(approval_required=True).exists())
        call_command("check_job_approval_status", stdout=out)
        output = out.getvalue()
        self.assertIn("Following jobs still have `approval_required=True`.", output)

    def test_check_job_approval_status_with_approval_required_scheduled_jobs(self):
        job = Job.objects.first()
        scheduled_job = ScheduledJob.objects.create(
            name="Scheduled Job",
            task="test_managment_command.TestManagmentCommand",
            job_model=job,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            approval_required=True,
            start_time=now(),
        )
        self.assertTrue(ScheduledJob.objects.filter(approval_required=True).exists())
        with self.assertRaises(ApprovalRequiredScheduledJobsError) as cm:
            call_command("check_job_approval_status")

        self.assertIn(
            "These need to be approved (and run) or denied before upgrading to Nautobot v3", str(cm.exception)
        )
        self.assertIn(scheduled_job.name, str(cm.exception))
