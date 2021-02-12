from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('dcim', '0129_rack_status_db'),
    ]

    operations = [
        # Remove: Rack.status (old)
        migrations.RemoveField(
            model_name='rack',
            name='status',
        ),
        # Rename: Rack.status_db -> Rack.status
        migrations.RenameField(
            model_name='rack',
            old_name='status_db',
            new_name='status',
        ),
    ]
