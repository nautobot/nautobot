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
from pathlib import Path
from unittest import skip

from django.contrib.contenttypes.models import ContentType
from django.test import SimpleTestCase
import yaml

from nautobot.core.api.constants import IMPORT_DOCUMENT_VERSION
from nautobot.core.api.utils import nest_flat_dict
from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_TYPE
from nautobot.core.jobs import ExportObjectList
from nautobot.core.testing import create_job_result_and_run_job, TransactionTestCase
from nautobot.dcim.models import Device, DeviceType, Manufacturer
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models import ExportTemplate, JobLogEntry, SavedView, Status

# ===========================================================================
# Layer 1c — shared pure functions (format-agnostic core, no DB)
# ===========================================================================


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


class ImportExportJobTestCase(TransactionTestCase):
    """Shared fixtures + the setup→run→assert cadence for the ExportObjectList / ImportObjects jobs."""

    databases = ("default", "job_logs")

    csv_data = "\n".join(
        [
            "name,color,content_types",
            "test_status1,111111,dcim.device",
            'test_status2,222222,"dcim.device,dcim.location"',
            "test_status3,333333,dcim.device",
            "test_status4,444444,dcim.device",
        ]
    )

    # -- scenario setup --------------------------------------------------------
    def create_status(self, name="test_update_status", color="111111"):
        status = Status.objects.create(name=name, color=color)
        status.content_types.set([ContentType.objects.get_for_model(Device)])
        return status

    def create_saved_view(self, model_class=Status, config=None):
        return SavedView.objects.create(
            name="Global default View",
            owner=self.user,
            view=f"{model_class._meta.app_label}:{model_class._meta.model_name}_list",
            is_global_default=True,
            config=config or {},
        )

    # -- run the jobs ----------------------------------------------------------
    def run_export(self, *, model=Status, expected_status=JobResultStatusChoices.STATUS_SUCCESS, **kwargs):
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            content_type=ContentType.objects.get_for_model(model).pk,
            **kwargs,
        )
        self.assertJobResultStatus(job_result, expected_status)
        return job_result

    def run_import(
        self, csv_data=None, *, model=Status, expected_status=JobResultStatusChoices.STATUS_SUCCESS, **kwargs
    ):
        if csv_data is not None:
            kwargs["csv_data"] = csv_data
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            content_type=ContentType.objects.get_for_model(model).pk,
            **kwargs,
        )
        self.assertJobResultStatus(job_result, expected_status)
        return job_result

    # -- read the produced export file ----------------------------------------
    def export_filename(self, job_result):
        return Path(job_result.files.first().file.name).name

    def _export_bytes(self, job_result):
        with job_result.files.first().file.open("rb") as fh:
            return fh.read()

    def export_text(self, job_result):
        return self._export_bytes(job_result).decode("utf-8").lstrip("﻿")

    def export_lines(self, job_result):
        return self.export_text(job_result).splitlines()

    def export_rows(self, job_result):
        """Parsed CSV data rows (directive/comment lines skipped)."""
        lines = [line for line in self.export_lines(job_result) if not line.startswith("#")]
        return list(csv.DictReader(StringIO("\n".join(lines))))

    def export_document(self, job_result):
        """The JSON or YAML export parsed into Python (chosen by file extension)."""
        text = self._export_bytes(job_result).decode("utf-8")
        return json.loads(text) if self.export_filename(job_result).endswith(".json") else yaml.safe_load(text)

    # -- assert the outcome ----------------------------------------------------
    def assertImport(self, job_result, *, created=None, updated=None, unchanged=None, match_fields=None, source=None):
        """Assert the upsert summary counters/metadata on the JobResult.result."""
        for key, expected in (
            ("created", created),
            ("updated", updated),
            ("unchanged", unchanged),
            ("effective_match_fields", match_fields),
            ("match_fields_source", source),
        ):
            if expected is not None:
                self.assertEqual(job_result.result[key], expected, key)

    def assertLog(self, job_result, contains, *, level=None):
        qs = JobLogEntry.objects.filter(job_result=job_result, message__icontains=contains)
        if level is not None:
            qs = qs.filter(log_level=level)
        self.assertTrue(qs.exists(), f"Expected a {level or 'any'}-level log line containing {contains!r}")

    def assertNoLog(self, job_result, contains, *, level=None):
        qs = JobLogEntry.objects.filter(job_result=job_result, message__icontains=contains)
        if level is not None:
            qs = qs.filter(log_level=level)
        self.assertFalse(qs.exists(), f"Unexpected {level or 'any'}-level log line containing {contains!r}")

    def assertNoIssues(self, job_result):
        self.assertFalse(
            JobLogEntry.objects.filter(
                job_result=job_result, log_level__in=[LogLevelChoices.LOG_WARNING, LogLevelChoices.LOG_ERROR]
            ).exists()
        )


# ===========================================================================
# Layer 2 — export format adapters
# ===========================================================================
class ExportAdapterTests(ImportExportJobTestCase):
    def test_adapter_export__all_csv(self):
        """By default, the job exports all instances to CSV."""
        job_result = self.run_export()
        self.assertEqual(self.export_filename(job_result), "nautobot_statuses.csv")
        self.assertGreaterEqual(len(self.export_lines(job_result)), Status.objects.count() + 1)

    def test_adapter_export__json_nested(self):
        """JSON export wraps records in the metadata document, with related fields nested under their parent key."""
        mfr = Manufacturer.objects.create(name="Document Mfr")
        DeviceType.objects.create(manufacturer=mfr, model="Document DT", u_height=1)
        doc = self.export_document(
            self.run_export(model=DeviceType, query_string="model=Document+DT", export_format="json")
        )
        self.assertEqual(doc["nautobot_import_version"], IMPORT_DOCUMENT_VERSION)
        self.assertEqual(doc["model"], "dcim.devicetype")
        self.assertIn("match_fields", doc)
        self.assertEqual(len(doc["records"]), 1)
        self.assertEqual(doc["records"][0]["model"], "Document DT")
        self.assertEqual(doc["records"][0]["manufacturer"], {"name": "Document Mfr"})  # nested, not flattened
        self.assertNotIn("url", doc["records"][0])

    @skip("Enable in X4: uses use_current_view (sort + saved-view export config)")
    def test_adapter_export__generic_yaml(self):
        """A model without to_yaml() exports to YAML as a document rather than erroring."""
        status = Status.objects.create(name="test_yaml_export_status", color="112233")
        status.content_types.set([ContentType.objects.get_for_model(Device)])
        doc = self.export_document(
            self.run_export(query_string="name=test_yaml_export_status", export_format="yaml", use_current_view=True)
        )
        self.assertEqual(doc["model"], "extras.status")
        self.assertEqual(doc["match_fields"], ["name"])
        self.assertEqual(len(doc["records"]), 1)
        self.assertEqual(doc["records"][0]["name"], "test_yaml_export_status")
        self.assertEqual(doc["records"][0]["color"], "112233")

    def test_adapter_export__csv_stamps_directive(self):
        """CSV exports carry their own import instructions: the model's natural key as the match key."""
        self.assertEqual(
            self.export_lines(self.run_export())[0],
            f"# nautobot_import_version={IMPORT_DOCUMENT_VERSION}; model=extras.status; match_fields=name",
        )

    def test_adapter_export__via_export_template(self):
        """When an export-template is specified, it is used."""
        et = ExportTemplate.objects.create(
            content_type=ContentType.objects.get_for_model(Status),
            name="Simple Export Template",
            template_code="{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
            file_extension="txt",
        )
        job_result = self.run_export(export_template=et.pk)
        self.assertEqual(self.export_filename(job_result), "nautobot_statuses.txt")
        text = self.export_text(job_result)
        self.assertEqual(len(text.split("\n")), Status.objects.count() + 1)
        for status in Status.objects.iterator():
            self.assertIn(status.name, text)

    def test_adapter_export__devicetype_library_yaml(self):
        """Device-type YAML uses the devicetype-library format, not the generic document."""
        mfr = Manufacturer.objects.create(name="Cisco")
        DeviceType.objects.create(manufacturer=mfr, model="Cisco CSR1000v", u_height=0)
        job_result = self.run_export(model=DeviceType, export_format="yaml")
        self.assertEqual(self.export_filename(job_result), "nautobot_device_types.yaml")
        self.assertEqual(self.export_document(job_result)["manufacturer"], "Cisco")
