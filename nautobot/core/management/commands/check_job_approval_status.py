from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from nautobot.extras.models import Job, ScheduledJob


class ApprovalRequiredScheduledJobsError(ValidationError):
    """Raised when scheduled jobs requiring approval are found during managment command."""

    def __init__(self, message_lines):
        self.message_lines = message_lines
        super().__init__(message_lines)

    def __str__(self):
        return "\n".join(self.message_lines)


class Command(BaseCommand):
    help = "Checks for scheduled jobs and jobs that require approval."

    def handle(self, *args, **options):
        approval_required_scheduled_jobs = ScheduledJob.objects.filter(approval_required=True).values_list("id", "name")

        if approval_required_scheduled_jobs:
            message_lines = [
                "These need to be approved (and run) or denied before upgrading to Nautobot v3, as the introduction of the approval workflows feature means that future scheduled-job approvals will be handled differently.",
                "Refer to the documentation: https://docs.nautobot.com/projects/core/en/v2.4.14/user-guide/platform-functionality/jobs/job-scheduling-and-approvals/#approval-via-the-ui",
                "Below is a list of affected scheduled jobs:",
            ]
            for schedule_job_id, scheduled_job_name in approval_required_scheduled_jobs:
                message_lines.append(f"    - ID: {schedule_job_id}, Name: {scheduled_job_name}")
            raise ApprovalRequiredScheduledJobsError(message_lines)

        approval_required_jobs = Job.objects.filter(approval_required=True).values_list("name", flat=True)
        if approval_required_jobs:
            message_lines = [
                "Following jobs still have `approval_required=True`.",
                "These jobs will no longer trigger approval automatically.",
                "After upgrading to Nautobot 3.x, you should add an approval workflow definition(s) covering these jobs.",
                "Refer to the documentation: https://docs.nautobot.com/projects/core/en/v3.0.0/user-guide/platform-functionality/approval-workflow/",
                "Affected jobs (Names):",
            ]
            for job_name in approval_required_jobs:
                message_lines.append(f"    - {job_name}")
        else:
            message_lines = ["No approval_required jobs or scheduled jobs found."]
        self.stdout.write("\n".join(message_lines))
