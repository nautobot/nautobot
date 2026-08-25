import csv
import io
from unittest.mock import patch
import uuid

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings, RequestFactory, SimpleTestCase, tag, TestCase
from django.urls import reverse

from nautobot.core.api import serializers as core_api_serializers
from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_TYPE, VARBINARY_IP_FIELD_REPR_OF_CSV_NO_OBJECT
from nautobot.dcim.api.serializers import DeviceSerializer
from nautobot.dcim.models.devices import Controller, Device, DeviceType, Platform, SoftwareImageFile, SoftwareVersion
from nautobot.dcim.models.locations import Location
from nautobot.extras.models.roles import Role
from nautobot.extras.models.statuses import Status
from nautobot.extras.models.tags import Tag
from nautobot.ipam.models import Namespace, RouteTarget, VRF
from nautobot.tenancy.models import Tenant
from nautobot.users.factory import UserFactory


class CSVParsingRelatedTestCase(TestCase):
    maxDiff = None

    def setUp(self):
        location = Location.objects.filter(
            parent__isnull=False,
            parent__parent__isnull=True,
            location_type__content_types__in=[ContentType.objects.get_for_model(Device)],
        )[0]

        devicetype = DeviceType.objects.first()
        devicerole = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        tags = Tag.objects.get_for_model(Device).all()[:3]
        Controller.objects.filter(controller_device__isnull=False).delete()
        Device.objects.all().delete()
        self.device = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestDevice1",
            status=device_status,
            location=location,
        )
        self.device.tags.set(tags)

        self.device2 = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestDevice2",
            status=device_status,
            location=location,
            tenant=Tenant.objects.create(name="Tenant"),
        )

    @override_settings(ALLOWED_HOSTS=["*"])
    def test_csv_export_related_serializer_methods(self):
        """Test special methods in Serializer related to the parsing of CSV."""
        device = self.device

        request = RequestFactory().get(reverse("dcim-api:device-list"), ACCEPT="text/csv")
        setattr(request, "accepted_media_type", ["text/csv"])

        serializer = DeviceSerializer(instance=device, context={"request": request})

        with self.subTest("Assert If CSV Request"):
            self.assertTrue(serializer._is_csv_request())

        with self.subTest(""):
            expected_related_natural_key_fields = [
                "parent_bay__name",
                "parent_bay__device__name",
                "parent_bay__device__tenant__name",
                "parent_bay__device__location__name",
                *[
                    f"parent_bay__device__location__{'parent__' * depth}name"
                    for depth in range(1, Location.objects.max_tree_depth() + 1)
                ],  # Location max_tree_depth is based on factory data so this has to be generated dynamically
                "vc_master_for__name",
                "local_config_context_schema__name",
                "device_type__manufacturer__name",
                "device_type__model",
                "status__name",
                "role__name",
                "tenant__name",
                "platform__name",
                "location__name",
                *[
                    f"location__{'parent__' * depth}name" for depth in range(1, Location.objects.max_tree_depth() + 1)
                ],  # Location max_tree_depth is based on factory data so this has to be generated dynamically
                "rack__name",
                "rack__rack_group__name",
                "rack__rack_group__location__name",
                *[
                    f"rack__rack_group__location__{'parent__' * depth}name"
                    for depth in range(1, Location.objects.max_tree_depth() + 1)
                ],  # Location max_tree_depth is based on factory data so this has to be generated dynamically
                "primary_ip4__parent__namespace__name",
                "primary_ip4__host",
                "primary_ip6__parent__namespace__name",
                "primary_ip6__host",
                "virtual_chassis__name",
                "controller_managed_device_group__name",
                "device_redundancy_group__name",
                "software_version__platform__name",
                "software_version__version",
                "secrets_group__name",
            ]
            self.assertEqual(
                sorted(serializer._get_related_fields_natural_key_field_lookups()),
                sorted(expected_related_natural_key_fields),
            )

        with self.subTest("Assert natural_keys_values dict is valid"):
            natural_keys_values = serializer.natural_keys_values
            self.assertEqual(len(natural_keys_values), 1)

            # Assert FK Field lookups without an object is swapped for None
            field_without_values = [
                "parent_bay",
                "vc_master_for",
                "local_config_context_schema",
                "tenant",
                "platform",
                "rack",
                "primary_ip4",
                "primary_ip6",
                "virtual_chassis",
                "controller_managed_device_group",
                "device_redundancy_group",
                "secrets_group",
            ]
            for field_name in field_without_values:
                field_lookups = Device._meta.get_field(field_name).related_model.natural_key_field_lookups
                for lookup in field_lookups:
                    self.assertIn(
                        natural_keys_values[self.device.pk][f"{field_name}__{lookup}"],
                        [CSV_NO_OBJECT, VARBINARY_IP_FIELD_REPR_OF_CSV_NO_OBJECT],
                    )

            # Assert FK Field lookups with an object
            self.assertEqual(device.device_type.model, natural_keys_values[self.device.pk]["device_type__model"])
            self.assertEqual(
                device.device_type.manufacturer.name,
                natural_keys_values[self.device.pk]["device_type__manufacturer__name"],
            )
            self.assertEqual(device.status.name, natural_keys_values[self.device.pk]["status__name"])
            self.assertEqual(device.role.name, natural_keys_values[self.device.pk]["role__name"])

            self.assertEqual(device.location.name, natural_keys_values[self.device.pk]["location__name"])
            self.assertEqual(device.location.parent.name, natural_keys_values[self.device.pk]["location__parent__name"])
            self.assertEqual(natural_keys_values[self.device.pk]["location__parent__parent__name"], CSV_NO_OBJECT)
            self.assertEqual(
                natural_keys_values[self.device.pk]["location__parent__parent__parent__name"], CSV_NO_OBJECT
            )
            self.assertEqual(
                natural_keys_values[self.device.pk]["location__parent__parent__parent__parent__name"], CSV_NO_OBJECT
            )

        expected_location_nested_lookup_values = {
            f"location__{'parent__' * depth}name": CSV_NO_OBJECT
            for depth in range(2, Location.objects.max_tree_depth() + 1)
        }  # Location max_tree_depth is based on factory data so this has to be generated dynamically
        with self.subTest("Get the natural lookup field and its value"):
            # For Location
            location_lookup_value = serializer._get_natural_key_lookups_value_for_field(
                "location", natural_keys_values[self.device.pk]
            )
            self.assertEqual(
                location_lookup_value,
                {
                    "location__name": device.location.name,
                    "location__parent__name": device.location.parent.name,
                    **expected_location_nested_lookup_values,
                },
            )

            # For Status
            status_lookup_value = serializer._get_natural_key_lookups_value_for_field(
                "status", natural_keys_values[self.device.pk]
            )
            self.assertEqual(status_lookup_value, {"status__name": device.status.name})

            # For Rack, since `device.rack` does not exists, all rack natural_key_lookups should be `NoObject`
            rack_lookup_value = serializer._get_natural_key_lookups_value_for_field(
                "rack", natural_keys_values[self.device.pk]
            )
            expected_rack_group_nested_lookup_values = {
                f"rack__rack_group__location__{'parent__' * depth}name": CSV_NO_OBJECT
                for depth in range(1, Location.objects.max_tree_depth() + 1)
            }  # Location max_tree_depth is based on factory data so this has to be generated dynamically
            self.assertEqual(
                rack_lookup_value,
                {
                    "rack__name": CSV_NO_OBJECT,
                    "rack__rack_group__location__name": CSV_NO_OBJECT,
                    **expected_rack_group_nested_lookup_values,
                    "rack__rack_group__name": CSV_NO_OBJECT,
                },
            )

        with self.subTest("To Serializer Representation"):
            expected_parent_bay_nested_lookup_values = {
                f"parent_bay__device__location__{'parent__' * depth}name": CSV_NO_OBJECT
                for depth in range(1, Location.objects.max_tree_depth() + 1)
            }  # Location max_tree_depth is based on factory data so this has to be generated dynamically
            expected_data = {
                "id": str(device.pk),
                "object_type": "dcim.device",
                "display": device.display,
                "url": f"http://testserver/api/dcim/devices/{device.pk}/",
                "natural_slug": device.natural_slug,
                "face": CSV_NULL_TYPE,
                "local_config_context_data": CSV_NULL_TYPE,
                "local_config_context_data_owner_object_id": CSV_NULL_TYPE,
                "name": device.name,
                "serial": "",
                "asset_tag": CSV_NULL_TYPE,
                "position": CSV_NULL_TYPE,
                "device_redundancy_group_priority": CSV_NULL_TYPE,
                "vc_position": CSV_NULL_TYPE,
                "vc_priority": CSV_NULL_TYPE,
                "comments": "",
                "local_config_context_schema__name": CSV_NO_OBJECT,
                "local_config_context_data_owner_content_type": CSV_NULL_TYPE,
                "device_type__manufacturer__name": device.device_type.manufacturer.name,
                "device_type__model": device.device_type.model,
                "status__name": device.status.name,
                "role__name": device.role.name,
                "tenant__name": CSV_NO_OBJECT,
                "platform__name": CSV_NO_OBJECT,
                "location__name": device.location.name,
                "location__parent__name": device.location.parent.name,
                **expected_location_nested_lookup_values,
                "rack__name": CSV_NO_OBJECT,
                "rack__rack_group__name": CSV_NO_OBJECT,
                "rack__rack_group__location__name": CSV_NO_OBJECT,
                **expected_rack_group_nested_lookup_values,
                "primary_ip4__parent__namespace__name": CSV_NO_OBJECT,
                "primary_ip4__host": CSV_NO_OBJECT,
                "primary_ip6__parent__namespace__name": CSV_NO_OBJECT,
                "primary_ip6__host": CSV_NO_OBJECT,
                "virtual_chassis__name": CSV_NO_OBJECT,
                "controller_managed_device_group__name": CSV_NO_OBJECT,
                "device_redundancy_group__name": CSV_NO_OBJECT,
                "software_version__platform__name": CSV_NO_OBJECT,
                "software_version__version": CSV_NO_OBJECT,
                "secrets_group__name": CSV_NO_OBJECT,
                "parent_bay__name": CSV_NO_OBJECT,
                "parent_bay__device__name": CSV_NO_OBJECT,
                "parent_bay__device__tenant__name": CSV_NO_OBJECT,
                "parent_bay__device__location__name": CSV_NO_OBJECT,
                **expected_parent_bay_nested_lookup_values,
            }
            serializer_data = serializer.data

            tags = sorted(serializer_data.pop("tags"))
            instance_tags_pk = sorted(device.tags.values_list("name", flat=True))
            self.assertEqual(tags, instance_tags_pk)

            serializer_data.pop("notes_url")
            serializer_data.pop("custom_fields")
            serializer_data.pop("created")
            serializer_data.pop("last_updated")
            self.assertDictEqual(expected_data, dict(serializer_data))

    @override_settings(ALLOWED_HOSTS=["*"])
    def test_csv_export_chunked_natural_key_queries_produce_same_result(self):
        """Verify `natural_keys_values` is correctly calculated regardless of the CSV_NATURAL_KEY_QUERY_CHUNK value."""
        request = RequestFactory().get(reverse("dcim-api:device-list"), ACCEPT="text/csv")
        setattr(request, "accepted_media_type", ["text/csv"])

        # Baseline: one big query (chunk size large enough to fit every lookup).
        with patch.object(core_api_serializers, "CSV_NATURAL_KEY_QUERY_CHUNK", 1000):
            baseline = DeviceSerializer(instance=self.device, context={"request": request}).natural_keys_values

        # Chunked: many small queries, exercising the per-pk dict merge path.
        with patch.object(core_api_serializers, "CSV_NATURAL_KEY_QUERY_CHUNK", 3):
            chunked = DeviceSerializer(instance=self.device, context={"request": request}).natural_keys_values

        self.assertEqual(baseline, chunked)

    @override_settings(ALLOWED_HOSTS=["*"])
    def test_round_trip_export_import(self):
        """"""
        user = UserFactory.create()
        user.is_superuser = True
        user.is_active = True
        user.save()

        self.client.force_login(user)
        response = self.client.get(reverse("dcim-api:device-list") + "?format=csv")
        self.assertEqual(response.status_code, 200)
        response_data = response.content.decode(response.charset)

        # parse the csv data
        csv_reader = csv.DictReader(response_data.splitlines())
        # remove the 'id' column so that all the items are imported new
        fieldnames = [field for field in csv_reader.fieldnames if field != "id"]
        # read all entries into a list
        response_csv = list(csv_reader)

        # mutate our data for testing purposes
        for row in response_csv:
            if row["name"] == "TestDevice1":
                row["name"] = "TestDevice3"
            elif row["name"] == "TestDevice2":
                row["name"] = ""

        # prep our data to write out
        with io.StringIO() as import_csv:
            writer = csv.DictWriter(import_csv, fieldnames=fieldnames)
            writer.writeheader()
            for row in response_csv:
                filtered_row = {key: row[key] for key in fieldnames}
                writer.writerow(filtered_row)
            data = {"csv_data": import_csv.getvalue()}
        url = reverse("dcim:device_import")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        # uploading the CSV always returns a 200 code with a page with an error message on it
        # ensure we don't have that error message
        self.assertNotIn("FORM-ERROR", response.content.decode(response.charset))
        self.assertEqual(Device.objects.count(), 4)

        # Assert TestDevice3 got created with the right fields
        device3 = Device.objects.get(
            name="TestDevice3",
            location=self.device.location,
            device_type=self.device.device_type,
            role=self.device.role,
            status=self.device.status,
            tenant=None,
        )
        self.assertEqual(device3.tags.count(), self.device.tags.count())

        # Assert device without name got created with the right fields
        device4 = Device.objects.get(
            name=None,
            location=self.device2.location,
            device_type=self.device2.device_type,
            role=self.device2.role,
            status=self.device2.status,
            tenant=self.device2.tenant,
        )
        self.assertEqual(device4.tags.count(), 0)

    @override_settings(ALLOWED_HOSTS=["*"])
    def test_m2m_field_import(self):
        """Test CSV import of M2M field."""

        platform = Platform.objects.first()
        software_version_status = Status.objects.get_for_model(SoftwareVersion).first()
        software_image_file_status = Status.objects.get_for_model(SoftwareImageFile).first()

        software_version = SoftwareVersion.objects.create(
            platform=platform, version="Test version 1.0.0", status=software_version_status
        )
        software_image_files = (
            SoftwareImageFile.objects.create(
                software_version=software_version,
                image_file_name="software_image_file_qs_test_1.bin",
                status=software_image_file_status,
            ),
            SoftwareImageFile.objects.create(
                software_version=software_version,
                image_file_name="software_image_file_qs_test_2.bin",
                status=software_image_file_status,
                default_image=True,
            ),
            SoftwareImageFile.objects.create(
                software_version=software_version,
                image_file_name="software_image_file_qs_test_3.bin",
                status=software_image_file_status,
            ),
        )

        user = UserFactory.create()
        user.is_superuser = True
        user.is_active = True
        user.save()
        self.client.force_login(user)

        with self.subTest("Import M2M field using list of UUIDs"):
            import_data = f"""name,device_type,location,role,status,software_image_files
TestDevice5,{self.device.device_type.pk},{self.device.location.pk},{self.device.role.pk},{self.device.status.pk},"{software_image_files[0].pk},{software_image_files[1].pk}"
"""
            data = {"csv_data": import_data}
            url = reverse("dcim:device_import")
            response = self.client.post(url, data)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(Device.objects.count(), 3)

            # Assert TestDevice5 got created with the right fields
            device5 = Device.objects.get(
                name="TestDevice5",
                location=self.device.location,
                device_type=self.device.device_type,
                role=self.device.role,
                status=self.device.status,
                tenant=None,
            )
            self.assertEqual(device5.software_image_files.count(), 2)

        with self.subTest("Import M2M field using multiple identifying fields"):
            import_data = f"""name,device_type,location,role,status,software_image_files__software_version,software_image_files__image_file_name
TestDevice6,{self.device.device_type.pk},{self.device.location.pk},{self.device.role.pk},{self.device.status.pk},"{software_version.pk},{software_version.pk}","{software_image_files[0].image_file_name},{software_image_files[1].image_file_name}"
"""
            data = {"csv_data": import_data}
            url = reverse("dcim:device_import")
            response = self.client.post(url, data)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(Device.objects.count(), 4)

            # Assert TestDevice5 got created with the right fields
            device6 = Device.objects.get(
                name="TestDevice6",
                location=self.device.location,
                device_type=self.device.device_type,
                role=self.device.role,
                status=self.device.status,
                tenant=None,
            )
            self.assertEqual(device6.software_image_files.count(), 2)

        with self.subTest("Import M2M field using incorrect number of values"):
            import_data = f"""name,device_type,location,role,status,software_image_files__software_version,software_image_files__image_file_name
TestDevice7,{self.device.device_type.pk},{self.device.location.pk},{self.device.role.pk},{self.device.status.pk},"{software_version.pk},{software_version.pk}","{software_image_files[0].image_file_name},{software_image_files[1].image_file_name},{software_image_files[2].image_file_name}"
"""
            data = {"csv_data": import_data}
            url = reverse("dcim:device_import")
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Incorrect number of values provided for the software_image_files field")
            self.assertEqual(Device.objects.count(), 4)


@tag("unit")
class NaturalKeyLookupValuesTest(SimpleTestCase):
    """`_get_natural_key_lookups_value_for_field` maps raw lookup values to their export representations."""

    def _values(self, natural_key_field_instance, field_name="location", for_csv=True):
        serializer = DeviceSerializer(context={"request": None, "depth": 0}, exporting=True, force_csv=for_csv)
        return serializer._get_natural_key_lookups_value_for_field(field_name, natural_key_field_instance)

    def test_none_becomes_the_null_sentinel_for_csv(self):
        """CSV has no null type, so a null must be spelled with the in-band sentinel."""
        self.assertEqual(self._values({"location__name": None}), {"location__name": CSV_NULL_TYPE})

    def test_none_stays_none_for_documents(self):
        """JSON/YAML can express null directly, so no sentinel is emitted."""
        self.assertEqual(self._values({"location__name": None}, for_csv=False), {"location__name": None})

    def test_falsey_values_are_preserved(self):
        """0/False/"" are real values, not missing ones; only None means "no value here"."""
        self.assertEqual(
            self._values({"location__a": 0, "location__b": False, "location__c": "", "location__d": "0"}),
            {"location__a": 0, "location__b": False, "location__c": "", "location__d": "0"},
        )

    def test_no_object_sentinel_passes_through(self):
        self.assertEqual(
            self._values({"location__name": VARBINARY_IP_FIELD_REPR_OF_CSV_NO_OBJECT}),
            {"location__name": CSV_NO_OBJECT},
        )

    def test_uuid_is_stringified(self):
        value = uuid.uuid4()
        self.assertEqual(self._values({"location__id": value}), {"location__id": str(value)})

    def test_other_fields_are_ignored(self):
        self.assertEqual(self._values({"tenant__name": None, "location__name": "Campus"}), {"location__name": "Campus"})


class M2MNaturalKeyValuesTest(TestCase):
    """`_get_m2m_natural_key_values` renders an M2M field's members by natural key, for CSV export."""

    def _values(self, instance, field_name, for_csv=True):
        # `exporting` is what makes the non-default M2M fields readable here.
        serializer = get_serializer_for_model(type(instance))(
            context={"request": None, "depth": 0}, exporting=True, force_csv=for_csv
        )
        return serializer._get_m2m_natural_key_values(instance, serializer.fields[field_name])

    def test_scalar_keyed_members_join_with_commas(self):
        """RouteTarget's natural key is a single value, so members render as a comma-separated string."""
        vrf = VRF.objects.create(name="M2M NK Test VRF", namespace=Namespace.objects.first())
        for name in ("65000:101", "65000:102"):
            vrf.import_targets.add(RouteTarget.objects.create(name=name))
        self.assertEqual(sorted(self._values(vrf, "import_targets").split(",")), ["65000:101", "65000:102"])

    def test_scalar_keyed_members_stay_a_list_for_documents(self):
        """JSON/YAML keep the list, which is lossless for values containing a comma."""
        vrf = VRF.objects.create(name="M2M NK List VRF", namespace=Namespace.objects.first())
        vrf.import_targets.add(RouteTarget.objects.create(name="has,comma"))
        self.assertEqual(self._values(vrf, "import_targets", for_csv=False), ["has,comma"])

    def test_composite_keyed_members_are_natural_key_dicts(self):
        """SoftwareImageFile has a 3-part natural key, so members become the flattened dicts import resolves."""
        device = Device.objects.create(
            name="M2M NK Test Device",
            location=Location.objects.filter(location_type__name="Campus").first(),
            device_type=DeviceType.objects.first(),
            role=Role.objects.get_for_model(Device).first(),
            status=Status.objects.get_for_model(Device).first(),
        )
        software_version = SoftwareVersion.objects.first()
        device.software_image_files.add(
            SoftwareImageFile.objects.create(
                image_file_name="m2m-nk-test.bin",
                software_version=software_version,
                status=Status.objects.get_for_model(SoftwareImageFile).first(),
            )
        )
        self.assertEqual(
            self._values(device, "software_image_files"),
            [
                {
                    "image_file_name": "m2m-nk-test.bin",
                    "software_version__platform__name": software_version.platform.name,
                    "software_version__version": software_version.version,
                }
            ],
        )

    def test_no_members_is_an_empty_list(self):
        """An empty M2M yields [], which the renderer flattens to an empty cell."""
        vrf = VRF.objects.create(name="M2M NK Empty VRF", namespace=Namespace.objects.first())
        self.assertEqual(self._values(vrf, "import_targets"), [])
        self.assertEqual(
            NautobotCSVRenderer().render([{"name": "vrf1", "import_targets": []}]).splitlines()[1], "vrf1,"
        )

    def test_tags_are_the_taggit_special_case(self):
        """`tags` is a TagsManager rather than a concrete M2M, but still resolves to the comma form."""
        vrf = VRF.objects.create(name="M2M NK Tagged VRF", namespace=Namespace.objects.first())
        content_type = ContentType.objects.get_for_model(VRF)
        for name in ("m2m-nk-tag-a", "m2m-nk-tag-b"):
            tag_ = Tag.objects.create(name=name)
            tag_.content_types.add(content_type)
            vrf.tags.add(tag_)
        self.assertEqual(sorted(self._values(vrf, "tags").split(",")), ["m2m-nk-tag-a", "m2m-nk-tag-b"])

    def test_composite_members_render_as_a_json_cell(self):
        """The dict form reaches CSV as a JSON-encoded cell, which the import parser can read back."""
        rendered = NautobotCSVRenderer().render(
            [
                {
                    "name": "dev1",
                    "software_image_files": [{"image_file_name": "a.bin", "software_version__version": "1.0"}],
                }
            ]
        )
        self.assertEqual(
            rendered.splitlines()[1],
            'dev1,"[{""image_file_name"": ""a.bin"", ""software_version__version"": ""1.0""}]"',
        )
