"""Consolidated test suite for the Configurable Import / Export with Upsert feature.

Organized to match `test-matrix-import-export.md`. The pattern (mirroring
`extras.tests.test_customfields.CustomFieldBackgroundTasks`) is:

    setup a scenario  →  run the job via a helper  →  assert the outcome via helpers

`ImportExportJobTestCase` provides the cadence:

    run_export(**opts) / run_import(csv_data, **opts)   — run the system job, assert its status, return it
    export_text / export_lines / export_rows / export_document / export_filename(jr)  — read the produced file
    assertImport(jr, created=, updated=, unchanged=, match_fields=, source=)  — assert the upsert summary
    assertLog(jr, substr, level=) / assertNoLog(...) / assertNoIssues(jr)     — assert the job log

so each test reads as a few declarative lines.

Naming convention (see the doc):
    test_<layer>_<direction>__<field_type|format>[__<operation>]   # core / adapter / e2e layers
    test_<area>__<case>                                            # match / scope / select / error / perm / rest

Lower-level serializer/parser unit tests for CSV live in `test_csv.py` / `test_api.py`; the
management-command round-trip lives in `test_commands.py`.
"""

import csv
from io import StringIO
import json

from django.test import SimpleTestCase, tag
import yaml

from nautobot.core.api.constants import IMPORT_DOCUMENT_VERSION
from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.api.utils import build_import_document, build_import_metadata, nest_flat_dict
from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_TYPE
from nautobot.core.jobs import ExportObjectList

# ===========================================================================
# Layer 1c — shared pure functions (format-agnostic core, no DB)
# ===========================================================================


@tag("unit")
class NestFlatDictTests(SimpleTestCase):
    """`nest_flat_dict` converts flat `a__b` keys to nested dicts (used by both export and import)."""

    def test_core_nest__flat_to_nested(self):
        result = nest_flat_dict({"name": "iface", "device__name": "dev", "device__tenant__name": "ten"})
        self.assertEqual(result, {"name": "iface", "device": {"name": "dev", "tenant": {"name": "ten"}}})

    def test_core_nest__nested_passthrough(self):
        self.assertEqual(nest_flat_dict({"name": "x", "color": "111111"}), {"name": "x", "color": "111111"})

    def test_core_nest__sentinels(self):
        result = nest_flat_dict(
            {"tenant__name": CSV_NO_OBJECT, "asset_tag": CSV_NULL_TYPE},
            null_sentinels=(CSV_NO_OBJECT, CSV_NULL_TYPE),
        )
        self.assertIsNone(result["tenant"]["name"])
        self.assertIsNone(result["asset_tag"])

    def test_core_nest__list_value_preserved(self):
        self.assertEqual(nest_flat_dict({"tags": ["a", "b"]}), {"tags": ["a", "b"]})


@tag("unit")
class PruneMissingReferencesTests(SimpleTestCase):
    """`_prune_missing_references` must collapse only genuinely-null relations.

    `CSV_NO_OBJECT` means "there is no related object at this hop"; `CSV_NULL_TYPE` means "the object
    exists, this one field of it is null". Only the former is a null reference.
    """

    def _reshape(self, flat_record):
        """The `_build_document_records` nest-then-prune step, in isolation."""
        null_prefixes = ExportObjectList._null_reference_prefixes(flat_record)
        nested = nest_flat_dict(flat_record, (CSV_NO_OBJECT,))
        for head in {key.split("__", 1)[0] for key in flat_record if "__" in key}:
            nested[head] = ExportObjectList._prune_missing_references(null_prefixes, head, nested.get(head))
        return nested

    def test_core_prune__null_relation(self):
        self.assertEqual(self._reshape({"tenant__name": CSV_NO_OBJECT}), {"tenant": None})

    def test_core_prune__null_nested_reference_kept(self):
        """A location that exists but has no parent keeps the location and nulls only the parent."""
        self.assertEqual(
            self._reshape({"location__name": "Campus", "location__parent__name": CSV_NO_OBJECT}),
            {"location": {"name": "Campus", "parent": None}},
        )

    def test_core_prune__nested_sentinel_does_not_null_its_parent(self):
        """A sentinel at `location__parent__name` reports `location__parent` as null, not `location`.

        Reachable when a field selection names only a nested path (`export_fields=["location__parent__name"]`),
        which today drops the relation's own natural-key lookups.
        """
        self.assertEqual(
            self._reshape({"location__parent__name": CSV_NO_OBJECT}),
            {"location": {"parent": None}},
        )

    def test_core_prune__all_null_field_values_kept(self):
        """A null for every selected field does not mean the related object is absent."""
        self.assertEqual(
            self._reshape({"location__description": None}),
            {"location": {"description": None}},
        )

    def test_core_prune__literal_null_string_survives(self):
        """`CSV_NULL_TYPE` is a CSV-only spelling; in a document it is just an ordinary string value."""
        self.assertEqual(
            self._reshape({"location__description": CSV_NULL_TYPE}),
            {"location": {"description": CSV_NULL_TYPE}},
        )

    def test_core_prune__empty_string_not_a_null_reference(self):
        self.assertEqual(self._reshape({"location__name": ""}), {"location": {"name": ""}})

    def test_core_prune__deeply_nested_reference(self):
        self.assertEqual(
            self._reshape(
                {
                    "location__name": "Campus",
                    "location__parent__name": "Region",
                    "location__parent__parent__name": CSV_NO_OBJECT,
                }
            ),
            {"location": {"name": "Campus", "parent": {"name": "Region", "parent": None}}},
        )

    def test_core_prune__relation_itself_null_collapses_at_head(self):
        """A null relation sentinels its own natural key too, which is what nulls the head."""
        self.assertEqual(
            self._reshape({"location__name": CSV_NO_OBJECT, "location__parent__name": CSV_NO_OBJECT}),
            {"location": None},
        )

    def test_core_prune__composite_natural_key_relation_null(self):
        self.assertEqual(
            self._reshape({"device_type__model": CSV_NO_OBJECT, "device_type__manufacturer__name": CSV_NO_OBJECT}),
            {"device_type": None},
        )

    def test_core_prune__composite_natural_key_relation_present(self):
        self.assertEqual(
            self._reshape({"device_type__model": "C9300", "device_type__manufacturer__name": "Cisco"}),
            {"device_type": {"model": "C9300", "manufacturer": {"name": "Cisco"}}},
        )


@tag("unit")
class ImportMetadataTests(SimpleTestCase):
    """`build_import_metadata` is the single source of the self-describing metadata both formats stamp."""

    def test_core_metadata__version_is_an_integer(self):
        """The version is the integer 3, not a string; readers compare numerically."""
        self.assertIsInstance(IMPORT_DOCUMENT_VERSION, int)
        self.assertEqual(IMPORT_DOCUMENT_VERSION, 3)

    def test_core_metadata__keys_and_order(self):
        metadata = build_import_metadata("dcim.manufacturer", match_fields=["name"])
        self.assertEqual(list(metadata.keys()), ["nautobot_import_version", "model", "match_fields"])
        self.assertEqual(metadata["nautobot_import_version"], IMPORT_DOCUMENT_VERSION)
        self.assertEqual(metadata["model"], "dcim.manufacturer")
        self.assertEqual(metadata["match_fields"], ["name"])

    def test_core_metadata__omits_empty_match_fields(self):
        self.assertEqual(
            build_import_metadata("dcim.manufacturer"),
            {"nautobot_import_version": IMPORT_DOCUMENT_VERSION, "model": "dcim.manufacturer"},
        )

    def test_core_document__is_metadata_plus_records(self):
        """The JSON/YAML document is the shared metadata with `records` appended last."""
        records = [{"name": "Cisco"}]
        document = build_import_document("dcim.manufacturer", records, match_fields=["name"])
        self.assertEqual(list(document.keys()), ["nautobot_import_version", "model", "match_fields", "records"])
        self.assertEqual(document["records"], records)
        metadata = build_import_metadata("dcim.manufacturer", match_fields=["name"])
        self.assertEqual({key: document[key] for key in metadata}, metadata)

    def test_core_document__json_renders_version_unquoted(self):
        document = build_import_document("dcim.manufacturer", [{"name": "Cisco"}])
        self.assertIn('"nautobot_import_version": 3', json.dumps(document, indent=2, default=str))

    def test_core_document__yaml_renders_version_unquoted(self):
        document = build_import_document("dcim.manufacturer", [{"name": "Cisco"}])
        self.assertIn("nautobot_import_version: 3\n", yaml.safe_dump(document, sort_keys=False))


@tag("unit")
class DirectiveRowTests(SimpleTestCase):
    """The CSV counterpart of the document metadata: a leading `# key=value; ...` comment row."""

    def _first_line(self, match_fields=None):
        rendered = NautobotCSVRenderer().render(
            [{"name": "Cisco", "description": "x"}],
            renderer_context={"import_directives": build_import_metadata("dcim.manufacturer", match_fields)},
        )
        return rendered.splitlines()[0]

    def test_core_directive__row_contents(self):
        self.assertEqual(
            self._first_line(match_fields=["name"]),
            "# nautobot_import_version=3; model=dcim.manufacturer; match_fields=name",
        )

    def test_core_directive__written_even_without_match_fields(self):
        """Version and model are always present, so the row is never suppressed."""
        self.assertEqual(self._first_line(), "# nautobot_import_version=3; model=dcim.manufacturer")

    def test_core_directive__list_values_are_space_joined(self):
        line = self._first_line(match_fields=["name", "serial"])
        self.assertEqual(line, "# nautobot_import_version=3; model=dcim.manufacturer; match_fields=name serial")

    def test_core_directive__occupies_a_single_cell(self):
        """A one-cell directive survives a spreadsheet open-edit-save cycle; see render_directive_row."""
        rendered = NautobotCSVRenderer().render(
            [{"name": "Cisco"}],
            renderer_context={"import_directives": build_import_metadata("dcim.manufacturer", ["name", "serial"])},
        )
        self.assertEqual(len(next(csv.reader(StringIO(rendered)))), 1)

    def test_core_directive__no_legacy_marker(self):
        """The version directive is the marker; the old `nautobot-import:` prefix is gone."""
        self.assertNotIn("nautobot-import", self._first_line(match_fields=["name"]))

    def test_core_directive__precedes_the_header_row(self):
        rendered = NautobotCSVRenderer().render(
            [{"name": "Cisco", "description": "x"}],
            renderer_context={"import_directives": build_import_metadata("dcim.manufacturer", ["name"])},
        )
        lines = rendered.splitlines()
        self.assertTrue(lines[0].startswith("#"), lines[0])
        self.assertEqual(lines[1], "name,description")
