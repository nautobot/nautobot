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
- send_installation_metrics
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
        parser.add_argument(
            "--no-send-installation-metrics",
            action="store_false",
            dest="send_installation_metrics",
            default=True,
            help="Do not automatically send installation metrics.",
        )
        parser.add_argument(
            "--no-refresh-content-type-cache",
            action="store_false",
            dest="refresh_content_type_cache",
            default=True,
            help="Do not automatically refresh content type cache.",
        )
        parser.add_argument(
            "--no-refresh-dynamic-group-member-caches",
            action="store_false",
            dest="refresh_dynamic_group_member_caches",
            default=True,
            help="Do not automatically refresh dynamic group member caches.",
        )

    def handle(self, *args, **options):
        # Run migrate
        if options.get("migrate"):
            self.stdout.write("Performing database migrations...")
            call_command(
                "migrate",
                skip_checks=False,  # make sure Postgres version check and others are applied
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

        # Send installation metrics
        if options.get("send_installation_metrics"):
            self.stdout.write("Sending installation metrics...")
            call_command("send_installation_metrics")
            self.stdout.write()
        else:
            self.stdout.write("--no-send-installation-metrics was specified; skipping installation metrics.")
            self.stdout.write()

        # Run refresh_content_type_cache
        if options.get("remove_stale_contenttypes") or options.get("refresh_content_type_cache"):
            self.stdout.write("Refreshing _content_type cache")
            call_command("refresh_content_type_cache")
            self.stdout.write()

        # Run refresh_dynamic_group_member_caches
        if options.get("refresh_dynamic_group_member_caches"):
            self.stdout.write("Refreshing dynamic group member caches...")
            call_command("refresh_dynamic_group_member_caches")
            self.stdout.write()
