from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS

from nautobot.extras.models import DynamicGroup


class Command(BaseCommand):
    help = "Update the member caches for all DynamicGroups."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help='The database to generate the test data in. Defaults to the "default" database.',
        )

    def handle(self, *args, **kwargs):
        """Run through all Dynamic Groups and ensure their member caches are up to date."""

        self.stdout.write(
            self.style.NOTICE(f"Refreshing DynamicGroup member caches in database {kwargs['database']}...")
        )

        dynamic_groups = DynamicGroup.objects.using(kwargs["database"]).all()

        for dynamic_group in dynamic_groups:
            try:
                dynamic_group.update_cached_members()
            except Exception as err:
                self.stderr.write(self.style.ERROR(f"Error while refreshing {dynamic_group}: {err}"))
