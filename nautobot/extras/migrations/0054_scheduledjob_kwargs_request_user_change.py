from django.db import migrations


def rename_scheduled_job_kwargs_request_user(apps, schema_editor):
    ScheduledJob = apps.get_model("extras", "ScheduledJob")
    for sj in ScheduledJob.objects.all():
        if "request" in sj.kwargs and sj.kwargs["request"].get("user", None) is not None:
            sj.kwargs["request"].setdefault("_user_pk", sj.kwargs["request"].pop("user"))
            sj.save()


def reverse_rename_scheduled_job_kwargs_request_user(apps, schema_editor):
    ScheduledJob = apps.get_model("extras", "ScheduledJob")
    for sj in ScheduledJob.objects.all():
        if "request" in sj.kwargs and sj.kwargs["request"].get("_user_pk", None) is not None:
            sj.kwargs["request"].setdefault("user", sj.kwargs["request"].pop("_user_pk"))
            sj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0053_relationship_required_on"),
    ]

    operations = [
        migrations.RunPython(
            rename_scheduled_job_kwargs_request_user, reverse_code=reverse_rename_scheduled_job_kwargs_request_user
        ),
    ]
