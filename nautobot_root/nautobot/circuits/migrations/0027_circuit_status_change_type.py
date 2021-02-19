from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('circuits', '0026_circuit_status_db'),
    ]

    operations = [
        # Remove: Circuit.status (old)
        migrations.RemoveField(
            model_name='circuit',
            name='status',
        ),
        # Rename: Circuit.status_db -> Circuit.status
        migrations.RenameField(
            model_name='circuit',
            old_name='status_db',
            new_name='status',
        ),
    ]
