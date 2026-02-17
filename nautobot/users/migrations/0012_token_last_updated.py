from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0011_alter_user_default_saved_views"),
    ]

    operations = [
        migrations.AddField(
            model_name="token",
            name="last_updated",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
