import argparse

from django.db import models
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from nautobot.dcim.models import Interface, VirtualChassis
from nautobot.extras.models import ConfigContext, ConfigContextSchema, ExportTemplate
from nautobot.virtualization.models import VMInterface


HELP_TEXT = """
Performs pre-migration validation checks for Nautobot 2.0.

If the Nautobot 1.5 instance cannot be upgraded, this command will exit uncleanly.
"""


# Forklifted from v2: `nautobot.ipam.utils.migrations.check_interface_vrfs`
def check_interface_vrfs():
    """
    Enumerate all Interface and VMInterface objects and raise an exception if any interface is found that is associated
    to more than one distinct VRF through the ip_address many-to-many relationship.

    Returns:
        None
    """

    interfaces_with_multiple_vrfs = (
        Interface.objects.annotate(vrf_count=models.Count("ip_addresses__vrf", distinct=True))
        .filter(vrf_count__gt=1)
        .distinct()
    )
    interfaces_with_mixed_vrfs = (
        Interface.objects.filter(ip_addresses__vrf__isnull=True).filter(ip_addresses__vrf__isnull=False).distinct()
    )
    vm_interfaces_with_multiple_vrfs = (
        VMInterface.objects.annotate(vrf_count=models.Count("ip_addresses__vrf", distinct=True))
        .filter(vrf_count__gt=1)
        .distinct()
    )
    vm_interfaces_with_mixed_vrfs = (
        VMInterface.objects.filter(ip_addresses__vrf__isnull=True).filter(ip_addresses__vrf__isnull=False).distinct()
    )

    if any(
        [
            interfaces_with_multiple_vrfs.exists(),
            interfaces_with_mixed_vrfs.exists(),
            vm_interfaces_with_multiple_vrfs.exists(),
            vm_interfaces_with_mixed_vrfs.exists(),
        ]
    ):
        raise ValidationError(
            "You cannot migrate Interfaces or VMInterfaces that have IPs with differing VRFs:\n"
            f"{list(interfaces_with_multiple_vrfs)}\n"
            f"{list(interfaces_with_mixed_vrfs)}\n"
            f"{list(vm_interfaces_with_multiple_vrfs)}\n"
            f"{list(vm_interfaces_with_mixed_vrfs)}"
        )


def check_virtualchassis_uniqueness():
    """
    Check for uniqueness enforcement changes for VirtualChassis.

    - Make `name` unique, reject migration if duplicate (don't want to rename VCs)

    See: https://github.com/nautobot/nautobot/issues/3846
    """
    vc_dupes = VirtualChassis.objects.values("name").annotate(count=models.Count("id")).filter(count__gt=1)

    if vc_dupes.exists():
        raise ValidationError(
            "You cannot migrate VirtualChassis objects that non-unique names:\n" f"{list(vc_dupes)}\n"
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
            f"You cannot migrate ExportTemplate objects with non-unique content_type, name pairs:\n {list(et_dupes)}\n"
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
            f"{list(cc_dupes)}\n"
            f"{list(ccs_dupes)}\n"
        )


class Command(BaseCommand):
    help = HELP_TEXT

    def create_parser(self, *args, **kwargs):
        """Custom parser that can display multiline help."""
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def handle(self, *args, **options):
        # Pre-migration checks run here.

        checks = [
            check_interface_vrfs,
            check_configcontext_uniqueness,
            check_exporttemplate_uniqueness,
            check_virtualchassis_uniqueness,
        ]

        for check in checks:
            try:
                self.stdout.write(self.style.WARNING(f">>> Running check: {check.__code__.co_name}..."))
                check()
            except ValidationError as err:
                # self.stderr.write(self.style.ERROR(str(err)))
                # raise CommandError("Pre-migration checks failed.")
                raise CommandError(str(err))
        else:
            self.stdout.write(self.style.SUCCESS("All pre-migration checks passed."))
