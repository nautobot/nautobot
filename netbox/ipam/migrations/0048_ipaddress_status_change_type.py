from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('ipam', '0047_ipaddress_status_db'),
    ]

    operations = [
        # Remove: IPAddress.status (old)
        migrations.RemoveField(
            model_name='ipaddress',
            name='status',
        ),
        # Rename: IPAddress.status_db -> IPAddress.status
        migrations.RenameField(
            model_name='ipaddress',
            old_name='status_db',
            new_name='status',
        ),
    ]
