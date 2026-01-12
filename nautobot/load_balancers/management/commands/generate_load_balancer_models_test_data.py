"""Generate test data for the Load Balancer Models app."""

from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS

from nautobot.load_balancers import models
from nautobot.load_balancers.tests import generate_test_data


class Command(BaseCommand):
    """Populate the database with various data as a baseline for testing (automated or manual)."""

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help='The database to generate the test data in. Defaults to the "default" database.',
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Flush any existing load balancer models data from the database before generating new data.",
        )

    def handle(self, *args, **options):
        """Entry point to the management command."""
        if options["flush"]:
            self.stdout.write(self.style.WARNING("Flushing load balancer models objects from the database..."))
            models.LoadBalancerPoolMember.objects.using(options["database"]).all().delete()
            models.LoadBalancerPool.objects.using(options["database"]).all().delete()
            models.VirtualServer.objects.using(options["database"]).all().delete()
            models.HealthCheckMonitor.objects.using(options["database"]).all().delete()

        generate_test_data(db=options["database"])

        self.stdout.write(self.style.SUCCESS(f"Database {options['database']} populated with app data successfully!"))
