from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from nautobot.core.constants import CSV_NULL_TYPE, CSV_NO_OBJECT, VARBINARY_IP_FIELD_REPR_OF_CSV_NO_OBJECT
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.api.serializers import DeviceSerializer
from nautobot.dcim.models.devices import Device, DeviceType
from nautobot.dcim.models.locations import Location
from nautobot.extras.models.roles import Role
from nautobot.extras.models.statuses import Status
from nautobot.extras.models.tags import Tag
from nautobot.tenancy.models import Tenant
from nautobot.users.factory import UserFactory


class CSVParsingRelatedTestCase(TestCase):
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
                "parent_bay__device__location__parent__name",
                "parent_bay__device__location__parent__parent__name",
                "parent_bay__device__location__parent__parent__parent__name",
                "parent_bay__device__location__parent__parent__parent__parent__name",
                "vc_master_for__name",
                "local_config_context_schema__name",
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
            self.assertEqual(
                location_lookup_value,
                {
                    "location__name": device.location.name,
                    "location__parent__name": device.location.parent.name,
                    "location__parent__parent__name": CSV_NO_OBJECT,
                    "location__parent__parent__parent__name": CSV_NO_OBJECT,
                    "location__parent__parent__parent__parent__name": CSV_NO_OBJECT,
                },
            )

            # For Status
            status_lookup_value = serializer._get_natural_key_lookups_value_for_field("status", lookup_querysets[0])
            self.assertEqual(status_lookup_value, {"status__name": device.status.name})

            # For Rack, since `device.rack` does not exists, all rack natural_key_lookups should be `NoObject`
            rack_lookup_value = serializer._get_natural_key_lookups_value_for_field("rack", lookup_querysets[0])
            self.assertEqual(
                rack_lookup_value,
                {
                    "rack__name": CSV_NO_OBJECT,
                    "rack__rack_group__location__name": CSV_NO_OBJECT,
                    "rack__rack_group__location__parent__name": CSV_NO_OBJECT,
                    "rack__rack_group__location__parent__parent__name": CSV_NO_OBJECT,
                    "rack__rack_group__location__parent__parent__parent__name": CSV_NO_OBJECT,
                    "rack__rack_group__location__parent__parent__parent__parent__name": CSV_NO_OBJECT,
                    "rack__rack_group__name": CSV_NO_OBJECT,
                },
            )

        with self.subTest("To Serializer Representation"):
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
                "location__parent__parent__name": CSV_NO_OBJECT,
                "location__parent__parent__parent__name": CSV_NO_OBJECT,
                "location__parent__parent__parent__parent__name": CSV_NO_OBJECT,
                "rack__name": CSV_NO_OBJECT,
                "rack__rack_group__name": CSV_NO_OBJECT,
                "rack__rack_group__location__name": CSV_NO_OBJECT,
                "rack__rack_group__location__parent__name": CSV_NO_OBJECT,
                "rack__rack_group__location__parent__parent__name": CSV_NO_OBJECT,
                "rack__rack_group__location__parent__parent__parent__name": CSV_NO_OBJECT,
                "rack__rack_group__location__parent__parent__parent__parent__name": CSV_NO_OBJECT,
                "primary_ip4__parent__namespace__name": CSV_NO_OBJECT,
                "primary_ip4__host": CSV_NO_OBJECT,
                "primary_ip6__parent__namespace__name": CSV_NO_OBJECT,
                "primary_ip6__host": CSV_NO_OBJECT,
                "cluster__name": CSV_NO_OBJECT,
                "virtual_chassis__name": CSV_NO_OBJECT,
                "device_redundancy_group__name": CSV_NO_OBJECT,
                "secrets_group__name": CSV_NO_OBJECT,
                "parent_bay__name": CSV_NO_OBJECT,
                "parent_bay__device__name": CSV_NO_OBJECT,
                "parent_bay__device__tenant__name": CSV_NO_OBJECT,
                "parent_bay__device__location__name": CSV_NO_OBJECT,
                "parent_bay__device__location__parent__name": CSV_NO_OBJECT,
                "parent_bay__device__location__parent__parent__name": CSV_NO_OBJECT,
                "parent_bay__device__location__parent__parent__parent__name": CSV_NO_OBJECT,
                "parent_bay__device__location__parent__parent__parent__parent__name": CSV_NO_OBJECT,
            }
            serializer_data = serializer.data

            tags = sorted(serializer_data.pop("tags"))
            instance_tags_pk = sorted(device.tags.values_list("name", flat=True))
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

        # Replace Device Name
        import_data = response_data.replace("TestDevice1", "TestDevice3").replace("TestDevice2", "")
        data = {"csv_data": import_data}
        url = reverse("dcim:device_import")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
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
