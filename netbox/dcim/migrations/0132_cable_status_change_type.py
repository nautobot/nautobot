from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('dcim', '0131_cable_status_db'),
    ]

    operations = [
        # Remove: Cable.status (old)
        migrations.RemoveField(
            model_name='cable',
            name='status',
        ),
        # Rename: Cable.status_db -> Cable.status
        migrations.RenameField(
            model_name='cable',
            old_name='status_db',
            new_name='status',
        ),
    ]
