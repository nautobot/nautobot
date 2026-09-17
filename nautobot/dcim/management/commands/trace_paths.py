from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from nautobot.circuits.models import CircuitTermination
from nautobot.dcim.models import (
    CablePath,
    CableType,
    ConsolePort,
    ConsoleServerPort,
    Interface,
    PowerFeed,
    PowerOutlet,
    PowerPort,
)
from nautobot.dcim.signals import create_cablepath

ENDPOINT_MODELS = (
    CircuitTermination,
    ConsolePort,
    ConsoleServerPort,
    Interface,
    PowerFeed,
    PowerOutlet,
    PowerPort,
)


def expected_path_counts_by_cable_type():
    """How many CablePaths each origin on a breakout cable should have, keyed by cable type.

    An origin on a breakout cable gets one CablePath per *distinct* opposite-side connector its own
    connector maps to via the cable type's lane mapping (see `create_cablepath`), whether or not
    each of those lanes is actually connected. A standard (non-breakout) cable always yields exactly
    one path per origin, so those cable types are omitted here and handled with a simple "has any
    path" check instead.

    Returns:
        dict: `{cable_type_pk: {(cable_end, connector): expected_distinct_peer_connector_count}}`,
            containing only breakout cable types.
    """
    counts = {}
    for cable_type in CableType.objects.all():
        if not cable_type.is_breakout:
            continue
        # (cable_end, connector) -> set of distinct connectors on the opposite end it maps to.
        peer_connectors = {}
        for entry in cable_type.mapping:
            peer_connectors.setdefault(("A", entry["a_connector"]), set()).add(entry["b_connector"])
            peer_connectors.setdefault(("B", entry["b_connector"]), set()).add(entry["a_connector"])
        counts[cable_type.pk] = {key: len(value) for key, value in peer_connectors.items()}
    return counts


class Command(BaseCommand):
    help = "Generate any missing cable paths among all cable termination objects in Nautobot"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            help="Force recalculation of all existing cable paths",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            dest="no_input",
            help="Do not prompt user for any input/confirmation",
        )

    def draw_progress_bar(self, percentage):
        """
        Draw a simple progress bar 20 increments wide illustrating the specified percentage.
        """
        bar_size = int(percentage / 5)
        self.stdout.write(f"\r  [{'#' * bar_size}{' ' * (20 - bar_size)}] {int(percentage)}%", ending="")

    def handle(self, *model_names, **options):
        # If --force was passed, first delete all existing CablePaths
        if options["force"]:
            cable_paths = CablePath.objects.all()
            paths_count = cable_paths.count()

            # Prompt the user to confirm recalculation of all paths
            if paths_count:
                self.stdout.write(self.style.ERROR("WARNING: Forcing recalculation of all cable paths."))
                if not options["no_input"]:
                    self.stdout.write(
                        f"This will delete and recalculate all {paths_count} existing cable paths. Are you sure?"
                    )
                    confirmation = input("Type yes to confirm: ")
                    if confirmation != "yes":
                        self.stdout.write(self.style.SUCCESS("Aborting"))
                        return

                # Delete all existing CablePath instances
                self.stdout.write(f"Deleting {paths_count} existing cable paths...")
                deleted_count, _ = CablePath.objects.all().delete()
                self.stdout.write((self.style.SUCCESS(f"  Deleted {deleted_count} paths")))

        if not options["force"]:
            # Precompute the expected path count per breakout cable type so the non-force filter below
            # can skip fully-traced breakout origins as well as fully-traced standard ones.
            expected_breakout_counts = expected_path_counts_by_cable_type()

        # Retrace paths
        for model in ENDPOINT_MODELS:
            origins = model.objects.filter(cable_termination__isnull=False)
            if not options["force"]:
                # Only retrace origins that are actually missing one or more paths.
                #
                # Compare each origin's existing path count against how many it *should* have. A
                # standard cable expects exactly one path, so any origin with zero paths needs
                # retracing. A breakout origin expects one path per fan-out lane (per its cable
                # type's mapping), so it needs retracing whenever it has fewer than that — this is
                # what catches a breakout that's only *partially* traced. Fully-traced origins of
                # either kind are skipped.
                origins = origins.annotate(num_paths=Count("cable_paths", distinct=True))
                needs_retrace = Q(num_paths=0)
                for cable_type_pk, expected_by_key in expected_breakout_counts.items():
                    for (cable_end, connector), expected in expected_by_key.items():
                        needs_retrace |= Q(
                            cable_termination__cable__cable_type=cable_type_pk,
                            cable_termination__cable_end=cable_end,
                            cable_termination__connector=connector,
                            num_paths__lt=expected,
                        )
                origins = origins.filter(needs_retrace)
            origins_count = origins.count()
            if not origins_count:
                self.stdout.write(f"Found no missing {model._meta.verbose_name} paths; skipping")
                continue
            self.stdout.write(f"Retracing {origins_count} cabled {model._meta.verbose_name_plural}...")
            i = 0
            skipped = 0
            for i, obj in enumerate(origins, start=1):
                try:
                    create_cablepath(obj, rebuild=False)
                except ValidationError as exc:
                    # Inconsistent existing data (e.g. a cabling loop committed without being traced,
                    # as can happen via loaddata) makes this origin impossible to trace. Skip it so a
                    # single bad origin doesn't abort retracing of everything else; a normal cable
                    # save still surfaces the same error to reject creating such a loop.
                    skipped += 1
                    reason = exc.messages[0] if exc.messages else str(exc)
                    self.stderr.write(self.style.WARNING(f"  Skipping {model._meta.verbose_name} {obj}: {reason}"))
                if not i % 100:
                    self.draw_progress_bar(i * 100 / origins_count)
            self.draw_progress_bar(100)
            self.stdout.write(self.style.SUCCESS(f"\n  Retraced {i - skipped} {model._meta.verbose_name_plural}"))
            if skipped:
                self.stdout.write(
                    self.style.WARNING(f"  Skipped {skipped} {model._meta.verbose_name_plural} with inconsistent data")
                )

        self.stdout.write(self.style.SUCCESS("Finished."))
