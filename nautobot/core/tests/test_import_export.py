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
from unittest import mock, skip

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.test import SimpleTestCase, tag, TestCase
from django.urls import reverse
from rest_framework import serializers
import yaml

from nautobot.circuits.api.serializers import CircuitSerializer, CircuitTerminationSerializer
from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.import_export import (
    build_document_records,
    build_import_document,
    build_import_metadata,
    EXPORT_FIELD_MAX_DEPTH,
    IMPORT_DOCUMENT_VERSION,
    nest_flat_dict,
    validate_field_paths,
)
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_TYPE
from nautobot.core.jobs import ExportObjectList
from nautobot.core.testing import create_job_result_and_run_job, get_job_class_and_model, TransactionTestCase
from nautobot.dcim.api.serializers import (
    CableSerializer,
    DeviceSerializer,
    DeviceTypeSerializer,
    InterfaceSerializer,
)
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
    RackReservation,
    SoftwareImageFile,
    SoftwareVersion,
)
from nautobot.extras.api.serializers import ObjectChangeSerializer, StatusSerializer
from nautobot.extras.choices import CustomFieldTypeChoices, JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models import CustomField, JobLogEntry, Role, SecretsGroup, Status, Tag
from nautobot.ipam.api.serializers import VLANSerializer
from nautobot.ipam.models import Namespace, RouteTarget, VLAN, VRF, VRFDeviceAssignment
from nautobot.users.api.serializers import UserSerializer
from nautobot.users.models import ObjectPermission

User = get_user_model()


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


class MatchFieldsTests(TestCase):
    """`ExportObjectList._get_match_fields` decides whether an export can carry import instructions.

    A file is only re-importable if it contains enough columns to identify each existing record, so an
    explicit field selection must stamp the match key only when the selection covers *every* natural-key
    lookup -- either the lookup itself (`manufacturer__name`) or the relation head that expands to it
    (`manufacturer`). Anything less and the file must not claim a key it cannot support.
    """

    def match_fields(self, model, export_field_paths=None):
        return ExportObjectList._get_match_fields(model, export_field_paths)

    def test_match__no_selection_uses_the_whole_natural_key(self):
        self.assertEqual(self.match_fields(Status), ["name"])
        self.assertEqual(self.match_fields(DeviceType), ["manufacturer__name", "model"])

    def test_match__selection_covering_the_key(self):
        self.assertEqual(self.match_fields(Status, ["name", "color"]), ["name"])

    def test_match__selection_omitting_the_key(self):
        self.assertIsNone(self.match_fields(Status, ["color"]))

    def test_match__composite_key_partially_covered(self):
        """All or nothing: `model` alone cannot identify a DeviceType without its manufacturer."""
        self.assertIsNone(self.match_fields(DeviceType, ["model"]))
        self.assertIsNone(self.match_fields(DeviceType, ["manufacturer"]))
        self.assertEqual(
            self.match_fields(DeviceType, ["model", "manufacturer__name"]), ["manufacturer__name", "model"]
        )

    def test_match__relation_head_covers_its_lookups(self):
        """A bare relation expands to its own natural key, so selecting the head covers those lookups."""
        self.assertEqual(self.match_fields(DeviceType, ["model", "manufacturer"]), ["manufacturer__name", "model"])

    def test_match__nested_selection_that_is_not_the_natural_key(self):
        """A nested selection replaces the relation's default lookups, so this one covers nothing."""
        self.assertIsNone(self.match_fields(DeviceType, ["model", "manufacturer__description"]))

    def test_match__every_head_must_be_covered(self):
        """An Interface is keyed by its device *and* its module, so one of the two is not enough."""
        self.assertIn("module__pk", Interface.csv_natural_key_field_lookups())
        self.assertIsNone(self.match_fields(Interface, ["name", "device"]))
        self.assertEqual(
            self.match_fields(Interface, ["name", "device", "module"]),
            list(Interface.csv_natural_key_field_lookups()),
        )

    def test_match__partial_lookup_of_a_relation_is_not_enough(self):
        """`device__name` is one of three `device__` lookups the key needs; naming it alone is not coverage."""
        self.assertIsNone(self.match_fields(Interface, ["name", "device__name"]))

    def test_match__model_without_a_natural_key(self):
        """No identifiable key means no directive, selection or not."""
        self.assertIsNone(self.match_fields(JobLogEntry))
        self.assertIsNone(self.match_fields(JobLogEntry, ["message"]))


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

    # -- custom fields have two spellings, chosen by the selection ---------------
    CF_RECORD = [{"name": "x", "custom_fields": {"a": 1, "b": 2}}]

    def test_core_cf__dict_kept_without_a_selection(self):
        self.assertEqual(build_document_records(self.CF_RECORD), self.CF_RECORD)

    def test_core_cf__dict_kept_when_named(self):
        """Naming `custom_fields` asks for the whole dict, as an unrestricted export produces."""
        self.assertEqual(build_document_records(self.CF_RECORD, field_order=["name", "custom_fields"]), self.CF_RECORD)

    def test_core_cf__selected_keys_become_top_level_entries(self):
        """A `cf_<key>` selection cannot be expressed inside the dict, so the dict gives way to flat keys."""
        self.assertEqual(
            build_document_records(self.CF_RECORD, field_order=["name", "cf_a"]),
            [{"name": "x", "cf_a": 1}],
        )

    def test_core_cf__unselected_key_is_dropped(self):
        """Only custom fields are filtered here; the serializer has already dropped unselected fields."""
        self.assertEqual(
            build_document_records([{"custom_fields": {"a": 1, "b": 2}}], field_order=["cf_b"]), [{"cf_b": 2}]
        )

    def test_core_cf__key_containing_the_separator_is_not_split(self):
        """A custom-field key may contain `__`; the flat entry must survive `nest_flat_dict` intact.

        Auto-slugification never produces a double underscore, but a key can be set explicitly.
        """
        self.assertEqual(
            build_document_records([{"custom_fields": {"my__field": "v"}}], field_order=["cf_my__field"]),
            [{"cf_my__field": "v"}],
        )

    def test_core_cf__selected_key_absent_from_the_record(self):
        """A selected key with no value for this object is present and null, not missing."""
        self.assertEqual(build_document_records([{"custom_fields": {"a": 1}}], field_order=["cf_b"]), [{"cf_b": None}])

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

    def create_status_with_custom_fields(self, name="Custom Field Status"):
        """A Status with two text custom fields set, so a selection can name one and omit the other."""
        content_type = ContentType.objects.get_for_model(Status)
        for key in ("export_cf_a", "export_cf_b"):
            custom_field = CustomField.objects.create(key=key, label=key, type=CustomFieldTypeChoices.TYPE_TEXT)
            custom_field.validated_save()
            custom_field.content_types.set([content_type])
        status = Status.objects.create(name=name, color="123456")
        status._custom_field_data = {"export_cf_a": "A value", "export_cf_b": "B value"}
        status.validated_save()
        return status

    def create_rack_reservation(self):
        """A RackReservation, whose `user` FK is a relation to a model with no natural-key overlap."""
        location_type = LocationType.objects.create(name="Perm Location Type")
        location_type.content_types.add(ContentType.objects.get_for_model(Rack))
        location = Location.objects.create(
            name="Perm Location",
            location_type=location_type,
            status=Status.objects.get_for_model(Location).first(),
        )
        rack = Rack.objects.create(
            name="Perm Rack", location=location, status=Status.objects.get_for_model(Rack).first(), u_height=10
        )
        reservation_owner = User.objects.create(
            username="reservation-owner", email="owner@example.com", is_superuser=True
        )
        return RackReservation.objects.create(
            rack=rack, units=[1, 2], user=reservation_owner, description="Perm Reservation"
        )

    def create_rack_reservation_and_limited_user(self):
        """A RackReservation plus a non-superuser who may view reservations but *not* users.

        The reservation's `user` FK is the interesting relation: `UserSerializer` exposes fields such as
        `email` and `is_superuser` that a RackReservation viewer has no business seeing.
        """
        self.create_rack_reservation()
        limited_user = User.objects.create(username="limited-user", is_superuser=False)
        permission = ObjectPermission.objects.create(name="View rack reservations", actions=["view"])
        permission.users.add(limited_user)
        permission.object_types.add(ContentType.objects.get_for_model(RackReservation))
        self.assertFalse(limited_user.has_perm("users.view_user"))
        return limited_user

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

    def test_adapter_export__uuid_valued_lookup_is_canonically_formatted(self):
        """A UUID reached through a relation is hyphenated, as the object's own `id` is.

        The natural-key lookups are cast to a CharField in SQL, where a UUID column is `char(32)` on MySQL
        but a native type on PostgreSQL. Also reached by unrestricted exports, via `module__pk` and kin.
        """
        reservation = self.create_rack_reservation()
        row = self.export_rows(self.run_export(model=RackReservation, export_fields="description,user__id"))[0]
        self.assertEqual(row["user__id"], str(reservation.user.pk))
        self.assertIn("-", row["user__id"])

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


class ValidateFieldPathsTests(TestCase):
    """`validate_field_paths` vets an export field selection against the serializer field graph.

    DB-backed rather than `SimpleTestCase` because instantiating a serializer resolves ContentTypes (the
    `tags` field's queryset is built by `Tag.objects.get_for_model`), and because a `cf_<key>` reference is
    checked against the model's actual custom fields.

    Otherwise the check is structural rather than about row data, which is what lets the `ExportObjectList`
    job reject a bad selection before it starts serializing.
    """

    @classmethod
    def setUpTestData(cls):
        """A superuser, so that the structural tests below are unaffected by the permission gate."""
        cls.superuser = User.objects.create(username="paths-superuser", is_superuser=True)

    def assertPathsValid(self, serializer_class, paths, **kwargs):
        """Assert the selection is accepted (the function returns None and raises nothing)."""
        kwargs.setdefault("user", self.superuser)
        self.assertIsNone(validate_field_paths(serializer_class, paths, **kwargs))  # pylint: disable=missing-kwoa

    def assertPathsInvalid(self, serializer_class, paths, *expected_fragments, **kwargs):
        """Assert the selection is rejected, and that the message contains each expected fragment."""
        kwargs.setdefault("user", self.superuser)
        with self.assertRaises(ValueError) as context:
            validate_field_paths(serializer_class, paths, **kwargs)
        message = str(context.exception)
        self.assertTrue(message.startswith("Invalid field selection: "), message)
        for fragment in expected_fragments:
            self.assertIn(fragment, message)
        return message

    # -- accepted selections ---------------------------------------------------
    def test_validate__plain_field(self):
        self.assertPathsValid(StatusSerializer, ["name", "color"])

    def test_validate__relation_head_with_no_expansion(self):
        """A bare relation is a legal selection; the serializer expands it to the relation's natural key."""
        self.assertPathsValid(DeviceTypeSerializer, ["manufacturer"])

    def test_validate__single_hop_traversal(self):
        self.assertPathsValid(DeviceTypeSerializer, ["model", "manufacturer__name"])

    def test_validate__multi_hop_traversal(self):
        """Each segment is resolved through the *related* model's serializer, not the root's."""
        self.assertPathsValid(DeviceSerializer, ["device_type__manufacturer__name"])

    def test_validate__traversal_through_a_read_only_fk(self):
        """A relation with no queryset is resolved from the model, so traversal past it still works.

        `Circuit.circuit_termination_a` is `editable=False`, so DRF gives its serializer field no queryset
        and the target comes from `NautobotHyperlinkedRelatedField._related_model` instead -- which must name
        `CircuitTermination` rather than the `Circuit` that declares the field (see
        `test_api.RelatedModelResolutionTest`). Getting that wrong is invisible until a path traverses it.
        """
        self.assertIsNone(
            CircuitSerializer(context={"request": None, "depth": 0}).fields["circuit_termination_a"].queryset
        )
        self.assertPathsValid(CircuitSerializer, ["cid", "circuit_termination_a__term_side"])
        # `cid` is a field of Circuit, not of CircuitTermination, so it must not validate past the hop
        self.assertNotIn("cid", CircuitTerminationSerializer(context={"request": None, "depth": 0}).fields)
        self.assertPathsInvalid(CircuitSerializer, ["circuit_termination_a__cid"], 'unknown field "cid"')

    def test_validate__at_the_maximum_depth(self):
        """`a__b__c__d` is three hops, which the default limit allows."""
        self.assertEqual(EXPORT_FIELD_MAX_DEPTH, 3)
        self.assertPathsValid(InterfaceSerializer, ["device__location__parent__name"])

    def test_validate__duplicate_paths_are_accepted(self):
        """Duplicates are not deduplicated here; the serializer/renderer tolerate a repeated selection."""
        self.assertPathsValid(StatusSerializer, ["name", "name"])

    def test_validate__export_only_m2m_field(self):
        """An opt-in M2M field is nameable, because validation instantiates the serializer as an export does.

        `software_image_files` is absent from a REST-mode `DeviceTypeSerializer` and only becomes readable
        under `exporting=True` -- but the export emits it by default (`test_adapter_export__m2m_composite_members`),
        so a selection has to be able to name it.
        """
        self.assertNotIn("software_image_files", DeviceTypeSerializer(context={"request": None, "depth": 0}).fields)
        self.assertPathsValid(DeviceTypeSerializer, ["model", "software_image_files"])

    def test_validate__field_that_export_mode_drops_is_rejected(self):
        """The converse: a field the export cannot emit is refused even though REST has it.

        `CableSerializer.terminations` is replaced by the typed accessors under `exporting=True`, so there
        would be no such column in the file.
        """
        self.assertIn("terminations", CableSerializer(context={"request": None, "depth": 0}).fields)
        self.assertPathsInvalid(CableSerializer, ["terminations"], 'unknown field "terminations"')

    # -- rejected selections ---------------------------------------------------
    def test_validate__unknown_head(self):
        self.assertPathsInvalid(StatusSerializer, ["no_such_field"], '"no_such_field": unknown field "no_such_field"')

    def test_validate__unknown_nested_segment(self):
        """The error names the offending segment as well as the whole path it came from."""
        self.assertPathsInvalid(
            DeviceSerializer,
            ["device_type__no_such_field"],
            '"device_type__no_such_field": unknown field "no_such_field"',
        )

    def test_validate__scalar_field_cannot_be_expanded(self):
        self.assertPathsInvalid(
            StatusSerializer, ["name__x"], '"name__x": "name" is not a related field and cannot be expanded'
        )

    def test_validate__non_relation_dict_field_cannot_be_expanded(self):
        """`custom_fields` is a dict-valued field, not a relation; `cf_<key>` is the way to name one."""
        self.assertPathsInvalid(
            DeviceSerializer,
            ["custom_fields__x"],
            '"custom_fields" is not a related field and cannot be expanded',
        )

    def test_validate__m2m_cannot_be_traversed(self):
        """Traversing a to-many relation is refused with a message specific to that reason.

        A current limitation of the mechanism rather than of the file format -- see
        `_traversable_relation_target`. Selecting `tags` itself is valid and yields the tag names.
        """
        self.assertPathsInvalid(
            DeviceSerializer, ["tags__name"], '"tags__name": cannot traverse into many-to-many field "tags"'
        )

    def test_validate__m2m_of_content_types_cannot_be_traversed(self):
        """Also refused when the M2M members are ContentTypes rather than Nautobot objects."""
        self.assertPathsInvalid(
            StatusSerializer, ["content_types__app_label"], 'cannot traverse into many-to-many field "content_types"'
        )

    def test_validate__beyond_the_maximum_depth(self):
        self.assertPathsInvalid(
            InterfaceSerializer,
            ["device__location__parent__parent__name"],
            '"device__location__parent__parent__name" traverses more than 3 relations',
        )

    def test_validate__maximum_depth_is_configurable(self):
        """`max_depth` is a parameter; the constant is only its default."""
        self.assertPathsInvalid(
            InterfaceSerializer,
            ["device__location__parent__name"],
            "traverses more than 2 relations",
            max_depth=2,
        )
        self.assertPathsInvalid(InterfaceSerializer, ["device__name"], "more than 0 relations", max_depth=0)

    def test_validate__depth_counts_the_path_not_its_expansion(self):
        """The limit bounds the relations a path *names*; the natural-key expansion is not counted.

        A path ending at a relation is emitted as that relation's natural-key lookups, which add hops.
        Those are not the user's choice and are not charged against the limit -- an unrestricted export of
        the same model already emits them, so counting them would make a selective export stricter than a
        full one, and would reject bare field names outright. See `EXPORT_FIELD_MAX_DEPTH`.
        """
        # `device` names no relation traversal at all, yet is emitted two hops deep
        emitted = [f"device__{lookup}" for lookup in Device.csv_natural_key_field_lookups()]
        self.assertIn("device__tenant__name", emitted)
        self.assertPathsValid(InterfaceSerializer, ["device"], max_depth=0)

        # ...and a relation named at the limit is accepted even though its expansion goes past it
        self.assertGreater(max(lookup.count("__") for lookup in emitted), 1)
        self.assertPathsValid(InterfaceSerializer, ["device__location__parent"], max_depth=2)

    def test_validate__depth_is_checked_before_the_field_names(self):
        """An over-deep path is reported as too deep even when none of its segments exist."""
        message = self.assertPathsInvalid(StatusSerializer, ["a__b__c__d__e"], "traverses more than")
        self.assertNotIn("unknown field", message)

    def test_validate__every_invalid_path_is_reported(self):
        """One call reports all the problems, so a user fixes their selection in one pass."""
        message = self.assertPathsInvalid(
            StatusSerializer,
            ["name", "no_such_field", "color", "also_bad"],
            'unknown field "no_such_field"',
            'unknown field "also_bad"',
        )
        self.assertEqual(message.count(";"), 1)  # the two errors, semicolon-joined

    def test_validate__trailing_separator(self):
        """A trailing `__` leaves an empty final segment, which is reported as an unknown field."""
        self.assertPathsInvalid(DeviceTypeSerializer, ["manufacturer__"], 'unknown field ""')

    def test_validate__empty_path(self):
        self.assertPathsInvalid(StatusSerializer, [""], 'unknown field ""')

    def test_validate__no_paths_is_not_an_error(self):
        """An empty selection means "export everything", which the caller represents as no paths at all."""
        self.assertPathsValid(StatusSerializer, [])

    # -- custom fields ---------------------------------------------------------
    def create_custom_field(self, key, model):
        custom_field = CustomField.objects.create(key=key, label=key, type=CustomFieldTypeChoices.TYPE_TEXT)
        custom_field.validated_save()
        custom_field.content_types.set([ContentType.objects.get_for_model(model)])
        return custom_field

    def test_validate__custom_field_reference(self):
        """`cf_<key>` names a custom field, which lives under the serializer's `custom_fields` dict."""
        self.create_custom_field("my_field", Device)
        self.assertPathsValid(DeviceSerializer, ["name", "cf_my_field"])

    def test_validate__unknown_custom_field_is_rejected(self):
        """A `cf_<key>` naming no custom field of this model is an error, not a silently empty column."""
        self.create_custom_field("my_field", Device)
        self.assertPathsInvalid(
            DeviceSerializer, ["name", "cf_no_such_field"], '"cf_no_such_field": unknown custom field "no_such_field"'
        )

    def test_validate__custom_field_of_another_model_is_rejected(self):
        """Custom fields are per content type, so one belonging to another model does not count."""
        self.create_custom_field("my_field", Device)
        self.assertPathsInvalid(StatusSerializer, ["cf_my_field"], 'unknown custom field "my_field"')

    def test_validate__custom_field_reference_on_a_model_without_any(self):
        self.assertPathsInvalid(DeviceSerializer, ["cf_anything"], 'unknown custom field "anything"')

    def test_validate__bare_custom_field_prefix(self):
        """`cf_` on its own names no key, so it is reported the same way as any other unknown one."""
        self.assertPathsInvalid(DeviceSerializer, ["cf_"], 'unknown custom field ""')

    def test_validate__custom_field_reference_cannot_be_expanded(self):
        """Reported as unexpandable rather than unknown: the shape of the path is wrong either way."""
        self.create_custom_field("my_field", Device)
        self.assertPathsInvalid(
            DeviceSerializer,
            ["cf_my_field__nested"],
            '"cf_my_field__nested": custom-field references cannot be expanded',
        )

    # -- what may be traversed -------------------------------------------------
    def test_validate__traversal_of_a_field_declaring_no_target(self):
        """A relation is resolved from the model, so a field that names no target is still traversable.

        `ObjectChangeSerializer.changed_object_type` is a `ContentTypeField`: no queryset, no
        `_related_model`. The model knows it is a foreign key to `ContentType` all the same, so the segment
        past it is checked against `ContentTypeSerializer` rather than waved through.
        """
        self.assertPathsValid(ObjectChangeSerializer, ["changed_object_type__app_label"])
        self.assertPathsInvalid(
            ObjectChangeSerializer, ["changed_object_type__utter_nonsense"], 'unknown field "utter_nonsense"'
        )

    def test_validate__identity_field_is_not_a_relation(self):
        """`url` is a `RelatedField` subclass but not a relation: it is the object's own address.

        Sourced from `"*"` rather than a model field, so there is nothing to traverse to -- and it is
        stripped from documents entirely (`EXCLUDED_DOCUMENT_FIELDS`), so nothing downstream would have
        objected either.
        """
        self.assertIsInstance(
            DeviceSerializer(context={"request": None, "depth": 0}).fields["url"], serializers.RelatedField
        )
        self.assertPathsInvalid(
            DeviceSerializer, ["url__anything"], '"url" is not a related field and cannot be expanded'
        )

    def test_validate__write_only_field_is_rejected(self):
        """A write-only field is in `fields` but never in the output, so naming it has to be an error.

        `UserSerializer.password` is the only write-only field in core whose name is also a model field.
        Accepted, it would produce a file with no `password` column and no warning that one was dropped --
        or, as the only selection, a file with no columns at all.
        """
        serializer = UserSerializer(context={"request": None, "depth": 0}, exporting=True)
        self.assertIn("password", serializer.fields)
        self.assertNotIn("password", [field.field_name for field in serializer._readable_fields])
        self.assertPathsInvalid(
            UserSerializer, ["password"], '"password": "password" is write-only and cannot be exported'
        )
        # ...and it is reported rather than quietly ignored when mixed with exportable fields
        self.assertPathsInvalid(UserSerializer, ["username", "password"], "is write-only")

    def test_validate__write_only_relation_is_rejected(self):
        """The same for a write-only relation, which the remaining four in core all are."""
        self.assertTrue(VLANSerializer(context={"request": None, "depth": 0}).fields["location"].write_only)
        self.assertPathsInvalid(VLANSerializer, ["vid", "location"], '"location" is write-only')

    def test_validate__serializer_only_relation_is_not_traversable(self):
        """A relation the serializer invents has no model field to traverse, so it cannot be expanded.

        `CableSerializer.termination_a_type` is a readable `ContentTypeField` left over from the model's
        pre-`terminations` shape, and it *does* carry a queryset -- so resolving the target from the
        serializer field would happily validate `termination_a_type__app_label` against
        `ContentTypeSerializer`, even though the lookup the export emits for it has nothing to resolve.
        """
        field = CableSerializer(context={"request": None, "depth": 0}, exporting=True).fields["termination_a_type"]
        self.assertFalse(field.write_only)
        self.assertIsNotNone(field.queryset)  # a target is available, but not from the model
        with self.assertRaises(FieldDoesNotExist):
            Cable._meta.get_field("termination_a_type")
        self.assertPathsInvalid(
            CableSerializer,
            ["termination_a_type__app_label"],
            '"termination_a_type" is not a related field and cannot be expanded',
        )

    def test_validate__traversal_is_deferred_when_the_related_model_has_no_serializer(self):
        """The one remaining deferral: a related model with no serializer is left to the database.

        No core model has such a relation today, so this patches the lookup to prove the branch; an App
        that registers a model without a serializer is the real case.
        """
        with mock.patch(
            "nautobot.core.api.import_export.get_serializer_for_model",
            side_effect=SerializerNotFound("no serializer"),
        ):
            self.assertPathsValid(DeviceSerializer, ["device_type__anything_at_all"])

    # -- permission on traversed models ----------------------------------------
    def limited_user(self):
        """A user who may view Devices but nothing they relate to."""
        user = User.objects.create(username="paths-limited-user", is_superuser=False)
        permission = ObjectPermission.objects.create(name="View devices", actions=["view"])
        permission.users.add(user)
        permission.object_types.add(ContentType.objects.get_for_model(Device))
        return user

    def test_validate__user_is_required(self):
        """`user` is keyword-only and mandatory, so enforcement cannot be skipped by omission."""
        with self.assertRaises(TypeError):
            validate_field_paths(DeviceSerializer, ["device_type__model"])  # pylint: disable=missing-kwoa

    def test_validate__unviewable_relation_cannot_be_traversed(self):
        self.assertPathsInvalid(
            DeviceSerializer,
            ["device_type__model"],
            '"device_type__model": requires permission to view dcim.devicetype',
            'only "id" may be selected',
            user=self.limited_user(),
        )

    def test_validate__id_of_an_unviewable_relation_is_allowed(self):
        self.assertPathsValid(DeviceSerializer, ["name", "device_type__id"], user=self.limited_user())

    def test_validate__viewable_relation_can_be_traversed(self):
        """A superuser holds every permission, so the gate never fires for one."""
        self.assertPathsValid(DeviceSerializer, ["device_type__manufacturer__name"], user=self.superuser)

    def test_validate__permission_is_checked_before_the_field_exists(self):
        """The error must not depend on whether the named field exists, or it becomes an oracle.

        A user who cannot view DeviceTypes learns nothing about which fields one has.
        """
        user = self.limited_user()
        real = self.assertPathsInvalid(DeviceSerializer, ["device_type__model"], user=user)
        bogus = self.assertPathsInvalid(DeviceSerializer, ["device_type__no_such_field"], user=user)
        self.assertNotIn("unknown field", bogus)
        self.assertEqual(real.replace("device_type__model", "X"), bogus.replace("device_type__no_such_field", "X"))


class ExportRelatedObjectPermissionTests(ImportExportJobTestCase):
    """What a user who cannot view a related model can nonetheless learn about it from an export.

    A selection must not become a way to read a model the user has no permission to view. This is the
    export-path analogue of what [GHSA-h8rv-c7c8-cvmx] fixed for `?depth=N` in the REST API; that fix does
    not reach here, because an export flattens related objects into database lookups rather than going
    through `return_nested_serializer_data_based_on_depth`, and `user_can_view_object` returns True outright
    when there is no request -- which is exactly how an export serializes.
    """

    def test_perm__selection_cannot_name_fields_of_an_unviewable_relation(self):
        """Naming a field of a related model the user cannot view fails the Job.

        Without this, `export_fields` would be a way to read `users.User` with only
        `dcim.view_rackreservation`: a default export of a RackReservation emits `user__username` alone, so
        `email` and `is_superuser` are reachable only through a selection.
        """
        limited_user = self.create_rack_reservation_and_limited_user()
        job_result = self.run_export(
            model=RackReservation,
            username=limited_user.username,
            export_fields="description,user__email,user__is_superuser",
            expected_status=JobResultStatusChoices.STATUS_FAILURE,
        )
        self.assertJobLogEntry(job_result, "requires permission to view users.user", level=LogLevelChoices.LOG_ERROR)
        self.assertFalse(job_result.files.exists())

    def test_perm__id_of_an_unviewable_relation_is_allowed(self):
        """`id` stays available: it is what an unviewable relation is reduced to.

        `display` is meant to join it, but is not yet selectable through a relation for anyone -- see
        `test_select__non_column_field_cannot_be_selected_through_a_relation`.
        """
        limited_user = self.create_rack_reservation_and_limited_user()
        rows = self.export_rows(
            self.run_export(model=RackReservation, username=limited_user.username, export_fields="description,user__id")
        )
        self.assertEqual(list(rows[0].keys()), ["description", "user__id"])
        self.assertEqual(rows[0]["user__id"], str(User.objects.get(username="reservation-owner").pk))

    def test_perm__a_permitted_relation_may_be_traversed(self):
        """Granting `users.view_user` makes the very same selection succeed.

        A positive control for the test above, which would also pass if the gate simply refused every
        traversal; this pins that what it checks is the permission.
        """
        limited_user = self.create_rack_reservation_and_limited_user()
        permission = ObjectPermission.objects.create(name="View users", actions=["view"])
        permission.users.add(limited_user)
        permission.object_types.add(ContentType.objects.get_for_model(User))
        rows = self.export_rows(
            self.run_export(
                model=RackReservation, username=limited_user.username, export_fields="description,user__email"
            )
        )
        self.assertEqual(rows[0]["user__email"], "owner@example.com")


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
        self.assertEqual(
            lines[0],
            f"# nautobot_import_version={IMPORT_DOCUMENT_VERSION}; model=dcim.devicetype; "
            "match_fields=manufacturer__name model",
        )
        self.assertEqual(lines[1], "model,manufacturer__name")
        self.assertEqual(lines[2], "Selection DT,Selection Mfr")

    # -- the match_fields directive under a selection ---------------------------
    # A selection can leave the file unable to identify its own records, in which case the export must not
    # stamp a match key. `MatchFieldsTests` covers the rule; these check what reaches the file.

    def test_select__directive_drops_the_key_when_the_selection_omits_it(self):
        """Selecting only non-key fields still writes a directive row, but with no match key in it."""
        self.create_status(name="test_selection_status", color="445566")
        lines = self.export_lines(self.run_export(query_string="name=test_selection_status", export_fields="color"))
        self.assertEqual(lines[0], f"# nautobot_import_version={IMPORT_DOCUMENT_VERSION}; model=extras.status")
        self.assertEqual(lines[1], "color")
        self.assertEqual(lines[2], "445566")

    def test_select__directive_dropped_when_a_composite_key_is_half_covered(self):
        """`model` identifies a DeviceType only together with its manufacturer."""
        mfr = Manufacturer.objects.create(name="Half Key Mfr")
        DeviceType.objects.create(manufacturer=mfr, model="Half Key DT", u_height=1)
        lines = self.export_lines(
            self.run_export(model=DeviceType, query_string="model=Half+Key+DT", export_fields="model")
        )
        self.assertEqual(lines[0], f"# nautobot_import_version={IMPORT_DOCUMENT_VERSION}; model=dcim.devicetype")
        self.assertEqual(lines[1], "model")

    def test_select__relation_head_covers_the_key_it_expands_to(self):
        """Selecting the bare relation stamps the key, and the column it names is really in the file.

        The directive would otherwise be a lie: it claims `manufacturer__name`, which is not what was
        typed -- it is what the head expands to.
        """
        mfr = Manufacturer.objects.create(name="Head Key Mfr")
        DeviceType.objects.create(manufacturer=mfr, model="Head Key DT", u_height=1)
        lines = self.export_lines(
            self.run_export(model=DeviceType, query_string="model=Head+Key+DT", export_fields="model,manufacturer")
        )
        self.assertEqual(
            lines[0],
            f"# nautobot_import_version={IMPORT_DOCUMENT_VERSION}; model=dcim.devicetype; "
            "match_fields=manufacturer__name model",
        )
        self.assertEqual(lines[1], "model,manufacturer__name")  # the claimed column is present
        self.assertEqual(lines[2], "Head Key DT,Head Key Mfr")

    def test_select__nested_selection_that_misses_the_key(self):
        """A nested selection replaces the relation's natural-key columns, so the key is not covered."""
        mfr = Manufacturer.objects.create(name="Miss Key Mfr", description="a description")
        DeviceType.objects.create(manufacturer=mfr, model="Miss Key DT", u_height=1)
        lines = self.export_lines(
            self.run_export(
                model=DeviceType,
                query_string="model=Miss+Key+DT",
                export_fields="model,manufacturer__description",
            )
        )
        self.assertEqual(lines[0], f"# nautobot_import_version={IMPORT_DOCUMENT_VERSION}; model=dcim.devicetype")
        self.assertEqual(lines[1], "model,manufacturer__description")
        self.assertNotIn("manufacturer__name", lines[1])

    def test_select__document_match_fields(self):
        """The document metadata follows the same rule as the CSV directive."""
        mfr = Manufacturer.objects.create(name="Doc Key Mfr")
        DeviceType.objects.create(manufacturer=mfr, model="Doc Key DT", u_height=1)
        covered = self.export_document(
            self.run_export(
                model=DeviceType,
                query_string="model=Doc+Key+DT",
                export_format="json",
                export_fields="model,manufacturer__name",
            )
        )
        self.assertEqual(covered["match_fields"], ["manufacturer__name", "model"])
        self.assertEqual(list(covered.keys()), ["nautobot_import_version", "model", "match_fields", "records"])

        uncovered = self.export_document(
            self.run_export(
                model=DeviceType,
                query_string="model=Doc+Key+DT",
                export_format="json",
                export_fields="model",
            )
        )
        # `match_fields` is the only thing missing; the rest of the metadata is unaffected
        self.assertEqual(list(uncovered.keys()), ["nautobot_import_version", "model", "records"])
        # ...and the records really do carry only the selected field, so the dropped key is not recoverable
        self.assertEqual(uncovered["records"], [{"model": "Doc Key DT"}])

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

    def test_select__export_only_m2m_column(self):
        """An opt-in M2M column can be named explicitly, not just inherited from the default field set.

        `software_image_files` is only readable under `exporting=True`, which is why validation has to
        instantiate the serializer the same way the export does.
        """
        software_image_files = self.create_device_type_with_software_image_files()
        rows = self.export_rows(
            self.run_export(
                model=DeviceType,
                query_string="model=M2M+Composite+DT",
                export_fields="model,software_image_files",
            )
        )
        self.assertEqual(list(rows[0].keys()), ["model", "software_image_files"])
        self.assertEqual(rows[0]["model"], "M2M Composite DT")
        self.assertEqual(
            json.loads(rows[0]["software_image_files"]),
            [
                {
                    "image_file_name": image_file.image_file_name,
                    "software_version__platform__name": image_file.software_version.platform.name,
                    "software_version__version": image_file.software_version.version,
                }
                for image_file in software_image_files
            ],
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

    # -- custom fields ---------------------------------------------------------
    # A `cf_<key>` entry is the only selection path that names something the serializer has no field for:
    # `OptInFieldsMixin` can only translate it into the `custom_fields` dict, which holds *every* custom
    # field of the object. CSV narrows that back down to the selected keys when it derives its `cf_*`
    # headers; the document formats do not, which is what `test_select__custom_field_in_a_document` pins.

    def test_select__custom_field_column(self):
        """A `cf_<key>` entry produces exactly that custom field's column, positioned by the selection."""
        self.create_status_with_custom_fields()
        lines = self.export_lines(
            self.run_export(query_string="name=Custom+Field+Status", export_fields="name,cf_export_cf_a")
        )
        self.assertEqual(lines[1], "name,cf_export_cf_a")  # cf_export_cf_b was not selected
        self.assertEqual(lines[2], "Custom Field Status,A value")

    def test_select__custom_field_ordering_is_honored(self):
        """A selected custom field takes its requested position, ahead of a concrete field."""
        self.create_status_with_custom_fields()
        lines = self.export_lines(
            self.run_export(query_string="name=Custom+Field+Status", export_fields="cf_export_cf_a,name")
        )
        self.assertEqual(lines[1], "cf_export_cf_a,name")
        self.assertEqual(lines[2], "A value,Custom Field Status")

    def test_select__custom_field_only_suppresses_the_match_directive(self):
        """Selecting only a custom field leaves the natural key uncovered, so no match key is stamped."""
        self.create_status_with_custom_fields()
        lines = self.export_lines(
            self.run_export(query_string="name=Custom+Field+Status", export_fields="cf_export_cf_a")
        )
        self.assertEqual(lines[0], f"# nautobot_import_version={IMPORT_DOCUMENT_VERSION}; model=extras.status")
        self.assertNotIn("match_fields", lines[0])
        self.assertEqual(lines[1], "cf_export_cf_a")
        self.assertEqual(lines[2], "A value")

    def test_select__one_custom_field_of_several(self):
        """Only the named custom fields appear, whichever subset is asked for."""
        self.create_status_with_custom_fields()
        lines = self.export_lines(
            self.run_export(query_string="name=Custom+Field+Status", export_fields="cf_export_cf_b")
        )
        self.assertEqual(lines[1], "cf_export_cf_b")
        self.assertEqual(lines[2], "B value")

    def test_select__custom_field_in_a_document(self):
        """A named custom field becomes a top-level `cf_<key>` in a document, not a nested dict entry.

        One custom field cannot be named *inside* `custom_fields`, so a `cf_<key>` selection switches the
        document to the same flat spelling CSV uses.
        """
        self.create_status_with_custom_fields()
        for export_format in ("json", "yaml"):
            with self.subTest(export_format=export_format):
                doc = self.export_document(
                    self.run_export(
                        query_string="name=Custom+Field+Status",
                        export_format=export_format,
                        export_fields="name,cf_export_cf_a",
                    )
                )
                self.assertEqual(doc["records"], [{"name": "Custom Field Status", "cf_export_cf_a": "A value"}])

    def test_select__custom_fields_dict_in_a_document(self):
        """Naming `custom_fields` keeps the nested dict, with every custom field in it."""
        self.create_status_with_custom_fields()
        doc = self.export_document(
            self.run_export(
                query_string="name=Custom+Field+Status",
                export_format="json",
                export_fields="name,custom_fields",
            )
        )
        self.assertEqual(
            doc["records"],
            [{"name": "Custom Field Status", "custom_fields": {"export_cf_a": "A value", "export_cf_b": "B value"}}],
        )

    def test_select__no_selection_keeps_the_custom_fields_dict_in_a_document(self):
        """With no selection the document is unchanged: custom fields stay nested."""
        self.create_status_with_custom_fields()
        doc = self.export_document(self.run_export(query_string="name=Custom+Field+Status", export_format="json"))
        self.assertEqual(doc["records"][0]["custom_fields"], {"export_cf_a": "A value", "export_cf_b": "B value"})

    def test_select__custom_fields_dict_may_be_named_directly(self):
        """Naming `custom_fields` asks for all of them, which is what both formats already produce."""
        self.create_status_with_custom_fields()
        lines = self.export_lines(
            self.run_export(query_string="name=Custom+Field+Status", export_fields="name,custom_fields")
        )
        self.assertEqual(lines[1], "name,cf_export_cf_a,cf_export_cf_b")
        self.assertEqual(lines[2], "Custom Field Status,A value,B value")

    def test_select__unknown_custom_field_fails(self):
        """A `cf_<key>` naming no custom field of the model fails the job rather than exporting nothing."""
        self.create_status_with_custom_fields()
        job_result = self.run_export(
            query_string="name=Custom+Field+Status",
            export_fields="name,cf_no_such_field",
            expected_status=JobResultStatusChoices.STATUS_FAILURE,
        )
        self.assertJobLogEntry(job_result, 'unknown custom field "no_such_field"', level=LogLevelChoices.LOG_ERROR)
        self.assertFalse(job_result.files.exists())

    def test_select__non_column_field_cannot_be_selected_through_a_relation(self):
        """A readable field that is not a database column fails cleanly when named through a relation.

        `display` is a model property and `url`/`object_type`/`natural_slug` are computed by the
        serializer, so none can be emitted as the database lookup a nested path becomes. Run as the default
        superuser to show this is a limit of the mechanism, not a permission check.
        """
        mfr = Manufacturer.objects.create(name="Non Column Mfr")
        DeviceType.objects.create(manufacturer=mfr, model="Non Column DT", u_height=1)
        for field_name in ("display", "url", "object_type", "natural_slug"):
            with self.subTest(field_name=field_name):
                job_result = self.run_export(
                    model=DeviceType,
                    query_string="model=Non+Column+DT",
                    export_fields=f"model,manufacturer__{field_name}",
                    expected_status=JobResultStatusChoices.STATUS_FAILURE,
                )
                self.assertJobLogEntry(
                    job_result,
                    f'"{field_name}" cannot yet be selected through a relation',
                    level=LogLevelChoices.LOG_ERROR,
                )

    def test_select__non_column_field_may_be_selected_on_the_object_itself(self):
        """The same fields are fine at the root, where they are rendered rather than looked up."""
        self.create_status(name="Non Column Status", color="123456")
        rows = self.export_rows(
            self.run_export(query_string="name=Non+Column+Status", export_fields="name,display,natural_slug")
        )
        self.assertEqual(rows[0]["display"], "Non Column Status")
        self.assertEqual(list(rows[0].keys()), ["name", "display", "natural_slug"])

    def test_select__write_only_field_fails_rather_than_exporting_nothing(self):
        """Selecting a write-only field fails the job instead of writing a file missing that column.

        `VLANSerializer.location` is write-only, so it is absent from `_readable_fields`; before this was
        validated, `export_fields="location"` produced a file with no columns and no rows at all.
        """
        job_result = self.run_export(
            model=VLAN, export_fields="vid,location", expected_status=JobResultStatusChoices.STATUS_FAILURE
        )
        self.assertJobLogEntry(job_result, "is write-only and cannot be exported", level=LogLevelChoices.LOG_ERROR)
        self.assertFalse(job_result.files.exists())

    @skip("Enable in X5: needs ExportFieldsForm (export UI)")
    def test_select__form_expands_single_fk_relations(self):
        """ExportFieldsForm offers a flat, orderable list including single-FK relations expanded one level."""
        from nautobot.core.forms import ExportFieldsForm  # TODO # pylint: disable=no-name-in-module

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
