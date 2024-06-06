import hashlib
import json
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections, DEFAULT_DB_ALIAS
from django.utils.crypto import get_random_string

from nautobot.core.settings_funcs import is_truthy


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

            from nautobot.circuits.factory import (
                CircuitFactory,
                CircuitTerminationFactory,
                CircuitTypeFactory,
                ProviderFactory,
                ProviderNetworkFactory,
            )
            from nautobot.dcim.factory import (
                ControllerFactory,
                ControllerManagedDeviceGroupFactory,
                DeviceFactory,
                DeviceFamilyFactory,
                DeviceRedundancyGroupFactory,
                DeviceTypeFactory,
                LocationFactory,
                LocationTypeFactory,
                ManufacturerFactory,
                PlatformFactory,
                SoftwareImageFileFactory,
                SoftwareVersionFactory,
            )
            from nautobot.extras.factory import (
                ContactFactory,
                ExternalIntegrationFactory,
                RoleFactory,
                StatusFactory,
                TagFactory,
                TeamFactory,
            )
            from nautobot.extras.management import populate_role_choices, populate_status_choices
            from nautobot.extras.utils import TaggableClassesQuery
            from nautobot.ipam.choices import PrefixTypeChoices
            from nautobot.ipam.factory import (
                NamespaceFactory,
                PrefixFactory,
                RIRFactory,
                RouteTargetFactory,
                VLANFactory,
                VLANGroupFactory,
                VRFFactory,
            )
            from nautobot.tenancy.factory import TenantFactory, TenantGroupFactory
        except ImportError as err:
            raise CommandError('Unable to load data factories. Is the "factory-boy" package installed?') from err

        if not seed:
            seed = get_random_string(16)
        self.stdout.write(f'Seeding the pseudo-random number generator with seed "{seed}"...')
        factory.random.reseed_random(seed)

        def _create_batch(some_factory, count, **kwargs):
            some_factory.create_batch(count, using=db_name, **kwargs)
            if is_truthy(os.environ.get("GITHUB_ACTIONS", "false")):
                model = some_factory._meta.get_model_class()
                model_ids = list(model.objects.order_by("id").values_list("id", flat=True))
                sha256_hash = hashlib.sha256(json.dumps(model_ids, cls=DjangoJSONEncoder).encode()).hexdigest()
                self.stdout.write(f"  SHA256 hash of {model.__name__} PKs: {sha256_hash}")

        self.stdout.write("Creating Roles...")
        populate_role_choices(verbosity=0, using=db_name)
        _create_batch(RoleFactory, 20)
        self.stdout.write("Creating Statuses...")
        populate_status_choices(verbosity=0, using=db_name)
        _create_batch(StatusFactory, 10)
        self.stdout.write("Creating Tags...")
        # Ensure that we have some tags that are applicable to all relevant content-types
        _create_batch(TagFactory, 5, content_types=TaggableClassesQuery().as_queryset())
        # ...and some tags that apply to a random subset of content-types
        _create_batch(TagFactory, 15)
        self.stdout.write("Creating Contacts...")
        _create_batch(ContactFactory, 20)
        self.stdout.write("Creating Teams...")
        _create_batch(TeamFactory, 20)
        self.stdout.write("Creating TenantGroups...")
        _create_batch(TenantGroupFactory, 10, has_parent=False)
        _create_batch(TenantGroupFactory, 10, has_parent=True)
        self.stdout.write("Creating Tenants...")
        _create_batch(TenantFactory, 10, has_tenant_group=False)
        _create_batch(TenantFactory, 10, has_tenant_group=True)
        self.stdout.write("Creating LocationTypes...")
        _create_batch(LocationTypeFactory, 7)  # only 7 unique LocationTypes are hard-coded presently
        self.stdout.write("Creating Locations...")
        # First 7 locations must be created in specific order so subsequent objects have valid parents to reference
        _create_batch(LocationFactory, 7, has_parent=True)
        _create_batch(LocationFactory, 40)
        _create_batch(LocationFactory, 10, has_parent=False)
        self.stdout.write("Creating Controller with Groups...")
        _create_batch(ControllerFactory, 1)
        _create_batch(ControllerManagedDeviceGroupFactory, 5)
        self.stdout.write("Creating RIRs...")
        _create_batch(RIRFactory, 9)  # only 9 unique RIR names are hard-coded presently
        self.stdout.write("Creating RouteTargets...")
        _create_batch(RouteTargetFactory, 20)
        self.stdout.write("Creating Namespaces...")
        _create_batch(NamespaceFactory, 10)
        self.stdout.write("Creating VRFs...")
        _create_batch(VRFFactory, 10, has_tenant=True)
        _create_batch(VRFFactory, 10, has_tenant=False)
        self.stdout.write("Creating VLANGroups...")
        _create_batch(VLANGroupFactory, 20)
        self.stdout.write("Creating VLANs...")
        _create_batch(VLANFactory, 20)
        self.stdout.write("Creating Prefixes and IP Addresses...")
        for i in range(30):
            PrefixFactory.create(prefix=f"10.{i}.0.0/16", type=PrefixTypeChoices.TYPE_CONTAINER, using=db_name)
            PrefixFactory.create(prefix=f"2001:db8:0:{i}::/64", type=PrefixTypeChoices.TYPE_CONTAINER, using=db_name)
        self.stdout.write("Creating Empty Namespaces...")
        _create_batch(NamespaceFactory, 5)
        self.stdout.write("Creating Device Families...")
        _create_batch(DeviceFamilyFactory, 20)
        self.stdout.write("Creating Manufacturers...")
        _create_batch(ManufacturerFactory, 8)  # First 8 hard-coded Manufacturers
        self.stdout.write("Creating Platforms (with manufacturers)...")
        _create_batch(PlatformFactory, 20, has_manufacturer=True)
        self.stdout.write("Creating Platforms (without manufacturers)...")
        _create_batch(PlatformFactory, 5, has_manufacturer=False)
        self.stdout.write("Creating SoftwareVersions...")
        _create_batch(SoftwareVersionFactory, 20)
        self.stdout.write("Creating SoftwareImageFiles...")
        _create_batch(SoftwareImageFileFactory, 25)
        self.stdout.write("Creating Manufacturers without Platforms...")
        _create_batch(ManufacturerFactory, 4)  # 4 more hard-coded Manufacturers
        self.stdout.write("Creating DeviceTypes...")
        _create_batch(DeviceTypeFactory, 30)
        self.stdout.write("Creating Manufacturers without DeviceTypes or Platforms...")
        _create_batch(ManufacturerFactory, 2)  # Last 2 hard-coded Manufacturers
        self.stdout.write("Creating DeviceRedundancyGroups...")
        _create_batch(DeviceRedundancyGroupFactory, 20)
        self.stdout.write("Creating Devices...")
        _create_batch(DeviceFactory, 20)
        self.stdout.write("Creating SoftwareVersions with Devices, InventoryItems or VirtualMachines...")
        _create_batch(SoftwareVersionFactory, 5)
        self.stdout.write("Creating SoftwareImageFiles without DeviceTypes...")
        _create_batch(SoftwareImageFileFactory, 5)
        self.stdout.write("Creating CircuitTypes...")
        _create_batch(CircuitTypeFactory, 40)
        self.stdout.write("Creating Providers...")
        _create_batch(ProviderFactory, 20)
        self.stdout.write("Creating ProviderNetworks...")
        _create_batch(ProviderNetworkFactory, 20)
        self.stdout.write("Creating Circuits...")
        _create_batch(CircuitFactory, 40)
        self.stdout.write("Creating Providers without Circuits...")
        _create_batch(ProviderFactory, 20)
        self.stdout.write("Creating CircuitTerminations...")
        _create_batch(CircuitTerminationFactory, 2, has_location=True, term_side="A")
        _create_batch(CircuitTerminationFactory, 2, has_location=True, term_side="Z")
        _create_batch(CircuitTerminationFactory, 2, has_location=False, term_side="A")
        _create_batch(CircuitTerminationFactory, 2, has_location=False, term_side="Z")
        _create_batch(CircuitTerminationFactory, 2, has_port_speed=True, has_upstream_speed=False)
        _create_batch(
            CircuitTerminationFactory,
            2,
            has_location=True,
            has_port_speed=True,
            has_upstream_speed=True,
            has_xconnect_id=True,
            has_pp_info=True,
            has_description=True,
        )
        self.stdout.write("Creating ExternalIntegrations...")
        _create_batch(ExternalIntegrationFactory, 20)
        self.stdout.write("Creating Controllers with Device or DeviceRedundancyGroups...")
        _create_batch(ControllerFactory, 10)
        _create_batch(ControllerManagedDeviceGroupFactory, 30)
        # make sure we have some tenants that have null relationships to make filter tests happy
        self.stdout.write("Creating Tenants without Circuits, Locations, IPAddresses, or Prefixes...")
        _create_batch(TenantFactory, 10)
        # TODO: nautobot.tenancy.tests.test_filters currently calls the following additional factories:
        # _create_batch(UserFactory, 10)
        # _create_batch(RackFactory, 10)
        # _create_batch(RackReservationFactory, 10)
        # _create_batch(ClusterTypeFactory, 10)
        # _create_batch(ClusterGroupFactory, 10)
        # _create_batch(ClusterFactory, 10)
        # _create_batch(VirtualMachineFactory, 10)
        # We need to remove them from there and enable them here instead, but that will require many test updates.

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
            self.stdout.write(self.style.WARNING(f"Loading factory data from file {options['fixture_file']}"))
            call_command("loaddata", "--database", options["database"], options["fixture_file"])
        else:
            self._generate_factory_data(options["seed"], options["database"])

            if options["cache_test_fixtures"]:
                self.stdout.write(self.style.WARNING(f"Saving factory data to file {options['fixture_file']}"))

                call_command(
                    "dumpdata",
                    indent=2,
                    format="json",
                    exclude=["auth.permission", "extras.job", "extras.customfield"],
                    output=options["fixture_file"],
                )

                self.stdout.write(self.style.SUCCESS(f"Dumped factory data to {options['fixture_file']}"))

        self.stdout.write(self.style.SUCCESS(f"Database {options['database']} populated successfully!"))
