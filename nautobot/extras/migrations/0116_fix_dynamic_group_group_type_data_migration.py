from django.db import migrations

from nautobot.extras.utils import fixup_dynamic_group_group_types


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0115_scheduledjob_time_zone"),
    ]

    operations = [
        migrations.RunPython(
            code=fixup_dynamic_group_group_types,
            reverse_code=migrations.operations.special.RunPython.noop,
        ),
    ]
