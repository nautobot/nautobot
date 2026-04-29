from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0142_remove_scheduledjob_approval_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="scheduledjob",
            name="user_name",
            field=models.CharField(db_index=True, default="", editable=False, max_length=150),
            preserve_default=False,
        ),
    ]
