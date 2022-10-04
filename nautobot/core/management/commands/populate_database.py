from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
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

    def handle(self, *args, **options):
        try:
            import factory.random

            from nautobot.extras.management import populate_status_choices
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
            self.stdout.write(self.style.WARNING("Flushing all existing data from the database..."))
            call_command("flush", "--no-input")

        seed = options["seed"] or get_random_string(16)
        self.stdout.write(f'Seeding the pseudo-random number generator with seed "{seed}"...')
        factory.random.reseed_random(seed)

        self.stdout.write("Creating Statuses...")
        populate_status_choices(verbosity=0)  # for now just the basic ones; we should add a factory for random ones too
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
