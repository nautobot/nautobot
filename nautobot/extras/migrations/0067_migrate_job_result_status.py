from celery import states
from django.db import migrations

LEGACY_TO_NEW_JOB_RESULT_STATUS_MAPPING = [
    ["pending", states.PENDING],
    ["running", states.STARTED],
    ["completed", states.SUCCESS],
    ["errored", states.FAILURE],
    ["failed", states.FAILURE],
]


def update_status_choices(apps, schema_editor):
    JobResult = apps.get_model("extras", "JobResult")
    for old_status_name, new_status_name in LEGACY_TO_NEW_JOB_RESULT_STATUS_MAPPING:
        JobResult.objects.filter(status=old_status_name).update(status=new_status_name)


def revert_status_choices(apps, schema_editor):
    JobResult = apps.get_model("extras", "JobResult")
    for old_status_name, new_status_name in LEGACY_TO_NEW_JOB_RESULT_STATUS_MAPPING:
        JobResult.objects.filter(status=new_status_name).update(status=old_status_name)


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0066_rename_configcontext_role"),
    ]
    operations = [migrations.RunPython(update_status_choices, reverse_code=revert_status_choices)]
