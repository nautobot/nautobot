import re

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from nautobot.core.constants import CSV_NON_TYPE, CSV_OBJECT_NOT_FOUND

from nautobot.dcim.api.serializers import DeviceSerializer
from nautobot.dcim.models.devices import Device, DeviceType
from nautobot.dcim.models.locations import Location
from nautobot.extras.models.roles import Role
from nautobot.extras.models.statuses import Status
from nautobot.extras.models.tags import Tag
from nautobot.users.factory import UserFactory


class CSVParsingRelatedTestCase(TestCase):
    def setUp(self):
        location = Location.objects.filter(parent__isnull=False, parent__parent__isnull=True).first()
        devicetype = DeviceType.objects.first()
        devicerole = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        tags = Tag.objects.get_for_model(Device).all()[:2]

        self.device = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestDevice1",
            status=device_status,
            location=location,
        )
        self.device.tags.set(tags)

        Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestDevice2",
            status=device_status,
            location=location,
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
                "parent_bay__device__location__parent__name",
                "parent_bay__device__location__parent__parent__name",
                "parent_bay__device__location__parent__parent__parent__name",
                "parent_bay__device__location__parent__parent__parent__parent__name",
                "vc_master_for__name",
                "local_config_context_schema__name",
                "local_config_context_data_owner_content_type__app_label",
                "local_config_context_data_owner_content_type__model",
                "device_type__manufacturer__name",
                "device_type__model",
                "status__name",
                "role__name",
                "tenant__name",
                "platform__name",
                "location__name",
                "location__parent__name",
                "location__parent__parent__name",
                "location__parent__parent__parent__name",
                "location__parent__parent__parent__parent__name",
                "rack__name",
                "rack__rack_group__name",
                "rack__rack_group__location__name",
                "rack__rack_group__location__parent__name",
                "rack__rack_group__location__parent__parent__name",
                "rack__rack_group__location__parent__parent__parent__name",
                "rack__rack_group__location__parent__parent__parent__parent__name",
                "primary_ip4__parent__namespace__name",
                "primary_ip4__host",
                "primary_ip6__parent__namespace__name",
                "primary_ip6__host",
                "cluster__name",
                "virtual_chassis__name",
                "device_redundancy_group__name",
                "secrets_group__name",
            ]
            # expected_related_natural_key_fields = sorted(lookup_fields_with_values + lookup_fields_without_values)
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
                "device_redundancy_group",
                "secrets_group",
            ]
            for field_name in field_without_values:
                field_lookups = Device._meta.get_field(field_name).related_model.natural_key_field_lookups
                for lookup in field_lookups:
                    self.assertEqual(lookup_querysets[0][f"{field_name}__{lookup}"], CSV_OBJECT_NOT_FOUND)

            # Assert FK Field lookups with an object
            self.assertEqual(device.device_type.model, lookup_querysets[0]["device_type__model"])
            self.assertEqual(
                device.device_type.manufacturer.name, lookup_querysets[0]["device_type__manufacturer__name"]
            )
            self.assertEqual(device.status.name, lookup_querysets[0]["status__name"])
            self.assertEqual(device.role.name, lookup_querysets[0]["role__name"])

            self.assertEqual(device.location.name, lookup_querysets[0]["location__name"])
            self.assertEqual(device.location.parent.name, lookup_querysets[0]["location__parent__name"])
            self.assertEqual(lookup_querysets[0]["location__parent__parent__name"], CSV_OBJECT_NOT_FOUND)
            self.assertEqual(lookup_querysets[0]["location__parent__parent__parent__name"], CSV_OBJECT_NOT_FOUND)
            self.assertEqual(
                lookup_querysets[0]["location__parent__parent__parent__parent__name"], CSV_OBJECT_NOT_FOUND
            )

        with self.subTest("Get the natural lookup field and its value"):
            # For Location
            location_lookup_value = serializer._get_natural_key_lookups_value_for_field("location", lookup_querysets[0])
            self.assertEqual(
                location_lookup_value,
                {"location__name": device.location.name, "location__parent__name": device.location.parent.name},
            )

            # For Status
            status_lookup_value = serializer._get_natural_key_lookups_value_for_field("status", lookup_querysets[0])
            self.assertEqual(status_lookup_value, {"status__name": device.status.name})

            # For Rack, it returns `{}` since rack has no instance/value
            rack_lookup_value = serializer._get_natural_key_lookups_value_for_field("rack", lookup_querysets[0])
            self.assertEqual(rack_lookup_value, {})

        with self.subTest("To Serializer Representation"):
            expected_data = {
                "id": str(device.pk),
                "object_type": "dcim.device",
                "display": device.name,
                "url": f"http://testserver/api/dcim/devices/{device.pk}/",
                "composite_key": device.composite_key,
                "face": CSV_NON_TYPE,
                "local_config_context_data": CSV_NON_TYPE,
                "local_config_context_data_owner_object_id": CSV_NON_TYPE,
                "name": device.name,
                "serial": "",
                "asset_tag": CSV_NON_TYPE,
                "position": CSV_NON_TYPE,
                "device_redundancy_group_priority": CSV_NON_TYPE,
                "vc_position": CSV_NON_TYPE,
                "vc_priority": CSV_NON_TYPE,
                "comments": "",
                "local_config_context_schema": CSV_NON_TYPE,
                "local_config_context_data_owner_content_type": CSV_NON_TYPE,
                "device_type__manufacturer__name": device.device_type.manufacturer.name,
                "device_type__model": device.device_type.model,
                "status__name": device.status.name,
                "role__name": device.role.name,
                "tenant": CSV_NON_TYPE,
                "platform": CSV_NON_TYPE,
                "location__name": device.location.name,
                "location__parent__name": device.location.parent.name,
                "rack": CSV_NON_TYPE,
                "primary_ip4": CSV_NON_TYPE,
                "primary_ip6": CSV_NON_TYPE,
                "cluster": CSV_NON_TYPE,
                "virtual_chassis": CSV_NON_TYPE,
                "device_redundancy_group": CSV_NON_TYPE,
                "secrets_group": CSV_NON_TYPE,
                "parent_bay": CSV_NON_TYPE,
            }
            serializer_data = serializer.data

            tags = sorted([str(tag["id"]) for tag in serializer_data.pop("tags")])
            instance_tags_pk = sorted([str(tag_pk) for tag_pk in device.tags.values_list("pk", flat=True)])
            self.assertEqual(tags, instance_tags_pk)

            serializer_data.pop("notes_url")
            serializer_data.pop("custom_fields")
            serializer_data.pop("created")
            serializer_data.pop("last_updated")

            self.assertEqual(expected_data, serializer_data)

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

        import_data = response_data.replace("TestDevice1", "TestDevice3").replace("TestDevice2", "TestDevice4")
        data = {
            "csv_data": import_data,
        }
        url = reverse("dcim:device_import")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Device.objects.count(), 4)
