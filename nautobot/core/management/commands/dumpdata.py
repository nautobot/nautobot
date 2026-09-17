from django.core.management.commands.dumpdata import Command as DumpDataCommand

from nautobot.core.models.sensitive_fields import sensitive_fields_exempt


class Command(DumpDataCommand):
    """Extend Django's `dumpdata` to serialize fields that `STRICT_SENSITIVE_FIELDS` normally withholds."""

    def handle(self, *app_labels, **options):
        with sensitive_fields_exempt():
            return super().handle(*app_labels, **options)
