from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('ipam', '0049_vlan_status_db'),
    ]

    operations = [
        # Remove: VLAN.status (old)
        migrations.RemoveField(
            model_name='vlan',
            name='status',
        ),
        # Rename: VLAN.status_db -> VLAN.status
        migrations.RenameField(
            model_name='vlan',
            old_name='status_db',
            new_name='status',
        ),
    ]
