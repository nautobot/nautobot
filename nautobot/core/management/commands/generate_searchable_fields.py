"""Management command to (re)generate the committed `searchable_fields.yaml` source-of-truth artifact.

The generated YAML is rendered into the user-facing documentation (via `docs/macros.py`) so that the list of
fields searchable through each model's list-view search bar (the `q=` filter) stays in sync with the code
automatically. Run this command whenever a model's `SearchFilter` predicates change:

    nautobot-server generate_searchable_fields

Use `--check` in CI to verify the committed artifact is up to date without modifying it.
"""

from pathlib import Path

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand
import yaml

from nautobot.core.templatetags.helpers import bettertitle
from nautobot.core.utils.lookup import get_searchable_fields_for_model

# The committed artifact lives alongside settings.yaml in nautobot/core/.
SEARCHABLE_FIELDS_YAML = Path(__file__).resolve().parents[2] / "searchable_fields.yaml"


def collect_searchable_fields():
    """Introspect every model's FilterSet and return the fields searchable via its list-view search bar.

    A model is included only if its FilterSet exposes a `q` filter that is a `SearchFilter` instance (i.e. the
    model participates in list-view/global search). The searchable field names are read from the filter's
    `filter_predicates`, which is resolved at class-definition time and already reflects both inherited `q`
    filters (via the FilterSet metaclass) and the default predicates layered in by `SearchFilter` itself.

    Returns:
        (dict): Mapping of `app_label` to `{"app_name": <verbose name>, "models": [{"name": ..., "fields": [...]}]}`,
            with models and fields sorted for deterministic output.
    """
    by_app = {}
    for model in django_apps.get_models():
        app_config = django_apps.get_app_config(model._meta.app_label)
        # Only document Nautobot's own models. This excludes development-only example apps and keeps the
        # committed artifact stable regardless of which additional apps happen to be installed when it is
        # regenerated. Models from installed third-party apps are searchable per that app's own documentation.
        if not app_config.name.startswith("nautobot."):
            continue

        fields = get_searchable_fields_for_model(model)
        if not fields:
            continue

        app_label = model._meta.app_label
        entry = by_app.setdefault(
            app_label,
            {"app_name": str(app_config.verbose_name), "models": []},
        )
        entry["models"].append(
            {
                "name": bettertitle(str(model._meta.verbose_name)),
                "fields": fields,
            }
        )

    for entry in by_app.values():
        entry["models"].sort(key=lambda item: item["name"].lower())

    return by_app


def render_yaml(data):
    """Serialize the collected data to a stable YAML string (deterministic key ordering)."""
    return yaml.safe_dump(data, sort_keys=True, default_flow_style=False, allow_unicode=True)


class Command(BaseCommand):
    help = "Generate the searchable_fields.yaml documentation source-of-truth from the models' SearchFilters."

    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Do not write the file; exit with a non-zero status if the committed file is out of date.",
        )

    def handle(self, *args, **options):
        rendered = render_yaml(collect_searchable_fields())

        if options["check"]:
            current = SEARCHABLE_FIELDS_YAML.read_text() if SEARCHABLE_FIELDS_YAML.exists() else ""
            if current != rendered:
                self.stderr.write(
                    self.style.ERROR(
                        f"{SEARCHABLE_FIELDS_YAML} is out of date. "
                        "Run `nautobot-server generate_searchable_fields` and commit the result."
                    )
                )
                raise SystemExit(1)
            self.stdout.write(self.style.SUCCESS(f"{SEARCHABLE_FIELDS_YAML} is up to date."))
            return

        SEARCHABLE_FIELDS_YAML.write_text(rendered)
        self.stdout.write(self.style.SUCCESS(f"Wrote {SEARCHABLE_FIELDS_YAML}"))
