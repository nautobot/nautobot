from django.db import migrations


def rename_scheduled_job_kwargs_request_user(apps, schema_editor):
    """
    Rename ScheduledJob.kwargs["request"]["user"] to ScheduledJob.kwargs["request"]["_user_pk"]
    to support https://github.com/nautobot/nautobot/pull/3105 and prevent an AttributeError exception
    when the scheduled job runs.
    """
    ScheduledJob = apps.get_model("extras", "ScheduledJob")
    for sj in ScheduledJob.objects.all():
        if "request" in sj.kwargs:
            sj.kwargs["request"].setdefault("_user_pk", sj.kwargs["request"].pop("user", None))
            sj.save()


def reverse_rename_scheduled_job_kwargs_request_user(apps, schema_editor):
    ScheduledJob = apps.get_model("extras", "ScheduledJob")
    for sj in ScheduledJob.objects.all():
        if "request" in sj.kwargs:
            sj.kwargs["request"].setdefault("user", sj.kwargs["request"].pop("_user_pk", None))
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
