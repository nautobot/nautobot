import argparse

from django.core.management import call_command
from django.core.management.base import BaseCommand


HELP_TEXT = """
Performs Nautobot common server upgrade operations using a single entrypoint.

This will run the following management commands with default settings, in order:

- migrate
- trace_paths
- build_ui --npm-install
- collectstatic
- remove_stale_contenttypes
- clearsessions
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
            "--no-build-ui",
            action="store_false",
            dest="build_ui",
            default=True,
            help="Do not automatically build the user interface.",
        )
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
            self.stdout.write("Performing database migrations...")
            call_command(
                "migrate",
                interactive=False,
                traceback=options["traceback"],
                verbosity=options["verbosity"],
            )
            self.stdout.write()

        # Run trace_paths
        if options.get("trace_paths"):
            self.stdout.write("Generating cable paths...")
            call_command("trace_paths", no_input=True)
            self.stdout.write()

        # Run build
        if options.get("build_ui"):
            self.stdout.write("Building user interface...")
            call_command("build_ui", npm_install=True)
            self.stdout.write()

        # Run collectstatic
        if options.get("collectstatic"):
            self.stdout.write("Collecting static files...")
            call_command("collectstatic", interactive=False)
            self.stdout.write()

        # Run remove_stale_contenttypes
        if options.get("remove_stale_contenttypes"):
            self.stdout.write("Removing stale content types...")
            call_command("remove_stale_contenttypes", interactive=False)
            self.stdout.write()

        # Run clearsessions
        if options.get("clearsessions"):
            self.stdout.write("Removing expired sessions...")
            call_command("clearsessions")
            self.stdout.write()
