from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0011_alter_user_default_saved_views"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="created",
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="last_updated",
            field=models.DateTimeField(auto_now=True, blank=True, null=True),
        ),
    ]
