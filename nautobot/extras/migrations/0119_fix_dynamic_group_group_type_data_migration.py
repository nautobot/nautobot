from django.db import migrations

from nautobot.extras.utils import fixup_dynamic_group_group_types


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0118_remove_task_queues_from_job_and_queue_from_scheduled_job"),
    ]

    operations = [
        migrations.RunPython(
            code=fixup_dynamic_group_group_types,
            reverse_code=migrations.operations.special.RunPython.noop,
        ),
    ]
