import argparse

from django.core.management import call_command
from django.core.management.base import BaseCommand


HELP_TEXT = """
Performs Nautobot common server upgrade operations using a single entrypoint.

This will run the following management commands with default settings, in order:

- migrate
- trace_paths
- collectstatic
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
            "--no-collectstatic",
            action="store_false",
            dest="collectstatic",
            default=True,
            help="Do not automatically collect static files into STATIC_ROOT.",
        )
        parser.add_argument(
            "--no-migrate",
            action="store_false",
            dest="migrate",
            default=True,
            help="Do not automatically perform any database migrations.",
        )
        parser.add_argument(
            "--no-trace-paths",
            action="store_false",
            dest="trace_paths",
            default=True,
            help="Do not automatically generate missing cable paths.",
        )

    def handle(self, **options):
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
