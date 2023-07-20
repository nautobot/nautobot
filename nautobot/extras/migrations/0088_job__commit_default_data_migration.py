from django.db import migrations


def migrate_commit_default_to_dryrun_default(apps, schema_editor):
    """
    Negate the value of dryrun_default (True becomes False, False becomes True)
    """
    Job = apps.get_model("extras", "Job")
    for job_model in Job.objects.all():
        original = job_model.dryrun_default
        if isinstance(original, bool):
            job_model.dryrun_default = not original
            job_model.save()


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0087_job__celery_task_fields__dryrun_support"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_commit_default_to_dryrun_default,
            reverse_code=migrate_commit_default_to_dryrun_default,
        ),
    ]
