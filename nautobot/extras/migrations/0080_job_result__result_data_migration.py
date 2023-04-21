from django.db import migrations


def migrate_data_to_result(apps, schema_editor):
    """
    Migrate the JobResult `data` field to `result`
    """
    JobResult = apps.get_model("extras", "Job")
    for job_result in JobResult.objects.all():
        if job_result.data is not None and job_result.result is None:
            job_result.result = job_result.data
            job_result.data = None
            job_result.save()


def migrate_result_to_data(apps, schema_editor):
    """
    Migrate the JobResult `result` field to `data`
    """
    JobResult = apps.get_model("extras", "Job")
    for job_result in JobResult.objects.all():
        if job_result.result is not None and job_result.data is None:
            job_result.data = job_result.result
            job_result.result = None
            job_result.save()


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0079_job__commit_default_data_migration"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_data_to_result,
            reverse_code=migrate_result_to_data,
        ),
    ]
