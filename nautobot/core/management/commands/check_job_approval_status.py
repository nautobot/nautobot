from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from nautobot.extras.models import Job, ScheduledJob


class ApprovalRequiredScheduledJobsError(ValidationError):
    """Raised when scheduled jobs requiring approval are found during managment command."""


class Command(BaseCommand):
    help = "Checks for scheduled jobs and jobs that require approval."

    def handle(self, *args, **options):
        approval_required_scheduled_jobs = ScheduledJob.objects.filter(approval_required=True).values_list("id", "name")

        if approval_required_scheduled_jobs:
            message_lines = [
                "There are scheduled jobs that still require approval.",
                "Please clear, approve or deny the job in approval queue.",
                "Below is a list of affected scheduled jobs:",
            ]
            for schedule_job_id, scheduled_job_name in approval_required_scheduled_jobs:
                message_lines.append(f"    - ID: {schedule_job_id}, Name: {scheduled_job_name}")
            raise ApprovalRequiredScheduledJobsError("\n".join(message_lines))

        approval_required_jobs = Job.objects.filter(approval_required=True).values_list("name", flat=True)
        if approval_required_jobs:
            message_lines = [
                "Following jobs still have `approval_required=True`.",
                "These jobs will no longer trigger approval automatically.",
                "After upgrading to Nautobot 3.x, you should add an approval workflow definition(s) covering these jobs.",
                "Refer to the documentation: https://docs.nautobot.com/projects/core/en/next/user-guide/platform-functionality/approval-workflow/",
                "Affected jobs (Names):",
            ]
            for job_name in approval_required_jobs:
                message_lines.append(f"    - {job_name}")
        else:
            message_lines = ["No approval_required jobs or scheduled jobs found."]
        self.stdout.write("\n".join(message_lines))
