"""
Migration pre-check for deprecating the `approval_required` flag on Job.

This migration performs the following checks before proceeding:
1. Aborts the migration if any ScheduledJob still has `approval_required=True`,
   because the task approval queue must be cleared before the flag can be removed.
2. Allows the migration to continue if any Job has `approval_required=True`,
   but prints a warning to inform that this behavior is deprecated.
   Users should define an approval workflow definition for such jobs going forward.

Refer to documentation for migration to the new approval workflow system:
https://docs.nautobot.com/projects/core/en/next/user-guide/platform-functionality/approval-workflow/
"""

from django.db import migrations

from nautobot.extras.exceptions import ApprovalRequiredScheduledJobsError


def _reverse_migrate_data(*_):
    pass


def _migrate_data(apps, *_):
    ScheduledJob = apps.get_model("extras", "ScheduledJob")
    approval_required_scheduled_jobs = ScheduledJob.objects.filter(approval_required=True).values_list("id", "name")

    if approval_required_scheduled_jobs:
        message_lines = [
            "Migration aborted: There are scheduled jobs that still require approval.",
            "Please clear the job approval queue prior to the upgrade.",
            "Below list of effected scheduled jobs:",
        ]
        for schedule_job_id, scheduled_job_name in approval_required_scheduled_jobs:
            message_lines.append(f"    - ID: {schedule_job_id}, Name: {scheduled_job_name}")
        raise ApprovalRequiredScheduledJobsError("\n".join(message_lines))

    Job = apps.get_model("extras", "Job")
    approval_required_jobs = Job.objects.filter(approval_required=True).values_list("name")
    if approval_required_jobs:
        message_lines = [
            "Migration passed, but the following jobs still have `approval_required=True`.",
            "These jobs will no longer trigger approval automatically.",
            "After upgrading to Nautobot 3.x, you should add an approval workflow definition(s) covering these jobs.",
            "Refer to the documentation: https://docs.nautobot.com/projects/core/en/next/user-guide/platform-functionality/approval-workflow/",
            "Affected jobs (Names):",
        ]
        for job_name in approval_required_jobs:
            message_lines.append(f"    - {job_name}")
        print("\n".join(message_lines))
    else:
        print("Migration passed: No approval_required jobs or scheduled jobs found.")


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0124_approval_workflow_models"),
    ]

    operations = [
        migrations.RunPython(code=_migrate_data, reverse_code=_reverse_migrate_data),
    ]
