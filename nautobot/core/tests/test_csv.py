import csv
import io

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings, RequestFactory, TestCase
from django.urls import reverse

from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_TYPE, VARBINARY_IP_FIELD_REPR_OF_CSV_NO_OBJECT
from nautobot.dcim.api.serializers import DeviceSerializer
from nautobot.dcim.models.devices import Controller, Device, DeviceType, Platform, SoftwareImageFile, SoftwareVersion
from nautobot.dcim.models.locations import Location
from nautobot.extras.models.roles import Role
from nautobot.extras.models.statuses import Status
from nautobot.extras.models.tags import Tag
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
                "cluster__name",
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

        with self.subTest("Assert Lookup Querysets is valid"):
            lookup_querysets = serializer.natural_keys_values
            self.assertEqual(lookup_querysets.count(), 1)

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
                "cluster",
                "virtual_chassis",
                "controller_managed_device_group",
                "device_redundancy_group",
                "secrets_group",
            ]
            for field_name in field_without_values:
                field_lookups = Device._meta.get_field(field_name).related_model.natural_key_field_lookups
                for lookup in field_lookups:
                    self.assertIn(
                        lookup_querysets[0][f"{field_name}__{lookup}"],
                        [CSV_NO_OBJECT, VARBINARY_IP_FIELD_REPR_OF_CSV_NO_OBJECT],
                    )

            # Assert FK Field lookups with an object
            self.assertEqual(device.device_type.model, lookup_querysets[0]["device_type__model"])
            self.assertEqual(
                device.device_type.manufacturer.name, lookup_querysets[0]["device_type__manufacturer__name"]
            )
            self.assertEqual(device.status.name, lookup_querysets[0]["status__name"])
            self.assertEqual(device.role.name, lookup_querysets[0]["role__name"])

            self.assertEqual(device.location.name, lookup_querysets[0]["location__name"])
            self.assertEqual(device.location.parent.name, lookup_querysets[0]["location__parent__name"])
            self.assertEqual(lookup_querysets[0]["location__parent__parent__name"], CSV_NO_OBJECT)
            self.assertEqual(lookup_querysets[0]["location__parent__parent__parent__name"], CSV_NO_OBJECT)
            self.assertEqual(lookup_querysets[0]["location__parent__parent__parent__parent__name"], CSV_NO_OBJECT)

        with self.subTest("Get the natural lookup field and its value"):
            # For Location
            location_lookup_value = serializer._get_natural_key_lookups_value_for_field("location", lookup_querysets[0])
            expected_location_nested_lookup_values = {
                f"location__{'parent__' * depth}name": CSV_NO_OBJECT
                for depth in range(2, Location.objects.max_tree_depth() + 1)
            }  # Location max_tree_depth is based on factory data so this has to be generated dynamically
            self.assertEqual(
                location_lookup_value,
                {
                    "location__name": device.location.name,
                    "location__parent__name": device.location.parent.name,
                    **expected_location_nested_lookup_values,
                },
            )

            # For Status
            status_lookup_value = serializer._get_natural_key_lookups_value_for_field("status", lookup_querysets[0])
            self.assertEqual(status_lookup_value, {"status__name": device.status.name})

            # For Rack, since `device.rack` does not exists, all rack natural_key_lookups should be `NoObject`
            rack_lookup_value = serializer._get_natural_key_lookups_value_for_field("rack", lookup_querysets[0])
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
                "cluster__name": CSV_NO_OBJECT,
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
