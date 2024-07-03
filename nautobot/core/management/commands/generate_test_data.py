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
            "--print-hashes",
            action="store_true",
            help=(
                "After creating each batch of records, print a hash of the list of all IDs of all objects of "
                "the given type. This is useful for identifying any problems with factory randomness / determinism; "
                "in general, successive runs with the same seed should output identical hashes for each stage, "
                "while successive runs with differing seeds should output different hashes. "
                "Setting environment variable GITHUB_ACTIONS to true is equivalent to specifying this argument."
            ),
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

    def _generate_factory_data(self, seed, db_name, print_hashes=False):
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

        def _create_batch(some_factory, count, description="", **kwargs):
            model = some_factory._meta.get_model_class()
            if description:
                description = " " + description
            message = f"Creating {count} {model._meta.verbose_name_plural}{description}..."
            self.stdout.write(message)
            records = some_factory.create_batch(count, using=db_name, **kwargs)
            if print_hashes:
                model_ids = [record.id for record in records]
                sha256_hash = hashlib.sha256(json.dumps(model_ids, cls=DjangoJSONEncoder).encode()).hexdigest()
                self.stdout.write(f"  SHA256: {sha256_hash}")

        populate_role_choices(verbosity=0, using=db_name)
        _create_batch(RoleFactory, 20)
        populate_status_choices(verbosity=0, using=db_name)
        _create_batch(StatusFactory, 10)
        # Ensure that we have some tags that are applicable to all relevant content-types
        _create_batch(
            TagFactory, 5, description="on all content-types", content_types=TaggableClassesQuery().as_queryset()
        )
        # ...and some tags that apply to a random subset of content-types
        _create_batch(TagFactory, 15, description="on some content-types")
        _create_batch(ContactFactory, 20)
        _create_batch(TeamFactory, 20)
        _create_batch(TenantGroupFactory, 10, description="without parents", has_parent=False)
        _create_batch(TenantGroupFactory, 10, description="with parents", has_parent=True)
        _create_batch(TenantFactory, 10, description="without a parent group", has_tenant_group=False)
        _create_batch(TenantFactory, 10, description="with a parent group", has_tenant_group=True)
        _create_batch(LocationTypeFactory, 7)  # only 7 unique LocationTypes are hard-coded presently
        # First 7 locations must be created in specific order so subsequent objects have valid parents to reference
        _create_batch(LocationFactory, 7, description="as structure", has_parent=True)
        _create_batch(LocationFactory, 40)
        _create_batch(LocationFactory, 10, description="without a parent Location", has_parent=False)
        _create_batch(ControllerFactory, 1, description="without a Device or DeviceRedundancyGroup")
        _create_batch(ControllerManagedDeviceGroupFactory, 5, description="to contain Devices")
        _create_batch(RIRFactory, 9)  # only 9 unique RIR names are hard-coded presently
        _create_batch(RouteTargetFactory, 20)
        _create_batch(NamespaceFactory, 10)
        _create_batch(VRFFactory, 20)
        _create_batch(VLANGroupFactory, 20)
        _create_batch(VLANFactory, 20)
        for i in range(30):
            _create_batch(
                PrefixFactory,
                1,
                description=f"(10.{i}.0.0/16 and descendants)",
                prefix=f"10.{i}.0.0/16",
                type=PrefixTypeChoices.TYPE_CONTAINER,
            )
            _create_batch(
                PrefixFactory,
                1,
                description=f"(2001:db8:0:{i}::/64 and descendants)",
                prefix=f"2001:db8:0:{i}::/64",
                type=PrefixTypeChoices.TYPE_CONTAINER,
            )
        _create_batch(NamespaceFactory, 5, description="without any Prefixes or IPAddresses")
        _create_batch(DeviceFamilyFactory, 20)
        _create_batch(ManufacturerFactory, 8)  # First 8 hard-coded Manufacturers
        _create_batch(PlatformFactory, 20, description="with Manufacturers", has_manufacturer=True)
        _create_batch(PlatformFactory, 5, description="without Manufacturers", has_manufacturer=False)
        _create_batch(SoftwareVersionFactory, 20, description="to be usable by Devices")
        _create_batch(SoftwareImageFileFactory, 25, description="to be usable by DeviceTypes")
        _create_batch(ManufacturerFactory, 4, description="without Platforms")  # 4 more hard-coded Manufacturers
        _create_batch(DeviceTypeFactory, 30)
        _create_batch(ManufacturerFactory, 2, description="without Platforms or DeviceTypes")  # Last 2 hard-coded
        _create_batch(DeviceRedundancyGroupFactory, 20)
        _create_batch(DeviceFactory, 20)
        _create_batch(SoftwareVersionFactory, 5, description="without Devices")
        _create_batch(SoftwareImageFileFactory, 5, description="without DeviceTypes")
        _create_batch(CircuitTypeFactory, 40)
        _create_batch(ProviderFactory, 20, description="to be usable by Circuits")
        _create_batch(ProviderNetworkFactory, 20)
        _create_batch(CircuitFactory, 40)
        _create_batch(ProviderFactory, 20, description="without Circuits")
        # TODO do we really need all of these specifics for CircuitTerminations?
        _create_batch(
            CircuitTerminationFactory, 2, description="with a location, for side A", has_location=True, term_side="A"
        )
        _create_batch(
            CircuitTerminationFactory, 2, description="with a location, for side Z", has_location=True, term_side="Z"
        )
        _create_batch(
            CircuitTerminationFactory,
            2,
            description="without a location, for side A",
            has_location=False,
            term_side="A",
        )
        _create_batch(
            CircuitTerminationFactory,
            2,
            description="without a location, for side Z",
            has_location=False,
            term_side="Z",
        )
        _create_batch(
            CircuitTerminationFactory,
            2,
            description="with port_speed but without upstream_speed",
            has_port_speed=True,
            has_upstream_speed=False,
        )
        _create_batch(
            CircuitTerminationFactory,
            2,
            description="with a location, port_speed, upstream_speed, xconnect_id, pp_info, and description",
            has_location=True,
            has_port_speed=True,
            has_upstream_speed=True,
            has_xconnect_id=True,
            has_pp_info=True,
            has_description=True,
        )
        _create_batch(ExternalIntegrationFactory, 20)
        _create_batch(ControllerFactory, 10, description="with Devices or DeviceRedundancyGroups")
        _create_batch(ControllerManagedDeviceGroupFactory, 5, description="without any Devices")
        # make sure we have some tenants that have null relationships to make filter tests happy
        _create_batch(TenantFactory, 10, description="without any associated objects")
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
            print_hashes = options["print_hashes"]
            if is_truthy(os.environ.get("GITHUB_ACTIONS", "false")):
                print_hashes = True
            self._generate_factory_data(options["seed"], options["database"], print_hashes=print_hashes)

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
