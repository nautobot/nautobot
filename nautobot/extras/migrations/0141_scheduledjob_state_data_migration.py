from django.db import migrations

from nautobot.extras.choices import ApprovalWorkflowStateChoices, ScheduledJobStateChoices


def populate_state(apps, schema_editor):
    """
    Migrates existing ScheduledJob records to populate the new `state` field.

    State is derived from the combination of `enabled` and any associated
    ApprovalWorkflow state, because prior to this migration approval state was
    tracked implicitly via `approval_required` + `enabled` flags:

        enabled=True  + pending workflow  -> PENDING
                        (job awaiting approval, enabled stays True until decision)
        enabled=True  + no workflow       -> ACTIVE
        enabled=False + denied workflow   -> DENIED
        enabled=False + canceled workflow -> CANCELED
        enabled=False + no pending/denied/canceled workflow or no workflow -> COMPLETED
    """
    ScheduledJob = apps.get_model("extras", "ScheduledJob")
    ApprovalWorkflow = apps.get_model("extras", "ApprovalWorkflow")
    ContentType = apps.get_model("contenttypes", "ContentType")

    scheduled_job_ct = ContentType.objects.get(app_label="extras", model="scheduledjob")

    job_workflow_state = dict(
        ApprovalWorkflow.objects.filter(
            object_under_review_content_type=scheduled_job_ct,
            current_state__in=[
                ApprovalWorkflowStateChoices.PENDING,
                ApprovalWorkflowStateChoices.DENIED,
                ApprovalWorkflowStateChoices.CANCELED,
            ],
        ).values_list("object_under_review_object_id", "current_state")
    )

    to_update = []
    for scheduled_job in ScheduledJob.objects.only("pk", "enabled", "state"):
        workflow_state = job_workflow_state.get(scheduled_job.pk)

        if workflow_state == ApprovalWorkflowStateChoices.PENDING:
            new_state = ScheduledJobStateChoices.PENDING
        elif scheduled_job.enabled:
            new_state = ScheduledJobStateChoices.ACTIVE
        elif workflow_state == ApprovalWorkflowStateChoices.DENIED:
            new_state = ScheduledJobStateChoices.DENIED
        elif workflow_state == ApprovalWorkflowStateChoices.CANCELED:
            new_state = ScheduledJobStateChoices.CANCELED
        else:
            new_state = ScheduledJobStateChoices.COMPLETED

        if scheduled_job.state != new_state:
            scheduled_job.state = new_state
            to_update.append(scheduled_job)

    ScheduledJob.objects.bulk_update(to_update, ["state"], 1000)


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0140_scheduledjob_state"),
    ]

    operations = [
        migrations.RunPython(populate_state, migrations.RunPython.noop),
    ]
