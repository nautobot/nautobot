from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('ipam', '0045_prefix_status_db'),
    ]

    operations = [
        # Remove: Prefix.status (old)
        migrations.RemoveField(
            model_name='prefix',
            name='status',
        ),
        # Rename: Prefix.status_db -> Prefix.status
        migrations.RenameField(
            model_name='prefix',
            old_name='status_db',
            new_name='status',
        ),
    ]
