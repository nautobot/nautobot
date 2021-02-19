from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('dcim', '0133_powerfeed_status_db'),
    ]

    operations = [
        # Remove: PowerFeed.status (old)
        migrations.RemoveField(
            model_name='powerfeed',
            name='status',
        ),
        # Rename: PowerFeed.status_db -> PowerFeed.status
        migrations.RenameField(
            model_name='powerfeed',
            old_name='status_db',
            new_name='status',
        ),
    ]
