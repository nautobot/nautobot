from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ipam", "0016_prefix_type_data_migration"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="prefix",
            name="is_pool",
        ),
    ]
