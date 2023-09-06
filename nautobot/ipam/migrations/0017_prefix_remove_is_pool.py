from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0034_migrate_region_and_site_data_to_locations"),
        ("ipam", "0016_prefix_type_data_migration"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="prefix",
            name="is_pool",
        ),
    ]
