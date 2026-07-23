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

import codecs
import csv
from io import StringIO
import json
from pathlib import Path
from unittest import expectedFailure, skip

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from rest_framework.exceptions import ParseError
import yaml

from nautobot.core.api.constants import IMPORT_DOCUMENT_VERSION
from nautobot.core.api.parsers import ImportDocumentParserMixin
from nautobot.core.api.utils import build_import_document, nest_flat_dict
from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_SENTINELS, CSV_NULL_TYPE
from nautobot.core.jobs import ExportObjectList
from nautobot.core.jobs.import_utils import detect_import_format
from nautobot.core.testing import create_job_result_and_run_job, get_job_class_and_model, TransactionTestCase
from nautobot.dcim.api.serializers import DeviceSerializer
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models import (
    Contact,
    ContactAssociation,
    ExportTemplate,
    FileProxy,
    JobLogEntry,
    Role,
    SavedView,
    Status,
)
from nautobot.ipam.models import Prefix
from nautobot.users.models import ObjectPermission


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
        nested = nest_flat_dict(flat_record, CSV_NULL_SENTINELS)
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
        """CSV_NULL_TYPE for every selected field does not mean the related object is absent."""
        self.assertEqual(
            self._reshape({"location__description": CSV_NULL_TYPE}),
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


class ImportDocumentTests(SimpleTestCase):
    """`build_import_document` (writer) and `unwrap_document` (reader) share one wire format."""

    def test_core_document__build(self):
        doc = build_import_document("dcim.manufacturer", [{"name": "Cisco"}], match_fields=["name"])
        self.assertEqual(list(doc.keys()), ["nautobot_import", "model", "match_fields", "records"])
        self.assertEqual(doc["nautobot_import"], IMPORT_DOCUMENT_VERSION)
        self.assertEqual(doc["model"], "dcim.manufacturer")
        self.assertEqual(doc["match_fields"], ["name"])
        self.assertEqual(doc["records"], [{"name": "Cisco"}])

    def test_core_document__build_omits_empty_match_fields(self):
        self.assertNotIn("match_fields", build_import_document("dcim.manufacturer", [{"name": "Cisco"}]))

    def test_core_document__unwrap_envelope(self):
        doc = build_import_document("dcim.manufacturer", [{"name": "Cisco"}], match_fields=["name"])
        metadata, records = ImportDocumentParserMixin.unwrap_document(doc)
        self.assertEqual(metadata["model"], "dcim.manufacturer")
        self.assertEqual(metadata["match_fields"], ["name"])
        self.assertEqual(records, [{"name": "Cisco"}])

    def test_core_document__unwrap_bare_list(self):
        metadata, records = ImportDocumentParserMixin.unwrap_document([{"name": "Cisco"}])
        self.assertEqual(metadata, {})
        self.assertEqual(records, [{"name": "Cisco"}])

    def test_core_document__unwrap_bad_version(self):
        with self.assertRaises(ParseError):
            ImportDocumentParserMixin.unwrap_document({"nautobot_import": "999", "records": []})

    def test_core_document__unwrap_mapping_without_records(self):
        with self.assertRaises(ParseError):
            ImportDocumentParserMixin.unwrap_document({"model": "dcim.manufacturer"})

    def test_core_document__unwrap_records_not_a_list(self):
        with self.assertRaises(ParseError):
            ImportDocumentParserMixin.unwrap_document({"records": {"not": "a list"}})


class DetectImportFormatTests(SimpleTestCase):
    """`detect_import_format` sniffs by filename first, then content, else CSV."""

    def test_core_detect__by_extension(self):
        self.assertEqual(detect_import_format(filename="x.json"), "json")
        self.assertEqual(detect_import_format(filename="x.yaml"), "yaml")
        self.assertEqual(detect_import_format(filename="x.yml"), "yaml")
        self.assertEqual(detect_import_format(filename="x.csv"), "csv")

    def test_core_detect__by_content_json(self):
        self.assertEqual(detect_import_format(text='{"records": []}'), "json")
        self.assertEqual(detect_import_format(text="[{}]"), "json")

    def test_core_detect__by_content_yaml(self):
        self.assertEqual(detect_import_format(text="---\nname: x"), "yaml")
        self.assertEqual(detect_import_format(text="nautobot_import: '1'\nrecords: []"), "yaml")

    def test_core_detect__default_csv(self):
        self.assertEqual(detect_import_format(text="name,color\nx,111111"), "csv")
        self.assertEqual(detect_import_format(), "csv")


# ===========================================================================
# Shared base — the run/read/assert cadence for job-backed tests
# ===========================================================================
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
        self.assertEqual(doc["nautobot_import"], "1")
        self.assertEqual(doc["model"], "dcim.devicetype")
        self.assertIn("match_fields", doc)
        self.assertEqual(len(doc["records"]), 1)
        self.assertEqual(doc["records"][0]["model"], "Document DT")
        self.assertEqual(doc["records"][0]["manufacturer"], {"name": "Document Mfr"})  # nested, not flattened
        self.assertNotIn("url", doc["records"][0])

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
        self.assertEqual(self.export_lines(self.run_export())[0], "# nautobot-import: match_fields=name")

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


# ===========================================================================
# Export field selection
# ===========================================================================
class ExportFieldSelectionTests(ImportExportJobTestCase):
    def test_select__csv(self):
        """An explicit field selection yields exactly those columns, in selection order."""
        mfr = Manufacturer.objects.create(name="Selection Mfr")
        DeviceType.objects.create(manufacturer=mfr, model="Selection DT", u_height=1)
        lines = self.export_lines(
            self.run_export(
                model=DeviceType,
                query_string="model=Selection+DT",
                export_fields="model,manufacturer__name",
                use_current_view=True,
            )
        )
        self.assertTrue(lines[0].startswith("# nautobot-import: match_fields="), lines[0])
        self.assertEqual(lines[1], "model,manufacturer__name")
        self.assertEqual(lines[2], "Selection DT,Selection Mfr")

    def test_select__omits_directive_when_key_not_covered(self):
        """If the selection omits the natural key, the export is not stamped with a match directive."""
        Status.objects.create(name="test_selection_status", color="445566")
        lines = self.export_lines(
            self.run_export(query_string="name=test_selection_status", export_fields="color", use_current_view=True)
        )
        self.assertEqual(lines[0], "color")
        self.assertEqual(lines[1], "445566")

    def test_select__json(self):
        """Field selection applies to JSON document exports as well, with nested related fields."""
        mfr = Manufacturer.objects.create(name="Selection JSON Mfr")
        DeviceType.objects.create(manufacturer=mfr, model="Selection JSON DT", u_height=1)
        doc = self.export_document(
            self.run_export(
                model=DeviceType,
                query_string="model=Selection+JSON+DT",
                export_format="json",
                export_fields="model,manufacturer__name",
                use_current_view=True,
            )
        )
        self.assertEqual(
            doc["records"], [{"model": "Selection JSON DT", "manufacturer": {"name": "Selection JSON Mfr"}}]
        )

    def test_select__invalid(self):
        """An invalid field selection fails with a clear error naming the bad path."""
        job_result = self.run_export(
            export_fields="name,no_such_field", expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        self.assertLog(job_result, "no_such_field", level=LogLevelChoices.LOG_ERROR)

    def test_select__form_expands_single_fk_relations(self):
        """ExportFieldsForm offers a flat, orderable list including single-FK relations expanded one level."""
        from nautobot.core.forms import ExportFieldsForm

        form = ExportFieldsForm(content_type=ContentType.objects.get_for_model(Device), initial_fields=["name"])
        paths = [choice[0] for choice in form.fields["export_fields"].choices]
        self.assertIn("name", paths)
        self.assertIn("device_type__manufacturer", paths)
        self.assertIn("status__name", paths)
        self.assertFalse([path for path in paths if path.startswith("tags__")])
        self.assertEqual(form.fields["export_fields"].initial, ["name"])
        rendered = str(form["export_fields"].as_widget())
        self.assertIn("export-field-caret", rendered)
        self.assertIn("export-nested", rendered)
        self.assertIn('value="device_type__manufacturer"', rendered)

    def test_select__modal_renders_selector(self):
        """The ExportObjectList job form renders via the custom modal template with the orderable selector."""
        get_job_class_and_model("nautobot.core.jobs", "ExportObjectList")  # ensure the job model is enabled
        self.add_permissions("extras.run_job")
        response = self.client.post(
            reverse("extras:job_run_by_class_path", kwargs={"class_path": "nautobot.core.jobs.ExportObjectList"}),
            data={
                "render_job_form": True,
                "job_modal_button": "core.export_object_list",
                "content_type": ContentType.objects.get_for_model(Status).pk,
                "export_fields": "name,color",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertHttpStatus(response, 200)
        # Assert the template path explicitly: JobView._get_template_name falls back to the generic modal
        # (with only a message) if htmx_template_name can't be loaded, so a bad path degrades silently.
        self.assertTemplateUsed(response, "system_jobs/export_job_form_modal.html")
        content = response.content.decode(response.charset)
        self.assertIn("export-fields-selector", content)
        self.assertIn("nb-select-multiple-orderable-list", content)
        self.assertIn('value="name"', content)
        self.assertInHTML(
            '<input class="form-check-input my-6" id="id_export_selector-export_fields_option_name" '
            'name="export_selector-export_fields" type="checkbox" value="name" checked>',
            content,
        )


# ===========================================================================
# Export scope — "Use Current View" (filters + sort + saved views)
# ===========================================================================
class ExportScopeTests(ImportExportJobTestCase):
    def test_scope__ignores_saved_view_by_default(self):
        """A saved view's export settings apply only on explicit request, never implicitly."""
        Status.objects.create(name="test_saved_ignored_status", color="556677")
        saved_view = self.create_saved_view(config={"export_config": {"fields": ["color"], "format": "json"}})
        job_result = self.run_export(query_string=f"saved_view={saved_view.pk}&name=test_saved_ignored_status")
        self.assertTrue(self.export_filename(job_result).endswith(".csv"))
        header = next(line for line in self.export_lines(job_result) if not line.startswith("#"))
        self.assertIn("name", header.split(","))

    def test_scope__current_view_applies_sort(self):
        """Use Current View applies the current view's sort order to the export."""
        Status.objects.create(name="zzz_sort_a", color="111111")
        Status.objects.create(name="zzz_sort_b", color="222222")
        rows = self.export_rows(
            self.run_export(query_string="name=zzz_sort_a&name=zzz_sort_b&sort=-name", use_current_view=True)
        )
        self.assertEqual([row["name"] for row in rows], ["zzz_sort_b", "zzz_sort_a"])

    def test_scope__without_current_view_ignores_filters(self):
        """Without Use Current View, the export is a full export and the view's filters are ignored."""
        Status.objects.create(name="zzz_only_me", color="111111")
        names = [row["name"] for row in self.export_rows(self.run_export(query_string="name=zzz_only_me"))]
        self.assertIn("zzz_only_me", names)
        self.assertGreater(len(names), 1)

    def test_scope__uses_saved_view_export_config(self):
        """A saved view's export_config supplies the field selection and format when not explicitly given."""
        Status.objects.create(name="test_saved_export_status", color="667788")
        saved_view = self.create_saved_view(config={"export_config": {"fields": ["name", "color"], "format": "csv"}})
        lines = [
            line
            for line in self.export_lines(
                self.run_export(
                    query_string=f"saved_view={saved_view.pk}&name=test_saved_export_status", use_current_view=True
                )
            )
            if not line.startswith("#")
        ]
        self.assertEqual(lines[0], "name,color")
        self.assertEqual(lines[1], "test_saved_export_status,667788")

    def test_scope__saved_view_config_format(self):
        """A saved view's export_config format applies when no explicit format is given."""
        Status.objects.create(name="test_saved_json_status", color="778899")
        saved_view = self.create_saved_view(config={"export_config": {"fields": ["name", "color"], "format": "json"}})
        doc = self.export_document(
            self.run_export(
                query_string=f"saved_view={saved_view.pk}&name=test_saved_json_status", use_current_view=True
            )
        )
        self.assertEqual(doc["records"], [{"name": "test_saved_json_status", "color": "778899"}])

    def test_scope__explicit_fields_override_saved_view(self):
        """Explicit export_fields takes precedence over the saved view's export_config."""
        Status.objects.create(name="test_saved_override_status", color="8899aa")
        saved_view = self.create_saved_view(config={"export_config": {"fields": ["name", "color"]}})
        lines = self.export_lines(
            self.run_export(
                query_string=f"saved_view={saved_view.pk}&name=test_saved_override_status",
                use_current_view=True,
                export_fields="color",
            )
        )
        self.assertEqual(lines[0], "color")

    def test_scope__get_saved_view_filter_params(self):
        """Test various cases for the saved view filter parameters."""
        saved_view = self.create_saved_view(config={"filter_params": {"name": ["Active"]}})
        test_cases = [
            ({"saved_view": saved_view.pk}, {"name": ["Active"]}),
            (
                {"saved_view": saved_view.pk, "name": ["Active"], "content_types": ["dcim.devices"]},
                {"name": ["Active"]},
            ),
            ({"saved_view": saved_view.pk, "content_types": ["dcim.devices"]}, {}),
            ({"saved_view": saved_view.pk, "all_filters_removed": "true"}, {}),
            ({"name": ["Active"]}, {}),
        ]
        for query_params, expected_output in test_cases:
            with self.subTest(query_params=query_params, expected_output=expected_output):
                self.assertEqual(ExportObjectList()._get_saved_view_filter_params(query_params), expected_output)

    def test_scope__saved_view_to_csv_without_filters(self):
        sv = self.create_saved_view()
        rows = self.export_rows(self.run_export(query_string=f"saved_view={sv.pk}", use_current_view=True))
        self.assertEqual(len(rows), Status.objects.count())

    def test_scope__saved_view_to_csv_with_filters_from_saved_view(self):
        filter_name = Status.objects.first().name
        sv = self.create_saved_view(config={"filter_params": {"name": [filter_name]}})
        rows = self.export_rows(self.run_export(query_string=f"saved_view={sv.pk}", use_current_view=True))
        self.assertGreaterEqual(Status.objects.count(), 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], filter_name)

    def test_scope__saved_view_to_csv_with_combined_filters(self):
        filter_name = Status.objects.first().name
        filter_name2 = Status.objects.last().name
        sv = self.create_saved_view(config={"filter_params": {"name": [filter_name]}})
        rows = self.export_rows(
            self.run_export(
                query_string=f"saved_view={sv.pk}&name={filter_name}&name={filter_name2}", use_current_view=True
            )
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], filter_name)
        self.assertEqual(rows[1]["name"], filter_name2)

    def test_scope__saved_view_manufacturer_with_replaced_filters(self):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer")
        manufacturer2 = Manufacturer.objects.create(name="Test2 Manufacturer", description="test filter")
        sv = self.create_saved_view(model_class=Manufacturer, config={"filter_params": {"name": [manufacturer.name]}})
        rows = self.export_rows(
            self.run_export(
                model=Manufacturer,
                query_string=f"saved_view={sv.pk}&description={manufacturer2.description}",
                use_current_view=True,
            )
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], manufacturer2.name)
        self.assertEqual(rows[0]["description"], manufacturer2.description)
        self.assertTrue(all(row["name"] != manufacturer.name for row in rows))

    def test_scope__saved_view_to_csv_after_removing_all_filters(self):
        filter_name = Status.objects.first().name
        sv = self.create_saved_view(config={"filter_params": {"name": [filter_name]}})
        rows = self.export_rows(
            self.run_export(query_string=f"saved_view={sv.pk}&all_filters_removed=true", use_current_view=True)
        )
        self.assertEqual(len(rows), Status.objects.count())

    def test_scope__stale_saved_view(self):
        """A deleted/nonexistent saved_view reference falls back to a full export rather than erroring."""
        job_result = self.run_export(
            use_current_view=True, query_string="saved_view=00000000-0000-0000-0000-000000000000"
        )
        self.assertGreaterEqual(len(self.export_lines(job_result)), Status.objects.count() + 1)

    def test_scope__bad_sort_key(self):
        """A sort on a non-sortable key is ignored with a warning; the export still succeeds."""
        job_result = self.run_export(use_current_view=True, query_string="sort=not_a_real_field")
        self.assertTrue(job_result.files.exists())
        self.assertLog(job_result, "Ignoring sort", level=LogLevelChoices.LOG_WARNING)


# ===========================================================================
# Export result modal & download
# ===========================================================================
class ExportResultModalTests(ImportExportJobTestCase):
    def test_export_modal_button_get_redirect_button(self):
        """The registered export job-modal button offers a file download for a completed export, else nothing."""
        from nautobot.extras.registry import registry

        button = registry["job_modal_buttons"]["core.export_object_list"]
        job_result = self.run_export()
        redirect_button = button.get_redirect_button(job_result, RequestFactory().get("/"))
        self.assertTrue(redirect_button["url"])
        self.assertIn("Download", redirect_button["label"])
        self.assertEqual(redirect_button["color"], "success")
        self.assertEqual(redirect_button["attributes"]["data-nb-auto-download"], "true")

        job_result.status = JobResultStatusChoices.STATUS_FAILURE
        job_result.save()
        self.assertEqual(button.get_redirect_button(job_result, RequestFactory().get("/")), {})

    def test_jobresult_modal_offers_export_download(self):
        """The job-result modal renders the auto-downloading Download button for a completed export."""
        job_result = self.run_export()
        self.add_permissions("extras.view_jobresult")
        response = self.client.post(
            reverse("extras:jobresult_modal", kwargs={"pk": job_result.pk}),
            data={"job_modal_button": "core.export_object_list"},
            HTTP_HX_REQUEST="true",
        )
        self.assertHttpStatus(response, 200)
        content = response.content.decode(response.charset)
        self.assertIn("data-nb-auto-download", content)
        self.assertIn("Download", content)


# ===========================================================================
# Import job modal
# ===========================================================================
class ImportModalTests(ImportExportJobTestCase):
    def test_import__modal_renders_field_table(self):
        """The ImportObjects job form renders via its custom modal template with the field-reference table."""
        get_job_class_and_model("nautobot.core.jobs", "ImportObjects")  # ensure the job model is enabled
        self.add_permissions("extras.run_job")
        response = self.client.post(
            reverse("extras:job_run_by_class_path", kwargs={"class_path": "nautobot.core.jobs.ImportObjects"}),
            data={
                "render_job_form": True,
                "job_modal_button": "core.import_objects",
                "content_type": ContentType.objects.get_for_model(Status).pk,
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertHttpStatus(response, 200)
        # As above: an unloadable htmx_template_name silently falls back to the generic job modal.
        self.assertTemplateUsed(response, "system_jobs/import_job_form_modal.html")
        self.assertTemplateUsed(response, "system_jobs/inc/csv_fields_table.html")
        content = response.content.decode(response.charset)
        self.assertIn("csv-fields-table", content)
        self.assertIn("csv-fields-tbody", content)


# ===========================================================================
# Layer 1b — core import resolution (per field type)
# ===========================================================================
class CoreImportResolveTests(ImportExportJobTestCase):
    def test_core_import__m2m_ct(self):
        """A CSV with a content_types (M2M to ContentType) column creates records with the relations set."""
        job_result = self.run_import(self.csv_data)
        self.assertNoIssues(job_result)
        self.assertEqual(4, Status.objects.filter(name__startswith="test_status").count())

    def test_core_import__cf(self):
        """A custom-field value round-trips: importable as cf_<key> and exportable as a cf_<key> column."""
        from nautobot.extras.choices import CustomFieldTypeChoices
        from nautobot.extras.models import CustomField

        cf = CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, key="test_ie_cf", label="Test IE CF")
        cf.content_types.set([ContentType.objects.get_for_model(Status)])
        status = self.create_status(name="test_cf_status", color="111111")

        self.run_import("name,cf_test_ie_cf\ntest_cf_status,hello-cf", match_fields="name")
        status.refresh_from_db()
        self.assertEqual(status.cf["test_ie_cf"], "hello-cf")

        text = self.export_text(self.run_export(query_string="name=test_cf_status", export_fields="name,cf_test_ie_cf"))
        self.assertIn("cf_test_ie_cf", text)
        self.assertIn("hello-cf", text)

    def test_core_import__gfk(self):
        """A GFK-backed association (ContactAssociation) resolves its generic target and related keys."""
        self.add_permissions(
            "dcim.view_locationtype",
            "extras.view_status",
            "dcim.view_location",
            "extras.add_role",
            "extras.add_contact",
        )
        self.run_import("name\nContactAssignmentImportTestLocationType", model=LocationType)
        self.assertEqual(LocationType.objects.filter(name="ContactAssignmentImportTestLocationType").count(), 1)

        self.run_import(
            "\n".join(
                [
                    "location_type__name,name,status__name",
                    "ContactAssignmentImportTestLocationType,ContactAssignmentImportTestLocation1,Active",
                    "ContactAssignmentImportTestLocationType,ContactAssignmentImportTestLocation2,Active",
                ]
            ),
            model=Location,
        )
        self.assertEqual(
            Location.objects.filter(location_type__name="ContactAssignmentImportTestLocationType").count(), 2
        )

        self.run_import("name,email\nBob-ContactAssignmentImportTestLocation,bob@example.com", model=Contact)
        self.assertEqual(Contact.objects.filter(name="Bob-ContactAssignmentImportTestLocation").count(), 1)

        self.run_import(
            "name,content_types\nContactAssignmentImportTestLocation-On Site,extras.contactassociation", model=Role
        )
        self.assertEqual(Role.objects.filter(name="ContactAssignmentImportTestLocation-On Site").count(), 1)

        associations = ["associated_object_id,associated_object_type,status__name,role__name,contact__name"]
        for location in Location.objects.filter(location_type__name="ContactAssignmentImportTestLocationType"):
            associations.append(
                f"{location.pk},dcim.location,Active,ContactAssignmentImportTestLocation-On Site,"
                "Bob-ContactAssignmentImportTestLocation"
            )
        self.run_import("\n".join(associations), model=ContactAssociation)


# ===========================================================================
# Layer 1b — core upsert (create / update / unchanged)
# ===========================================================================
class CoreUpsertTests(ImportExportJobTestCase):
    def test_core_upsert__scalar__update(self):
        """An update logs the changed fields as `field: old → new`."""
        self.create_status(color="111111")
        job_result = self.run_import("name,color\ntest_update_status,222222", match_fields="name")
        self.assertImport(job_result, updated=1)
        entry = JobLogEntry.objects.get(job_result=job_result, message__icontains="Updated record")
        self.assertRegex(entry.message, r"color:.*111111.*→.*222222")

    def test_core_upsert__scalar__unchanged(self):
        """Re-importing identical data writes nothing: no save, no change-log, reported as unchanged."""
        status = self.create_status(color="111111")
        first = self.run_import("name,color\ntest_update_status,222222", match_fields="name")
        self.assertImport(first, updated=1)
        status.refresh_from_db()
        touched_at = status.last_updated

        second = self.run_import("name,color\ntest_update_status,222222", match_fields="name")
        self.assertImport(second, created=0, updated=0, unchanged=1)
        status.refresh_from_db()
        self.assertEqual(status.last_updated, touched_at)  # no write occurred
        self.assertNoLog(second, "No changes", level=LogLevelChoices.LOG_INFO)  # not surfaced at info level
        self.assertLog(second, "No changes", level=LogLevelChoices.LOG_DEBUG)  # but logged at debug level

    def test_core_upsert__mixed(self):
        """In a single run, matched rows update and unmatched rows create, with distinct counts reported."""
        status = self.create_status()
        csv_data = "\n".join(
            [
                "name,color,content_types",
                "test_update_status,555555,dcim.device",
                "test_upsert_new_status,666666,dcim.device",
            ]
        )
        job_result = self.run_import(csv_data, match_fields="name")
        status.refresh_from_db()
        self.assertEqual(status.color, "555555")
        self.assertTrue(Status.objects.filter(name="test_upsert_new_status", color="666666").exists())
        self.assertImport(job_result, updated=1, created=1)


# ===========================================================================
# Match key (source, uniqueness, failures)
# ===========================================================================
class MatchKeyTests(ImportExportJobTestCase):
    def test_match__param(self):
        """An explicit match_fields parameter updates matching records in place."""
        status = self.create_status()
        job_result = self.run_import("name,color\ntest_update_status,222222", match_fields="name")
        status.refresh_from_db()
        self.assertEqual(status.color, "222222")
        self.assertEqual(Status.objects.filter(name="test_update_status").count(), 1)
        self.assertImport(job_result, created=0, updated=1, match_fields=["name"], source="run parameter")

    def test_match__directive_csv(self):
        """A `# nautobot-import:` directive row resolves the match key with no parameters supplied."""
        status = self.create_status()
        csv_data = "\n".join(["# nautobot-import: match_fields=name", "name,color", "test_update_status,333333"])
        job_result = self.run_import(csv_data)
        status.refresh_from_db()
        self.assertEqual(status.color, "333333")
        self.assertImport(job_result, updated=1, match_fields=["name"])

    def test_match__precedence_param_over_directive(self):
        """An explicit match_fields parameter takes precedence over the file's directive."""
        status = self.create_status()
        csv_data = "\n".join(["# nautobot-import: match_fields=color", "name,color", "test_update_status,444444"])
        job_result = self.run_import(csv_data, match_fields="name")
        status.refresh_from_db()
        self.assertEqual(status.color, "444444")
        self.assertImport(job_result, match_fields=["name"])

    def test_match__default_natural_key(self):
        """With no parameter or directive, records match on the model's natural key by default."""
        status = self.create_status()
        csv_data = "\n".join(
            [
                "name,color,content_types",
                "test_update_status,777777,dcim.device",
                "test_default_new_status,888888,dcim.device",
            ]
        )
        job_result = self.run_import(csv_data)
        status.refresh_from_db()
        self.assertEqual(status.color, "777777")
        self.assertTrue(Status.objects.filter(name="test_default_new_status").exists())
        self.assertImport(job_result, updated=1, created=1, match_fields=["name"], source="default")

    def test_match__default_id(self):
        """With no parameter or directive, an `id` column matches records on primary key."""
        status = self.create_status()
        job_result = self.run_import(f"id,color\n{status.pk},999999")
        status.refresh_from_db()
        self.assertEqual(status.color, "999999")
        self.assertImport(job_result, updated=1, match_fields=["id"], source="default")

    def test_match__composite(self):
        """A composite match key (name, color) resolves the record; a non-key field is updated."""
        status = self.create_status(name="test_composite", color="111111")
        job_result = self.run_import(
            "name,color,description\ntest_composite,111111,composite-updated", match_fields="name,color"
        )
        status.refresh_from_db()
        self.assertEqual(status.description, "composite-updated")
        self.assertImport(job_result, updated=1, match_fields=["name", "color"])

    def test_match__user_defined_unique_field(self):
        """Matching on a field with no DB uniqueness constraint (color) works when it is unique in the data."""
        status = self.create_status(name="test_userunique", color="abcabc")
        job_result = self.run_import("name,color\ntest_userunique_renamed,abcabc", match_fields="color")
        status.refresh_from_db()
        self.assertEqual(status.name, "test_userunique_renamed")
        self.assertImport(job_result, updated=1, match_fields=["color"])

    def test_match__nonunique_dupe_in_file(self):
        """A match key that doesn't uniquely identify rows within the file fails with a clear error."""
        self.create_status()
        csv_data = "\n".join(["name,color", "test_update_status,111111", "test_update_status,222222"])
        job_result = self.run_import(
            csv_data, match_fields="name", expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        self.assertLog(job_result, "do not uniquely identify each row", level=LogLevelChoices.LOG_ERROR)

    def test_match__matches_multiple_existing(self):
        """A row whose match key matches more than one existing record fails with a clear error."""
        self.create_status(name="test_multi_status1", color="555555")
        self.create_status(name="test_multi_status2", color="555555")
        job_result = self.run_import(
            "name,color\ntest_multi_status1,555555",
            match_fields="color",
            roll_back_if_error=False,
            expected_status=JobResultStatusChoices.STATUS_FAILURE,
        )
        self.assertLog(job_result, "Multiple existing records match", level=LogLevelChoices.LOG_ERROR)

    def test_match__unknown_field(self):
        """An unrecognized match field fails with an error identifying the field."""
        self.create_status()
        job_result = self.run_import(
            "name,color\ntest_update_status,222222",
            match_fields="no_such_field",
            expected_status=JobResultStatusChoices.STATUS_FAILURE,
        )
        self.assertLog(job_result, "Unknown match field(s): no_such_field", level=LogLevelChoices.LOG_ERROR)


# ===========================================================================
# Layer 2 — import format adapters
# ===========================================================================
class ImportAdapterTests(ImportExportJobTestCase):
    def test_adapter_import__bom(self):
        """A .csv file with utf-8-with-BOM encoding imports successfully (#5812, #5985)."""
        status = Status.objects.get(name="Active").pk
        content = f"prefix,status\n192.168.1.1/32,{status}".encode("utf-8-sig")
        csv_file = FileProxy.objects.create(name="test.csv", file=ContentFile(content, name="test.csv"))
        job_result = self.run_import(model=Prefix, csv_file=csv_file.id)
        self.assertNoIssues(job_result)
        self.assertEqual(
            1, Prefix.objects.filter(status=Status.objects.get(name="Active"), prefix="192.168.1.1/32").count()
        )

    def test_adapter_import__bare_list_yaml(self):
        """A bare YAML list of records (no document) imports with the model supplied by the job form."""
        yaml_data = "\n".join(["- name: test_yaml_bare_status", "  color: '334455'", "  content_types: [dcim.device]"])
        self.run_import(yaml_data, import_format="yaml")
        self.assertTrue(Status.objects.filter(name="test_yaml_bare_status", color="334455").exists())


# ===========================================================================
# Layer 3 — end-to-end round-trips
# ===========================================================================
class RoundTripE2ETests(ImportExportJobTestCase):
    def _roundtrip(self, export_format, source):
        """Export one status, flip its color in the raw file, re-import, and assert the in-place update."""
        status = self.create_status(name=f"test_{export_format}_roundtrip", color="111111")
        export_kwargs = {"query_string": f"name=test_{export_format}_roundtrip"}
        if export_format != "csv":
            export_kwargs["export_format"] = export_format
        edited = self.export_text(self.run_export(**export_kwargs)).replace("111111", "222222")
        count_before = Status.objects.count()
        job_result = self.run_import(edited)  # format auto-detected from content
        status.refresh_from_db()
        self.assertEqual(status.color, "222222")
        self.assertEqual(Status.objects.count(), count_before)
        self.assertImport(job_result, created=0, updated=1, source=source)

    def test_e2e_roundtrip__csv(self):
        self._roundtrip("csv", source="file directive")

    def test_e2e_roundtrip__json(self):
        self._roundtrip("json", source="file directive")

    def test_e2e_roundtrip__yaml(self):
        self._roundtrip("yaml", source="file directive")


# ===========================================================================
# Import errors, strictness & rollback
# ===========================================================================
class ImportErrorTests(ImportExportJobTestCase):
    def test_error__no_data_no_file(self):
        """Either csv_data or csv_file must be provided."""
        self.run_import(username=self.user.username, expected_status=JobResultStatusChoices.STATUS_FAILURE)

    def test_error__unknown_field_json(self):
        """An import with an unrecognized field fails with an error identifying the field (#6464)."""
        payload = json.dumps([{"name": "test_bad_field_status", "color": "111111", "colour": "111111"}])
        job_result = self.run_import(
            payload, import_format="json", expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        self.assertLog(job_result, "unrecognized field(s): colour", level=LogLevelChoices.LOG_ERROR)
        self.assertFalse(Status.objects.filter(name="test_bad_field_status").exists())

    def test_error__unknown_field_csv(self):
        """A CSV import with an unrecognized column fails with an error identifying the column (#6464)."""
        job_result = self.run_import(
            "name,colour\ntest_bad_column_status,111111", expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        self.assertLog(job_result, "colour", level=LogLevelChoices.LOG_ERROR)
        self.assertFalse(Status.objects.filter(name="test_bad_column_status").exists())

    def test_error__model_mismatch(self):
        """A file whose document declares a different model than the requested content-type fails clearly."""
        payload = json.dumps(
            {
                "nautobot_import": "1",
                "model": "dcim.device",
                "records": [{"name": "test_mismatch_status", "color": "111111"}],
            }
        )
        job_result = self.run_import(
            payload, import_format="json", expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        self.assertLog(job_result, 'declares model "dcim.device"', level=LogLevelChoices.LOG_ERROR)

    def test_error__unsupported_format(self):
        """An unsupported import_format fails the job and imports nothing."""
        job_result = self.run_import(
            "name,color\ntest_bad_format,111111",
            import_format="xml",
            expected_status=JobResultStatusChoices.STATUS_FAILURE,
        )
        self.assertFalse(Status.objects.filter(name="test_bad_format").exists())
        self.assertIn("Unsupported import format", job_result.traceback or "")

    def test_error__empty_data(self):
        """A file with a header but no data rows creates nothing and warns."""
        job_result = self.run_import("name,color\n")
        self.assertFalse(Status.objects.filter(name__startswith="test_status").exists())
        self.assertLog(job_result, "created or updated", level=LogLevelChoices.LOG_WARNING)


class RollbackTests(ImportExportJobTestCase):
    def _bad_row_csv(self):
        rows = self.csv_data.split("\n")
        rows.insert(1, "test_status0,notacolor,dcim.device")
        return "\n".join(rows)

    def test_rollback__on_reverts_all(self):
        """A bad row rolls back all rows when roll_back_if_error."""
        job_result = self.run_import(
            self._bad_row_csv(), roll_back_if_error=True, expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        log_info = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, message__icontains="created"
        )
        for idx, status_name in enumerate(("test_status1", "test_status2", "test_status3", "test_status4")):
            self.assertIn(f'Created record "{status_name}"', log_info[idx].message)
            self.assertFalse(Status.objects.filter(name=status_name).exists())
        errors = JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(errors[0].message, "Row 1: `color`: `Enter a valid hexadecimal RGB color code.`")
        warnings = JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING)
        self.assertEqual(warnings[0].message, "Rolling back all 4 records.")
        self.assertEqual(warnings[1].message, "No status objects were created or updated")

    def test_rollback__off_keeps_good_rows(self):
        """With roll_back_if_error False, good rows persist and the bad row is reported."""
        job_result = self.run_import(self._bad_row_csv(), expected_status=JobResultStatusChoices.STATUS_FAILURE)
        errors = JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(errors[0].message, "Row 1: `color`: `Enter a valid hexadecimal RGB color code.`")
        self.assertFalse(Status.objects.filter(name="test_status0").exists())
        successes = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, message__icontains="created"
        )
        for idx, status_name in enumerate(("test_status1", "test_status2", "test_status3", "test_status4")):
            self.assertIn(f'Created record "{status_name}"', successes[idx].message)
            self.assertTrue(Status.objects.filter(name=status_name).exists())
        self.assertEqual(successes[4].message, "Created 4 status object(s) from 5 row(s) of data")


# ===========================================================================
# Sentinels & value edge cases
# ===========================================================================
class SentinelValueTests(ImportExportJobTestCase):
    def test_value__special_chars(self):
        """A scalar value with commas/quotes/apostrophes survives CSV export and re-import unchanged."""
        tricky = 'St. John\'s, "HQ" site'
        status = self.create_status(name="test_special", color="111111")
        status.description = tricky
        status.save()
        csv_data = self.export_text(self.run_export(query_string="name=test_special"))
        self.run_import(csv_data)
        status.refresh_from_db()
        self.assertEqual(status.description, tricky)

    @expectedFailure
    def test_sentinel__empty_equiv_null_noobject(self):
        """Intended: an empty cell clears a scalar to null, equivalent to NULL/NoObject.

        Known gap (qa-test-plan §13): an empty string is preserved as "" on a non-nullable CharField
        rather than coerced to null, so this currently fails.
        """
        status = self.create_status(name="test_empty_null", color="111111")
        status.description = "seed"
        status.save()
        self.run_import("name,description\ntest_empty_null,\n", match_fields="name")
        status.refresh_from_db()
        self.assertIsNone(status.description)


# ===========================================================================
# Import mode
# ===========================================================================
class ImportModeTests(ImportExportJobTestCase):
    @skip("Open question: create-only mode + an existing match — behavior undefined (test-matrix Q2)")
    def test_mode__create_only_match_exists(self):
        """Create-only mode encountering an existing match: expected behavior TBD."""


# ===========================================================================
# Permissions
# ===========================================================================
class PermissionTests(ImportExportJobTestCase):
    def test_perm__export_without_permission(self):
        """Job enforces view permission on the content-type being exported."""
        job_result = self.run_export(username=self.user.username, expected_status=JobResultStatusChoices.STATUS_FAILURE)
        self.assertLog(
            job_result,
            f'User "{self.user}" does not have permission to view status objects',
            level=LogLevelChoices.LOG_ERROR,
        )
        self.assertFalse(job_result.files.exists())

    def test_perm__export_with_constrained_permission(self):
        """Job only exports objects the user has permission to view."""
        instance1, instance2 = Status.objects.all()[:2]
        obj_perm = ObjectPermission(name="Test permission", constraints={"pk": instance1.pk}, actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Status))
        job_result = self.run_export(username=self.user.username)
        csv_bytes = self._export_bytes(job_result)
        self.assertTrue(csv_bytes.startswith(codecs.BOM_UTF8), csv_bytes)
        csv_data = csv_bytes.decode("utf-8")
        self.assertIn(str(instance1.pk), csv_data)
        self.assertNotIn(str(instance2.pk), csv_data)

    def test_perm__import_without_permission(self):
        """Job enforces create/update permission on the content-type being imported."""
        job_result = self.run_import(
            self.csv_data, username=self.user.username, expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        self.assertLog(
            job_result,
            f'User "{self.user}" does not have permission to create or update status objects',
            level=LogLevelChoices.LOG_ERROR,
        )
        self.assertFalse(Status.objects.filter(name__startswith="test_status").exists())

    def test_perm__import_constrained_add(self):
        """Job only creates objects the user has permission to add."""
        obj_perm = ObjectPermission(
            name="Test permission", constraints={"color__in": ["111111", "222222"]}, actions=["add"]
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Status))
        job_result = self.run_import(
            self.csv_data, username=self.user.username, expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        successes = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, message__icontains="created"
        )
        self.assertEqual(successes[0].message, 'Row 1: Created record "test_status1"')
        self.assertEqual(successes[1].message, 'Row 2: Created record "test_status2"')
        self.assertEqual(successes[2].message, "Created 2 status object(s) from 4 row(s) of data")
        self.assertLog(
            job_result,
            f'Row 3: User "{self.user}" does not have permission to create an object with these attributes',
            level=LogLevelChoices.LOG_ERROR,
        )
        self.assertFalse(Status.objects.filter(name="test_status3").exists())

    def test_perm__import_update_without_permission(self):
        """An import by a user with neither add nor change permissions is denied outright."""
        status = self.create_status()
        job_result = self.run_import(
            "name,color\ntest_update_status,999999",
            match_fields="name",
            username=self.user.username,
            expected_status=JobResultStatusChoices.STATUS_FAILURE,
        )
        self.assertLog(
            job_result,
            f'User "{self.user}" does not have permission to create or update status objects',
            level=LogLevelChoices.LOG_ERROR,
        )
        status.refresh_from_db()
        self.assertEqual(status.color, "111111")

    def test_perm__import_update_requires_change(self):
        """A user with only add permission cannot update matched records (treated as create → fails)."""
        obj_perm = ObjectPermission(name="Add only", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Status))
        status = self.create_status()
        self.run_import(
            "name,color\ntest_update_status,999999",
            match_fields="name",
            username=self.user.username,
            roll_back_if_error=False,
            expected_status=JobResultStatusChoices.STATUS_FAILURE,
        )
        status.refresh_from_db()
        self.assertEqual(status.color, "111111")


# ===========================================================================
# REST API CSV backwards-compatibility (§16)
# ===========================================================================
class RestApiCsvTests(TransactionTestCase):
    """The default CSV keeps only the historical M2M subset and omits the newly-supported composite M2M;
    exclude_m2m=False opts every M2M in; exclude_m2m=True drops them all. Measured on output fields."""

    def _csv_output_fields(self, exclude_m2m):
        context = {"request": None, "depth": 0}
        if exclude_m2m is not None:
            context["exclude_m2m"] = exclude_m2m
        serializer = DeviceSerializer(context=context, force_csv=True)
        return {name for name, field in serializer.fields.items() if not field.write_only}

    def test_rest_csv__default_keeps_subset_omits_composite(self):
        fields = self._csv_output_fields(None)
        self.assertIn("tags", fields)
        self.assertNotIn("software_image_files", fields)

    def test_rest_csv__exclude_m2m_false_includes_composite(self):
        self.assertIn("software_image_files", self._csv_output_fields(False))

    def test_rest_csv__exclude_m2m_true_removes_all_m2m(self):
        fields = self._csv_output_fields(True)
        self.assertNotIn("tags", fields)
        self.assertNotIn("software_image_files", fields)


# ===========================================================================
# Deferred — general M2M (see design-m2m-import-export.md)
# ===========================================================================
class DeferredM2MTests(ImportExportJobTestCase):
    @skip("Deferred: writing through-model M2M on import (see design-m2m-import-export.md)")
    def test_import_through_m2m_deferred(self):
        """VLAN.locations (through-model M2M) round-trip on import — deferred."""
