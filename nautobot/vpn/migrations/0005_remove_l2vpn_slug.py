from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vpn', '0004_l2vpntermination_primary_model'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='l2vpn',
            name='slug',
        ),
    ]
