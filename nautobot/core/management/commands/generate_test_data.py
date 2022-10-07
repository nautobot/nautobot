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

    def handle(self, *args, **options):
        try:
            import factory.random

            from nautobot.extras.factory import TagFactory
            from nautobot.extras.management import populate_status_choices
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

        seed = options["seed"] or get_random_string(16)
        self.stdout.write(f'Seeding the pseudo-random number generator with seed "{seed}"...')
        factory.random.reseed_random(seed)

        self.stdout.write("Creating Statuses...")
        populate_status_choices(verbosity=0)  # for now just the basic ones; we should add a factory for random ones too
        self.stdout.write("Creating Tags...")
        # Ensure that we have some tags that are applicable to all relevant content-types
        TagFactory.create_batch(5, content_types=TaggableClassesQuery().as_queryset)
        # ...and some tags that apply to a random subset of content-types
        TagFactory.create_batch(15)
        self.stdout.write("Creating TenantGroups...")
        TenantGroupFactory.create_batch(10, has_parent=False)
        TenantGroupFactory.create_batch(10, has_parent=True)
        self.stdout.write("Creating Tenants...")
        TenantFactory.create_batch(10, has_group=False)
        TenantFactory.create_batch(10, has_group=True)
        self.stdout.write("Creating RIRs...")
        RIRFactory.create_batch(9)  # only 9 unique RIR names are hard-coded presently
        self.stdout.write("Creating Aggregates...")
        AggregateFactory.create_batch(20)
        self.stdout.write("Creating RouteTargets...")
        RouteTargetFactory.create_batch(20)
        self.stdout.write("Creating VRFs...")
        VRFFactory.create_batch(20)
        self.stdout.write("Creating IP/VLAN Roles...")
        RoleFactory.create_batch(10)
        self.stdout.write("Creating VLANGroups...")
        VLANGroupFactory.create_batch(20)
        self.stdout.write("Creating VLANs...")
        VLANFactory.create_batch(20)

        self.stdout.write(self.style.SUCCESS("Database populated successfully!"))
