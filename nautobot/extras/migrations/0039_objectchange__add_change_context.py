from django.db import migrations, models

from nautobot.extras.choices import ObjectChangeEventContextChoices


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0038_configcontext_locations"),
    ]

    operations = [
        migrations.AddField(
            model_name="objectchange",
            name="change_context",
            field=models.CharField(
                db_index=True, default=ObjectChangeEventContextChoices.CONTEXT_UNKNOWN, editable=False, max_length=50
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="objectchange",
            name="change_context_detail",
            field=models.CharField(blank=True, editable=False, max_length=100),
        ),
    ]
