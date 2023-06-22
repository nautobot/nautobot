# TODO(jathan): This file MUST NOT be merged into Nautobot v2 (next).

import argparse

from django.db import models
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from nautobot.dcim.models import VirtualChassis
from nautobot.extras.models import ConfigContext, ConfigContextSchema, ExportTemplate


HELP_TEXT = """
Performs pre-migration validation checks for Nautobot 2.0.

If the Nautobot 1.5 instance cannot be upgraded, this command will exit uncleanly.
"""


def check_virtualchassis_uniqueness():
    """
    Check for uniqueness enforcement changes for VirtualChassis.

    - Make `name` unique, reject migration if duplicate (don't want to rename VCs)

    See: https://github.com/nautobot/nautobot/issues/3846
    """
    vc_dupes = VirtualChassis.objects.values("name").annotate(count=models.Count("id")).filter(count__gt=1)

    if vc_dupes.exists():
        raise ValidationError(
            f"You cannot migrate VirtualChassis objects with non-unique names:\n - {list(vc_dupes)}\n"
        )


def check_exporttemplate_uniqueness():
    """
    Check for uniqueness enforcement changes for ExportTemplate.

    - Move to `unique_together` on just `content_type` and `name`, reject migration if duplicate.

    See: https://github.com/nautobot/nautobot/issues/3848
    """
    et_dupes = (
        ExportTemplate.objects.values("content_type", "name").annotate(count=models.Count("id")).filter(count__gt=1)
    )

    if et_dupes.exists():
        raise ValidationError(
            f"You cannot migrate ExportTemplate objects with non-unique content_type, name pairs:\n - {list(et_dupes)}\n"
        )


def check_configcontext_uniqueness():
    """
    Check for uniqueness enforcement changes for ConfigContext and ConfigContextSchema.

    - Move to `name` unique, reject migration if duplicate

    See: https://github.com/nautobot/nautobot/issues/3849
    """
    cc_dupes = ConfigContext.objects.values("name").annotate(count=models.Count("id")).filter(count__gt=1)
    ccs_dupes = ConfigContextSchema.objects.values("name").annotate(count=models.Count("id")).filter(count__gt=1)

    if any(
        [
            cc_dupes.exists(),
            ccs_dupes.exists(),
        ]
    ):
        raise ValidationError(
            "You cannot migrate ConfigContext or ConfigContextSchema objects that have non-unique names:\n"
            f"- ConfigContext: {list(cc_dupes)}\n"
            f"- ConfigContextSchema: {list(ccs_dupes)}\n"
        )


class Command(BaseCommand):
    help = HELP_TEXT

    def create_parser(self, *args, **kwargs):
        """Custom parser that can display multiline help."""
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def handle(self, *args, **options):
        checks = [
            check_configcontext_uniqueness,
            check_exporttemplate_uniqueness,
            check_virtualchassis_uniqueness,
        ]
        errors = []

        for check in checks:
            func_name = check.__code__.co_name
            try:
                self.stdout.write(self.style.WARNING(f">>> Running check: {func_name}..."))
                check()
            except ValidationError as err:
                errors.append(err)

        if errors:
            msg = "One or more pre-migration checks failed:\n"
            for err_item in errors:
                message_lines = err_item.message.splitlines()
                for line in message_lines:
                    msg += f"    {line}\n"
                msg += "\n"
            raise CommandError(msg)
        else:
            self.stdout.write(self.style.SUCCESS("All pre-migration checks passed."))
