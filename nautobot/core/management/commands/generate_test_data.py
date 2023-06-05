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

    def _generate_factory_data(self, seed):
        try:
            import factory.random

            from nautobot.circuits.factory import (
                CircuitFactory,
                CircuitTerminationFactory,
                CircuitTypeFactory,
                ProviderFactory,
                ProviderNetworkFactory,
            )
            from nautobot.dcim.factory import (
                DeviceRedundancyGroupFactory,
                DeviceTypeFactory,
                ManufacturerFactory,
                PlatformFactory,
            )
            from nautobot.extras.factory import RoleFactory, StatusFactory, TagFactory
            from nautobot.extras.management import populate_status_choices
            from nautobot.dcim.factory import (
                LocationTypeFactory,
                LocationFactory,
            )
            from nautobot.extras.utils import TaggableClassesQuery
            from nautobot.ipam.factory import (
                NamespaceFactory,
                PrefixFactory,
                RIRFactory,
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

        self.stdout.write("Creating Roles...")
        RoleFactory.create_batch(20)
        self.stdout.write("Creating Statuses...")
        populate_status_choices(verbosity=0)
        StatusFactory.create_batch(10)
        self.stdout.write("Creating Tags...")
        # Ensure that we have some tags that are applicable to all relevant content-types
        TagFactory.create_batch(5, content_types=TaggableClassesQuery().as_queryset())
        # ...and some tags that apply to a random subset of content-types
        TagFactory.create_batch(15)
        self.stdout.write("Creating TenantGroups...")
        TenantGroupFactory.create_batch(10, has_parent=False)
        TenantGroupFactory.create_batch(10, has_parent=True)
        self.stdout.write("Creating Tenants...")
        TenantFactory.create_batch(10, has_tenant_group=False)
        TenantFactory.create_batch(10, has_tenant_group=True)
        self.stdout.write("Creating LocationTypes...")
        LocationTypeFactory.create_batch(7)  # only 7 unique LocationTypes are hard-coded presently
        self.stdout.write("Creating Locations...")
        # First 7 locations must be created in specific order so subsequent objects have valid parents to reference
        LocationFactory.create_batch(7, has_parent=True)
        LocationFactory.create_batch(40)
        LocationFactory.create_batch(10, has_parent=False)
        self.stdout.write("Creating Namespaces...")
        NamespaceFactory.create_batch(1)
        self.stdout.write("Creating RIRs...")
        RIRFactory.create_batch(9)  # only 9 unique RIR names are hard-coded presently
        self.stdout.write("Creating RouteTargets...")
        RouteTargetFactory.create_batch(20)
        self.stdout.write("Creating VRFs...")
        VRFFactory.create_batch(10, has_tenant=True)
        VRFFactory.create_batch(10, has_tenant=False)
        self.stdout.write("Creating VLANGroups...")
        VLANGroupFactory.create_batch(20)
        self.stdout.write("Creating VLANs...")
        VLANFactory.create_batch(20)
        self.stdout.write("Creating Prefixes and IP Addresses...")
        PrefixFactory.create_batch(30)
        self.stdout.write("Creating Manufacturers...")
        ManufacturerFactory.create_batch(8)  # First 8 hard-coded Manufacturers
        self.stdout.write("Creating Platforms (with manufacturers)...")
        PlatformFactory.create_batch(20, has_manufacturer=True)
        self.stdout.write("Creating Platforms (without manufacturers)...")
        PlatformFactory.create_batch(5, has_manufacturer=False)
        self.stdout.write("Creating Manufacturers without Platforms...")
        ManufacturerFactory.create_batch(4)  # 4 more hard-coded Manufacturers
        self.stdout.write("Creating DeviceTypes...")
        DeviceTypeFactory.create_batch(30)
        self.stdout.write("Creating Manufacturers without DeviceTypes or Platforms...")
        ManufacturerFactory.create_batch(2)  # Last 2 hard-coded Manufacturers
        self.stdout.write("Creating DeviceRedundancyGroups...")
        DeviceRedundancyGroupFactory.create_batch(20)
        self.stdout.write("Creating CircuitTypes...")
        CircuitTypeFactory.create_batch(20)
        self.stdout.write("Creating Providers...")
        ProviderFactory.create_batch(20)
        self.stdout.write("Creating ProviderNetworks...")
        ProviderNetworkFactory.create_batch(20)
        self.stdout.write("Creating Circuits...")
        CircuitFactory.create_batch(40)
        self.stdout.write("Creating Providers without Circuits...")
        ProviderFactory.create_batch(20)
        self.stdout.write("Creating CircuitTerminations...")
        CircuitTerminationFactory.create_batch(2, has_location=True, term_side="A")
        CircuitTerminationFactory.create_batch(2, has_location=True, term_side="Z")
        CircuitTerminationFactory.create_batch(2, has_location=False, term_side="A")
        CircuitTerminationFactory.create_batch(2, has_location=False, term_side="Z")
        CircuitTerminationFactory.create_batch(2, has_port_speed=True, has_upstream_speed=False)
        CircuitTerminationFactory.create_batch(
            size=2,
            has_location=True,
            has_port_speed=True,
            has_upstream_speed=True,
            has_xconnect_id=True,
            has_pp_info=True,
            has_description=True,
        )
        # TODO: nautobot.tenancy.tests.test_filters currently calls the following additional factories:
        # UserFactory.create_batch(10)
        # RackFactory.create_batch(10)
        # RackReservationFactory.create_batch(10)
        # ClusterTypeFactory.create_batch(10)
        # ClusterGroupFactory.create_batch(10)
        # ClusterFactory.create_batch(10)
        # VirtualMachineFactory.create_batch(10)
        # We need to remove them from there and enable them here instead, but that will require many test updates.

    def handle(self, *args, **options):
        if options["flush"]:
            if options["interactive"]:
                confirm = input(
                    f"""\
You have requested a flush of the database before generating new data.
This will IRREVERSIBLY DESTROY all data in the "{connections[DEFAULT_DB_ALIAS].settings_dict['NAME']}" database,
including all user accounts, and return each table to an empty state.
Are you SURE you want to do this?

Type 'yes' to continue, or 'no' to cancel: """
                )
                if confirm != "yes":
                    self.stdout.write("Cancelled.")
                    return

            self.stdout.write(self.style.WARNING("Flushing all existing data from the database..."))
            call_command("flush", "--no-input")

        if options["cache_test_fixtures"] and os.path.exists(options["fixture_file"]):
            self.stdout.write(self.style.WARNING(f"Loading factory data from file {options['fixture_file']}"))
            call_command("loaddata", options["fixture_file"])
        else:
            self._generate_factory_data(options["seed"])

            if options["cache_test_fixtures"]:
                self.stdout.write(self.style.WARNING(f"Saving factory data to file {options['fixture_file']}"))

                call_command(
                    "dumpdata",
                    indent=2,
                    format="json",
                    exclude=["contenttypes", "auth.permission", "extras.job", "extras.customfield"],
                    output=options["fixture_file"],
                )

                self.stdout.write(self.style.SUCCESS(f"Dumped factory data to {options['fixture_file']}"))

        self.stdout.write(self.style.SUCCESS("Database populated successfully!"))
