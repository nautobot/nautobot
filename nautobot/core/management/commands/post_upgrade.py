import argparse

from django.core.management import call_command
from django.core.management.base import BaseCommand


HELP_TEXT = """
Performs Nautobot common server upgrade operations using a single entrypoint.

This will run the following management commands with default settings, in order:

- migrate
- trace_paths
- collectstatic
- remove_stale_contenttypes
- clearsessions
- invalidate all
"""


class Command(BaseCommand):
    help = HELP_TEXT

    def create_parser(self, *args, **kwargs):
        """Custom parser that can display multiline help."""
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-clearsessions",
            action="store_false",
            dest="clearsessions",
            default=True,
            help="Do not automatically clean out expired sessions.",
        )
        parser.add_argument(
            "--no-collectstatic",
            action="store_false",
            dest="collectstatic",
            default=True,
            help="Do not automatically collect static files into a single location.",
        )
        parser.add_argument(
            "--no-invalidate-all",
            action="store_false",
            dest="invalidate_all",
            default=True,
            help="Do not automatically invalidate cache for entire application.",
        )
        parser.add_argument(
            "--no-migrate",
            action="store_false",
            dest="migrate",
            default=True,
            help="Do not automatically perform any database migrations.",
        )
        parser.add_argument(
            "--no-remove-stale-contenttypes",
            action="store_false",
            dest="remove_stale_contenttypes",
            default=True,
            help="Do not automatically remove stale content types.",
        )
        parser.add_argument(
            "--no-trace-paths",
            action="store_false",
            dest="trace_paths",
            default=True,
            help="Do not automatically generate missing cable paths.",
        )

    def handle(self, *args, **options):
        # Run migrate
        if options.get("migrate"):
            print("Performing database migrations...")
            call_command(
                "migrate",
                interactive=False,
                traceback=options["traceback"],
                verbosity=options["verbosity"],
            )
            print()

        # Run trace_paths
        if options.get("trace_paths"):
            print("Generating cable paths...")
            call_command("trace_paths", no_input=True)
            print()

        # Run collectstatic
        if options.get("collectstatic"):
            print("Collecting static files...")
            call_command("collectstatic", interactive=False)
            print()

        # Run remove_stale_contenttypes
        if options.get("remove_stale_contenttypes"):
            print("Removing stale content types...")
            call_command("remove_stale_contenttypes", interactive=False)
            print()

        # Run clearsessions
        if options.get("clearsessions"):
            print("Removing expired sessions...")
            call_command("clearsessions")
            print()

        # Run invalidate all
        if options.get("invalidate_all"):
            print("Invalidating cache...")
            call_command("invalidate", "all")
            print()
