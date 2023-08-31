from django.core.management.base import BaseCommand
from netutils.lib_mapper import NAPALM_LIB_MAPPER


from nautobot.dcim.models import Platform


HELP_TEXT = """
Populate the Platform.network_driver field from the napalm_driver or slug fields.

This command will attempt to find a valid mapping from the Platform.napalm_driver field to a matching entry in netutils.lib_mapper.NAPALM_LIB_MAPPER.

If no mapping is found, the value of the Platform.slug field will be used instead.

--interactive can be used to prompt for confirmation before making changes to each Platform.

--no-use-slug-field can be used to disable populating the network_driver field from the Platform.slug field.

--no-use-napalm-driver-field can be used to disable populating the network_driver field from the Platform.napalm_driver field.

By default, the network_driver field will only be populated if it is currently empty. Use --force to overwrite existing values.
"""


class Command(BaseCommand):
    help = HELP_TEXT

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--no-use-slug-field",
            action="store_false",
            dest="use_slug_field",
            default=True,
            help="Do not populate network_driver from the platform's slug field.",
        )
        group.add_argument(
            "--no-use-napalm-driver-field",
            action="store_false",
            dest="use_napalm_driver_field",
            default=True,
            help="Do not populate network_driver from the platform's napalm_driver field mapping to netutils.lib_mapper.NAPALM_LIB_MAPPER",
        )
        parser.add_argument(
            "--interactive",
            action="store_true",
            default=False,
            help="Prompt to confirm before updating the network_driver field on each platform.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Overwrite existing network_driver field values.",
        )

    def handle(self, *args, **options):
        for platform in Platform.objects.all():
            self.stdout.write(f"Checking {platform}...")

            if platform.network_driver and not options["force"]:
                self.stdout.write(
                    self.style.WARNING(f"{platform} currently is set to {platform.network_driver}, skipping.")
                )
                continue

            network_driver = ""
            if options["use_napalm_driver_field"] and platform.napalm_driver:
                if platform.napalm_driver in NAPALM_LIB_MAPPER:
                    network_driver = NAPALM_LIB_MAPPER[platform.napalm_driver]
            if network_driver == "" and options["use_slug_field"]:
                network_driver = platform.slug

            if network_driver == "":
                continue

            if options["interactive"]:
                confirm = ""
                while confirm not in ["y", "n"]:
                    confirm = input(f'Set "{platform}" network_driver to "{network_driver}"? [y/n] ')
                if confirm == "n":
                    continue

            platform.network_driver = network_driver
            platform.validated_save()
            self.stdout.write(self.style.SUCCESS(f'Set "{platform}" network_driver to "{network_driver}".'))
