from django.conf import settings
from django.db import migrations


def populate_user_name(apps, schema_editor):
    """
    Populate the new ScheduledJob.user_name field for existing rows.

    Sets user_name to the associated user's username, or "Undefined" when the
    user has been deleted (user FK is null).
    """
    ScheduledJob = apps.get_model("extras", "ScheduledJob")
    user_app_label, user_model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_app_label, user_model_name)

    user_ids = (
        ScheduledJob.objects.filter(user__isnull=False, user_name="").values_list("user_id", flat=True).distinct()
    )
    usernames_by_id = dict(User.objects.filter(pk__in=list(user_ids)).values_list("pk", "username"))

    to_update = []
    for scheduled_job in ScheduledJob.objects.filter(user_name="").only("pk", "user_id", "user_name"):
        if scheduled_job.user_id and scheduled_job.user_id in usernames_by_id:
            scheduled_job.user_name = usernames_by_id[scheduled_job.user_id]
        else:
            scheduled_job.user_name = "Undefined"
        to_update.append(scheduled_job)

    if to_update:
        ScheduledJob.objects.bulk_update(to_update, ["user_name"], 1000)


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0143_scheduledjob_user_name"),
    ]

    operations = [
        migrations.RunPython(populate_user_name, migrations.RunPython.noop),
    ]
