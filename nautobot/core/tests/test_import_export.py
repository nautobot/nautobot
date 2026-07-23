"""Tests for the CSV/JSON/YAML export format and the `ExportObjectList` job that writes it.

Job-backed tests subclass `ImportExportJobTestCase`, which supplies `run_export()` plus helpers to read
the produced file back (`export_text` / `export_lines` / `export_rows` / `export_document`).

The serializer-level natural-key machinery this builds on is tested in `test_csv.py`; the job's
permission, saved-view and export-template behavior is in `test_jobs.ExportObjectListTest`.
"""

import csv
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import skip

from django.contrib.contenttypes.models import ContentType
from django.test import SimpleTestCase, tag
from django.urls import reverse
import yaml

from nautobot.core.api.import_export import (
    build_document_records,
    build_import_document,
    build_import_metadata,
    IMPORT_DOCUMENT_VERSION,
    nest_flat_dict,
)
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_TYPE
from nautobot.core.jobs import ExportObjectList
from nautobot.core.testing import create_job_result_and_run_job, get_job_class_and_model, TransactionTestCase
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import (
    Cable,
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    Rack,
    SoftwareImageFile,
    SoftwareVersion,
)
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models import JobLogEntry, Role, SecretsGroup, Status, Tag
from nautobot.ipam.models import Namespace, RouteTarget, VRF, VRFDeviceAssignment


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
class OmitCoveredThroughFieldsTests(SimpleTestCase):
    """`_omit_covered_through_fields` decides whether an M2M column already carries its through data.

    Both branches that read a real relation are exercised end-to-end by the `test_adapter_export__m2m_*`
    tests below (`VRF.devices` renders the members, `SecretsGroup.secrets` renders the through rows). What
    only a stub reaches is a serializer field whose `source` is not a model field at all: no serializer in
    Nautobot spells an M2M field that way today, but `source="*"` is ordinary DRF, so an App's serializer
    can, and reporting the whole through model is the right answer when the column can't be identified.
    """

    def test_source_that_is_not_a_model_field(self):
        data_fields = ExportObjectList._omit_covered_through_fields(
            VRF, SimpleNamespace(source="*"), VRFDeviceAssignment, ["name", "rd"]
        )
        self.assertEqual(data_fields, ["name", "rd"])


@tag("unit")
class BuildDocumentRecordsTests(SimpleTestCase):
    """`build_document_records` must collapse only genuinely-null relations.

    `CSV_NO_OBJECT` means "there is no related object at this hop"; `CSV_NULL_TYPE` means "the object
    exists, this one field of it is null". Only the former is a null reference.
    """

    def test_core_prune__null_relation(self):
        self.assertEqual(build_document_records([{"tenant__name": CSV_NO_OBJECT}]), [{"tenant": None}])

    def test_core_prune__null_nested_reference_kept(self):
        """A location that exists but has no parent keeps the location and nulls only the parent."""
        self.assertEqual(
            build_document_records([{"location__name": "Campus", "location__parent__name": CSV_NO_OBJECT}]),
            [{"location": {"name": "Campus", "parent": None}}],
        )

    def test_core_prune__nested_sentinel_does_not_null_its_parent(self):
        """A sentinel at `location__parent__name` reports `location__parent` as null, not `location`.

        Reachable when a field selection names only a nested path (`export_fields=["location__parent__name"]`),
        which today drops the relation's own natural-key lookups.
        """
        self.assertEqual(
            build_document_records([{"location__parent__name": CSV_NO_OBJECT}]),
            [{"location": {"parent": None}}],
        )

    def test_core_prune__all_null_field_values_kept(self):
        """A null for every selected field does not mean the related object is absent."""
        self.assertEqual(
            build_document_records([{"location__description": None}]),
            [{"location": {"description": None}}],
        )

    def test_core_prune__literal_null_string_survives(self):
        """`CSV_NULL_TYPE` is a CSV-only spelling; in a document it is just an ordinary string value."""
        self.assertEqual(
            build_document_records([{"location__description": CSV_NULL_TYPE}]),
            [{"location": {"description": CSV_NULL_TYPE}}],
        )

    def test_core_prune__empty_string_not_a_null_reference(self):
        self.assertEqual(build_document_records([{"location__name": ""}]), [{"location": {"name": ""}}])

    def test_core_prune__deeply_nested_reference(self):
        self.assertEqual(
            build_document_records(
                [
                    {
                        "location__name": "Campus",
                        "location__parent__name": "Region",
                        "location__parent__parent__name": CSV_NO_OBJECT,
                    }
                ]
            ),
            [{"location": {"name": "Campus", "parent": {"name": "Region", "parent": None}}}],
        )

    def test_core_prune__relation_itself_null_collapses_at_head(self):
        """A null relation sentinels its own natural key too, which is what nulls the head."""
        self.assertEqual(
            build_document_records([{"location__name": CSV_NO_OBJECT, "location__parent__name": CSV_NO_OBJECT}]),
            [{"location": None}],
        )

    def test_core_prune__composite_natural_key_relation_null(self):
        self.assertEqual(
            build_document_records(
                [{"device_type__model": CSV_NO_OBJECT, "device_type__manufacturer__name": CSV_NO_OBJECT}]
            ),
            [{"device_type": None}],
        )

    def test_core_prune__composite_natural_key_relation_present(self):
        self.assertEqual(
            build_document_records([{"device_type__model": "C9300", "device_type__manufacturer__name": "Cisco"}]),
            [{"device_type": {"model": "C9300", "manufacturer": {"name": "Cisco"}}}],
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


class ImportExportJobTestCase(TransactionTestCase):
    """Shared fixtures + the setup→run→assert cadence for the ExportObjectList job."""

    databases = ("default", "job_logs")

    # -- scenario setup --------------------------------------------------------
    def create_status(self, name="test_update_status", color="111111"):
        status = Status.objects.create(name=name, color=color)
        status.content_types.set([ContentType.objects.get_for_model(Device)])
        return status

    def create_device_type_with_software_image_files(self):
        """A DeviceType whose `software_image_files` M2M members have a composite (3-part) natural key."""
        manufacturer = Manufacturer.objects.create(name="M2M Composite Mfr")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="M2M Composite DT", u_height=1)
        software_version = SoftwareVersion.objects.create(
            platform=Platform.objects.create(name="M2M Composite Platform", manufacturer=manufacturer),
            version="1.2.3",
            status=Status.objects.get_for_model(SoftwareVersion).first(),
        )
        for image_file_name in ("m2m-composite-a.bin", "m2m-composite-b.bin"):
            device_type.software_image_files.add(
                SoftwareImageFile.objects.create(
                    software_version=software_version,
                    image_file_name=image_file_name,
                    status=Status.objects.get_for_model(SoftwareImageFile).first(),
                )
            )
        return list(device_type.software_image_files.all())

    def create_cable(self):
        """A Cable terminated on two Interfaces, for the M2M fields `CableSerializer` excludes."""
        location_type = LocationType.objects.create(name="M2M Cable Location Type")
        location_type.content_types.add(ContentType.objects.get_for_model(Device))
        location = Location.objects.create(
            name="M2M Cable Location",
            location_type=location_type,
            status=Status.objects.get_for_model(Location).first(),
        )
        manufacturer = Manufacturer.objects.create(name="M2M Cable Mfr")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="M2M Cable DT", u_height=1)
        role = Role.objects.create(name="M2M Cable Role")
        role.content_types.add(ContentType.objects.get_for_model(Device))
        device = Device.objects.create(
            name="M2M Cable Device",
            device_type=device_type,
            role=role,
            status=Status.objects.get_for_model(Device).first(),
            location=location,
        )
        interface_status = Status.objects.get_for_model(Interface).first()
        interfaces = [
            Interface.objects.create(
                device=device,
                name=f"eth{index}",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            )
            for index in (0, 1)
        ]
        return Cable.objects.create(
            termination_a=interfaces[0],
            termination_b=interfaces[1],
            status=Status.objects.get_for_model(Cable).first(),
        )

    # -- run the job -----------------------------------------------------------
    def run_export(
        self,
        *,
        model=Status,
        expected_status=JobResultStatusChoices.STATUS_SUCCESS,
        allow_issues=False,
        **kwargs,
    ):
        """Run ExportObjectList and assert its status.

        A successful export is also expected to log nothing at WARNING or above, so a test that
        deliberately provokes a warning must pass `allow_issues=True`.
        """
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            content_type=ContentType.objects.get_for_model(model).pk,
            **kwargs,
        )
        self.assertJobResultStatus(job_result, expected_status)
        if expected_status == JobResultStatusChoices.STATUS_SUCCESS and not allow_issues:
            self.assertNoIssues(job_result)
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
    def assertNoIssues(self, job_result):
        self.assertFalse(
            JobLogEntry.objects.filter(
                job_result=job_result, log_level__in=[LogLevelChoices.LOG_WARNING, LogLevelChoices.LOG_ERROR]
            ).exists()
        )

    def assertJobLogEntry(self, job_result, contains, *, level=None):
        qs = JobLogEntry.objects.filter(job_result=job_result, message__icontains=contains)
        if level is not None:
            qs = qs.filter(log_level=level)
        self.assertTrue(qs.exists(), f"Expected a {level or 'any'}-level log entry containing {contains!r}")


class ExportAdapterTests(ImportExportJobTestCase):
    """Per-format export behavior. The CSV/export-template/device-type-YAML basics live in
    `test_jobs.ExportObjectListTest`; these cover what the document format adds."""

    def test_adapter_export__json_nested(self):
        """JSON wraps records in the metadata document, with related fields nested under their parent key."""
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

    def test_adapter_export__csv_stamps_directive(self):
        """CSV exports carry their own import instructions as the leading directive row."""
        self.assertEqual(
            self.export_lines(self.run_export())[0],
            f"# nautobot_import_version={IMPORT_DOCUMENT_VERSION}; model=extras.status; match_fields=name",
        )

    def test_adapter_export__yaml_is_the_document_even_for_devicetype(self):
        """YAML always means the standard document, including for models that also have a to_yaml()."""
        mfr = Manufacturer.objects.create(name="Standard YAML Mfr")
        DeviceType.objects.create(manufacturer=mfr, model="Standard YAML DT", u_height=1)
        job_result = self.run_export(model=DeviceType, query_string="model=Standard+YAML+DT", export_format="yaml")
        self.assertEqual(self.export_filename(job_result), "nautobot_device_types.yaml")
        doc = self.export_document(job_result)
        self.assertEqual(doc["nautobot_import_version"], IMPORT_DOCUMENT_VERSION)
        self.assertEqual(doc["model"], "dcim.devicetype")
        self.assertEqual(doc["records"][0]["model"], "Standard YAML DT")
        self.assertEqual(doc["records"][0]["manufacturer"], {"name": "Standard YAML Mfr"})

    def test_adapter_export__devicetype_library_rejects_unsupported_model(self):
        """The devicetype-library format is only meaningful for models that implement to_yaml()."""
        job_result = self.run_export(
            export_format="devicetype_library", expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        self.assertJobLogEntry(
            job_result, "does not support the devicetype-library format", level=LogLevelChoices.LOG_ERROR
        )
        self.assertFalse(job_result.files.exists())

    def test_adapter_export__generic_yaml(self):
        """A model without to_yaml() exports as the same document as JSON, dumped in declaration order."""
        self.create_status(name="test_yaml_export_status", color="112233")
        job_result = self.run_export(query_string="name=test_yaml_export_status", export_format="yaml")
        self.assertEqual(self.export_filename(job_result), "nautobot_statuses.yaml")

        doc = self.export_document(job_result)
        self.assertEqual(doc["nautobot_import_version"], IMPORT_DOCUMENT_VERSION)
        self.assertEqual(doc["model"], "extras.status")
        self.assertEqual(doc["match_fields"], ["name"])
        self.assertEqual(len(doc["records"]), 1)
        self.assertEqual(doc["records"][0]["name"], "test_yaml_export_status")
        self.assertEqual(doc["records"][0]["color"], "112233")

        # Dumped with sort_keys=False, so the version leads rather than the keys going alphabetical
        self.assertTrue(self.export_text(job_result).startswith("nautobot_import_version:"))

    def test_adapter_export__includes_non_default_m2m_columns(self):
        """The Job exports every M2M field, so the file can be re-imported in full.

        A REST `?format=csv` response for the same model has neither column -- see
        `test_csv.ExportingWidensM2MFieldsTest` for that contrast and the reasoning behind it.
        """
        namespace, _ = Namespace.objects.get_or_create(name="M2M Columns Namespace")
        VRF.objects.create(name="M2M Columns VRF", namespace=namespace)

        # Line 0 is the import directive, line 1 the header row
        headers = self.export_lines(self.run_export(model=VRF))[1].split(",")
        self.assertIn("import_targets", headers)
        self.assertIn("export_targets", headers)

    def test_adapter_export__m2m_through_data_is_reported_as_missing(self):
        """A relation whose through model records data about each pairing exports only the membership.

        `VRF.devices` is joined by `VRFDeviceAssignment`, which also records `rd` and `name`; the column
        of member natural keys can't carry those, so the Job says so and names where to find them.
        """
        namespace, _ = Namespace.objects.get_or_create(name="M2M Through Namespace")
        VRF.objects.create(name="M2M Through VRF", namespace=namespace)

        job_result = self.run_export(model=VRF)
        self.assertJobLogEntry(
            job_result,
            "`devices` is managed through `ipam.vrfdeviceassignment`, which also records `name`, `rd`",
            level=LogLevelChoices.LOG_INFO,
        )
        # Reported at INFO, not WARNING: the export is doing the right thing, just not the whole thing
        self.assertNoIssues(job_result)

    def test_adapter_export__m2m_field_absent_from_the_serializer_is_not_reported(self):
        """An M2M field the serializer omits has no column in the file, so there is nothing to report on.

        `CableSerializer` excludes the typed termination accessors (`interfaces`, `front_ports`, ...) in
        favor of its own `terminations` field. Their through model, `CableToCableTermination`, does record
        data about each pairing (`cable_end`, `connector`), so a report would be produced if the Job went
        looking for a column that isn't there.
        """
        self.create_cable()

        job_result = self.run_export(model=Cable)
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, message__icontains="cabletocabletermination").exists()
        )
        headers = self.export_lines(job_result)[1].split(",")
        self.assertNotIn("interfaces", headers)

    def test_adapter_export__m2m_through_data_kept_by_the_member_key_is_not_reported(self):
        """No notice when the column already carries the through data.

        `SecretsGroup.secrets` is sourced from the association rows rather than the secrets, and their
        natural key spans `access_type`/`secret_type`, so nothing is lost and there is nothing to say.
        """
        SecretsGroup.objects.create(name="M2M Through Secrets Group")
        job_result = self.run_export(model=SecretsGroup)
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, message__icontains="secretsgroupassociation").exists()
        )

    def test_adapter_export__m2m_scalar_members(self):
        """A scalar-keyed M2M is comma-joined for CSV but stays a list in either document format."""
        namespace, _ = Namespace.objects.get_or_create(name="M2M Export Namespace")
        vrf = VRF.objects.create(name="M2M Export VRF", namespace=namespace)
        for name in ("65000:1", "65000:2"):
            vrf.import_targets.add(RouteTarget.objects.create(name=name))

        row = next(r for r in self.export_rows(self.run_export(model=VRF)) if r["name"] == "M2M Export VRF")
        self.assertEqual(sorted(row["import_targets"].split(",")), ["65000:1", "65000:2"])

        for export_format in ("json", "yaml"):
            with self.subTest(export_format=export_format):
                doc = self.export_document(self.run_export(model=VRF, export_format=export_format))
                record = next(r for r in doc["records"] if r["name"] == "M2M Export VRF")
                self.assertEqual(sorted(record["import_targets"]), ["65000:1", "65000:2"])

    def test_adapter_export__m2m_scalar_member_containing_the_separator(self):
        """A member containing a comma is quoted inside the cell, so CSV still reads back two members."""
        namespace, _ = Namespace.objects.get_or_create(name="M2M Comma Namespace")
        vrf = VRF.objects.create(name="M2M Comma VRF", namespace=namespace)
        for name in ("65000:1", "65000:2,65000:3"):
            vrf.import_targets.add(RouteTarget.objects.create(name=name))

        row = next(r for r in self.export_rows(self.run_export(model=VRF)) if r["name"] == "M2M Comma VRF")
        self.assertEqual(
            sorted(NautobotCSVParser.split_list_cell(row["import_targets"])), ["65000:1", "65000:2,65000:3"]
        )

        for export_format in ("json", "yaml"):
            with self.subTest(export_format=export_format):
                doc = self.export_document(self.run_export(model=VRF, export_format=export_format))
                record = next(r for r in doc["records"] if r["name"] == "M2M Comma VRF")
                self.assertEqual(sorted(record["import_targets"]), ["65000:1", "65000:2,65000:3"])

    def test_adapter_export__m2m_tags(self):
        """`tags` is a TagsManager rather than a concrete M2M, but exports like any other scalar-keyed one."""
        namespace, _ = Namespace.objects.get_or_create(name="M2M Tags Namespace")
        vrf = VRF.objects.create(name="M2M Tags VRF", namespace=namespace)
        for name in ("m2m-export-tag-a", "m2m-export-tag-b"):
            tag_ = Tag.objects.create(name=name)
            tag_.content_types.add(ContentType.objects.get_for_model(VRF))
            vrf.tags.add(tag_)

        row = next(r for r in self.export_rows(self.run_export(model=VRF)) if r["name"] == "M2M Tags VRF")
        self.assertEqual(sorted(row["tags"].split(",")), ["m2m-export-tag-a", "m2m-export-tag-b"])

        for export_format in ("json", "yaml"):
            with self.subTest(export_format=export_format):
                doc = self.export_document(self.run_export(model=VRF, export_format=export_format))
                record = next(r for r in doc["records"] if r["name"] == "M2M Tags VRF")
                self.assertEqual(sorted(record["tags"]), ["m2m-export-tag-a", "m2m-export-tag-b"])

    def test_adapter_export__m2m_content_type_members(self):
        """An M2M to ContentType uses the scalar `<app_label>.<model>` key rather than a natural-key dict."""
        status = self.create_status(name="M2M CT Status")  # already carries dcim.device
        status.content_types.add(ContentType.objects.get_for_model(Rack))

        row = self.export_rows(self.run_export(query_string="name=M2M+CT+Status"))[0]
        self.assertEqual(sorted(row["content_types"].split(",")), ["dcim.device", "dcim.rack"])

        for export_format in ("json", "yaml"):
            with self.subTest(export_format=export_format):
                doc = self.export_document(
                    self.run_export(query_string="name=M2M+CT+Status", export_format=export_format)
                )
                self.assertEqual(sorted(doc["records"][0]["content_types"]), ["dcim.device", "dcim.rack"])

    def test_adapter_export__m2m_composite_members(self):
        """A composite-natural-key M2M renders each member by that key: a JSON cell in CSV, a nested dict
        in a document (where the member's own multi-hop lookups nest, just as the record's relations do).
        """
        software_image_files = self.create_device_type_with_software_image_files()
        expected_flat = [
            {
                "image_file_name": image_file.image_file_name,
                "software_version__platform__name": image_file.software_version.platform.name,
                "software_version__version": image_file.software_version.version,
            }
            for image_file in software_image_files
        ]
        expected_nested = [
            {
                "image_file_name": image_file.image_file_name,
                "software_version": {
                    "platform": {"name": image_file.software_version.platform.name},
                    "version": image_file.software_version.version,
                },
            }
            for image_file in software_image_files
        ]

        row = self.export_rows(self.run_export(model=DeviceType, query_string="model=M2M+Composite+DT"))[0]
        self.assertEqual(json.loads(row["software_image_files"]), expected_flat)

        for export_format in ("json", "yaml"):
            with self.subTest(export_format=export_format):
                doc = self.export_document(
                    self.run_export(
                        model=DeviceType, query_string="model=M2M+Composite+DT", export_format=export_format
                    )
                )
                self.assertEqual(doc["records"][0]["software_image_files"], expected_nested)

    def test_adapter_export__m2m_empty(self):
        """An M2M with no members is an empty cell in CSV and an empty list in either document format."""
        namespace, _ = Namespace.objects.get_or_create(name="M2M Empty Namespace")
        VRF.objects.create(name="M2M Empty VRF", namespace=namespace)

        row = next(r for r in self.export_rows(self.run_export(model=VRF)) if r["name"] == "M2M Empty VRF")
        self.assertEqual(row["import_targets"], "")

        for export_format in ("json", "yaml"):
            with self.subTest(export_format=export_format):
                doc = self.export_document(self.run_export(model=VRF, export_format=export_format))
                record = next(r for r in doc["records"] if r["name"] == "M2M Empty VRF")
                self.assertEqual(record["import_targets"], [])


class ExportFieldSelectionTests(ImportExportJobTestCase):
    def test_select__csv(self):
        """An explicit field selection yields exactly those columns, in selection order."""
        mfr = Manufacturer.objects.create(name="Selection Mfr")
        DeviceType.objects.create(manufacturer=mfr, model="Selection DT", u_height=1)
        lines = self.export_lines(
            self.run_export(
                model=DeviceType, query_string="model=Selection+DT", export_fields="model,manufacturer__name"
            )
        )
        self.assertTrue(
            lines[0].startswith("# nautobot_import_version=3; model=dcim.devicetype; match_fields="), lines[0]
        )
        self.assertEqual(lines[1], "model,manufacturer__name")
        self.assertEqual(lines[2], "Selection DT,Selection Mfr")

    @skip("Enable in X4: uses use_current_view (sort + saved-view export config)")
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
        self.assertTrue(
            JobLogEntry.objects.filter(
                job_result=job_result, message__contains="no_such_field", log_level=LogLevelChoices.LOG_ERROR
            ).exists()
        )

    @skip("Enable in X5: needs ExportFieldsForm (export UI)")
    def test_select__form_expands_single_fk_relations(self):
        """ExportFieldsForm offers a flat, orderable list including single-FK relations expanded one level."""
        from nautobot.core.forms import ExportFieldsForm  # TODO: move to a top-level import once this exists

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

    @skip("Enable in X5: needs the export job-form modal template + modal button")
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
        content = response.content.decode(response.charset)
        self.assertIn("export-fields-selector", content)
        self.assertIn("nb-select-multiple-orderable-list", content)
        self.assertIn('value="name"', content)
        self.assertInHTML(
            '<input class="form-check-input my-6" id="id_export_selector-export_fields_option_name" '
            'name="export_selector-export_fields" type="checkbox" value="name" checked>',
            content,
        )
