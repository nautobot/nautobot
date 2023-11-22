import os

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.utils.crypto import get_random_string


class Command(BaseCommand):
    help = "Populate the database with various data as a baseline for testing (automated or manual)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed",
            help="String to use as a random generator seed for reproducible results.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Flush any existing data from the database before generating new data.",
        )
        parser.add_argument(
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do NOT prompt the user for input or confirmation of any kind.",
        )
        parser.add_argument(
            "--cache-test-fixtures",
            action="store_true",
            help="Save test database to a json fixture file to re-use on subsequent tests.",
        )
        parser.add_argument(
            "--fixture-file",
            default="development/factory_dump.json",
            help="Fixture file to use with --cache-test-fixtures.",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help='The database to generate the test data in. Defaults to the "default" database.',
        )

    def _generate_factory_data(self, seed, db_name):
        try:
            import factory.random

            from nautobot.dcim.factory import (
                DeviceRedundancyGroupFactory,
                DeviceRoleFactory,
                DeviceTypeFactory,
                ManufacturerFactory,
                PlatformFactory,
            )
            from nautobot.extras.factory import StatusFactory, TagFactory
            from nautobot.extras.management import populate_status_choices
            from nautobot.dcim.factory import (
                RegionFactory,
                SiteFactory,
                LocationTypeFactory,
                LocationFactory,
            )
            from nautobot.extras.utils import TaggableClassesQuery
            from nautobot.ipam.factory import (
                AggregateFactory,
                RIRFactory,
                RoleFactory,
                RouteTargetFactory,
                VLANGroupFactory,
                VLANFactory,
                VRFFactory,
            )
            from nautobot.tenancy.factory import TenantFactory, TenantGroupFactory
        except ImportError as err:
            raise CommandError('Unable to load data factories. Is the "factory-boy" package installed?') from err

        if not seed:
            seed = get_random_string(16)
        self.stdout.write(f'Seeding the pseudo-random number generator with seed "{seed}"...')
        factory.random.reseed_random(seed)

        self.stdout.write("Creating Statuses...")
        populate_status_choices(verbosity=0, using=db_name)
        StatusFactory.create_batch(10, using=db_name)
        self.stdout.write("Creating Tags...")
        # Ensure that we have some tags that are applicable to all relevant content-types
        TagFactory.create_batch(5, content_types=TaggableClassesQuery().as_queryset(), using=db_name)
        # ...and some tags that apply to a random subset of content-types
        TagFactory.create_batch(15, using=db_name)
        self.stdout.write("Creating TenantGroups...")
        TenantGroupFactory.create_batch(10, has_parent=False, using=db_name)
        TenantGroupFactory.create_batch(10, has_parent=True, using=db_name)
        self.stdout.write("Creating Tenants...")
        TenantFactory.create_batch(10, has_group=False, using=db_name)
        TenantFactory.create_batch(10, has_group=True, using=db_name)
        self.stdout.write("Creating Regions...")
        RegionFactory.create_batch(15, has_parent=False, using=db_name)
        RegionFactory.create_batch(5, has_parent=True, using=db_name)
        self.stdout.write("Creating Sites...")
        SiteFactory.create_batch(15, using=db_name)
        self.stdout.write("Creating LocationTypes...")
        LocationTypeFactory.create_batch(7, using=db_name)  # only 7 unique LocationTypes are hard-coded presently
        self.stdout.write("Creating Locations...")
        LocationFactory.create_batch(20, using=db_name)  # we need more locations with sites since it can be nested now.
        self.stdout.write("Creating RIRs...")
        RIRFactory.create_batch(9, using=db_name)  # only 9 unique RIR names are hard-coded presently
        self.stdout.write("Creating RouteTargets...")
        RouteTargetFactory.create_batch(20, using=db_name)
        self.stdout.write("Creating VRFs...")
        VRFFactory.create_batch(20, using=db_name)
        self.stdout.write("Creating IP/VLAN Roles...")
        RoleFactory.create_batch(10, using=db_name)
        self.stdout.write("Creating VLANGroups...")
        VLANGroupFactory.create_batch(20, using=db_name)
        self.stdout.write("Creating VLANs...")
        VLANFactory.create_batch(20, using=db_name)
        self.stdout.write("Creating Aggregates, Prefixes and IP Addresses...")
        AggregateFactory.create_batch(5, has_tenant_group=True, using=db_name)
        AggregateFactory.create_batch(5, has_tenant_group=False, has_tenant=True, using=db_name)
        AggregateFactory.create_batch(10, using=db_name)
        self.stdout.write("Creating Sites without Prefixes, VLANs or VLANGroups...")
        SiteFactory.create_batch(5, has_region=False, has_tenant=False, using=db_name)
        self.stdout.write("Creating Manufacturers...")
        ManufacturerFactory.create_batch(14, using=db_name)  # All 14 hard-coded Manufacturers for now.
        self.stdout.write("Creating Platforms (with manufacturers)...")
        PlatformFactory.create_batch(20, has_manufacturer=True, using=db_name)
        self.stdout.write("Creating Platforms (without manufacturers)...")
        PlatformFactory.create_batch(5, has_manufacturer=False, using=db_name)
        self.stdout.write("Creating DeviceTypes...")
        DeviceTypeFactory.create_batch(20, using=db_name)
        self.stdout.write("Creating DeviceRedundancyGroups...")
        DeviceRedundancyGroupFactory.create_batch(10, using=db_name)
        self.stdout.write("Creating DeviceRoles...")
        DeviceRoleFactory.create_batch(10, using=db_name)

    def handle(self, *args, **options):
        if options["flush"]:
            if options["interactive"]:
                confirm = input(
                    f"""\
You have requested a flush of the database before generating new data.
This will IRREVERSIBLY DESTROY all data in the "{connections[options['database']].settings_dict['NAME']}" database,
including all user accounts, and return each table to an empty state.
Are you SURE you want to do this?

Type 'yes' to continue, or 'no' to cancel: """
                )
                if confirm != "yes":
                    self.stdout.write("Cancelled.")
                    return

            self.stdout.write(
                self.style.WARNING(f'Flushing all existing data from the database "{options["database"]}"...')
            )
            call_command("flush", "--no-input", "--database", options["database"])

        if options["cache_test_fixtures"] and os.path.exists(options["fixture_file"]):
            call_command("loaddata", options["fixture_file"])
        else:
            self._generate_factory_data(options["seed"], options["database"])

            if options["cache_test_fixtures"]:
                call_command(
                    "dumpdata",
                    "--natural-foreign",
                    "--natural-primary",
                    indent=2,
                    format="json",
                    exclude=["contenttypes", "django_rq", "auth.permission", "extras.job", "extras.customfield"],
                    output=options["fixture_file"],
                )

                self.stdout.write(self.style.SUCCESS(f"Dumped factory data to {options['fixture_file']}"))

        self.stdout.write(self.style.SUCCESS(f"Database {options['database']} populated successfully!"))
