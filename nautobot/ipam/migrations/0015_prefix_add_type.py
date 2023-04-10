from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ipam", "0014_rename_foreign_keys_and_related_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="prefix",
            name="type",
            field=models.CharField(default="network", max_length=50),
        ),
    ]
