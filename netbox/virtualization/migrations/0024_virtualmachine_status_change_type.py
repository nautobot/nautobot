from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('virtualization', '0023_virtualmachine_status_db'),
    ]

    operations = [
        # Remove: VirtualMachine.status (old)
        migrations.RemoveField(
            model_name='virtualmachine',
            name='status',
        ),
        # Rename: VirtualMachine.status_db -> VirtualMachine.status
        migrations.RenameField(
            model_name='virtualmachine',
            old_name='status_db',
            new_name='status',
        ),
    ]
