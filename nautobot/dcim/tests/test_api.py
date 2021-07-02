from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from nautobot.dcim.choices import *
from nautobot.dcim.constants import *
from nautobot.dcim.models import (
    Cable,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceRole,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    Manufacturer,
    InventoryItem,
    Platform,
    PowerFeed,
    PowerPort,
    PowerPortTemplate,
    PowerOutlet,
    PowerOutletTemplate,
    PowerPanel,
    Rack,
    RackGroup,
    RackReservation,
    RackRole,
    RearPort,
    RearPortTemplate,
    Region,
    Site,
    VirtualChassis,
)
from nautobot.extras.models import ConfigContextSchema, Status
from nautobot.ipam.models import VLAN
from nautobot.utilities.testing import APITestCase, APIViewTestCases
from nautobot.virtualization.models import Cluster, ClusterType


# Use the proper swappable User model
User = get_user_model()


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("dcim-api:api-root")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class Mixins:
    class ComponentTraceMixin(APITestCase):
        peer_termination_type = None

        def test_trace(self):
            """
            Test tracing a device component's attached cable.
            """
            obj = self.model.objects.first()
            peer_device = Device.objects.create(
                site=Site.objects.first(),
                device_type=DeviceType.objects.first(),
                device_role=DeviceRole.objects.first(),
                name="Peer Device",
            )
            if self.peer_termination_type is None:
                raise NotImplementedError("Test case must set peer_termination_type")
            peer_obj = self.peer_termination_type.objects.create(device=peer_device, name="Peer Termination")
            cable = Cable(termination_a=obj, termination_b=peer_obj, label="Cable 1")
            cable.save()

            self.add_permissions(f"dcim.view_{self.model._meta.model_name}")
            url = reverse(f"dcim-api:{self.model._meta.model_name}-trace", kwargs={"pk": obj.pk})
            response = self.client.get(url, **self.header)

            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 1)
            segment1 = response.data[0]
            self.assertEqual(segment1[0]["name"], obj.name)
            self.assertEqual(segment1[1]["label"], cable.label)
            self.assertEqual(segment1[2]["name"], peer_obj.name)


class RegionTest(APIViewTestCases.APIViewTestCase):
    model = Region
    brief_fields = ["_depth", "display", "id", "name", "site_count", "slug", "url"]
    create_data = [
        {
            "name": "Region 4",
            "slug": "region-4",
        },
        {
            "name": "Region 5",
            "slug": "region-5",
        },
        {
            "name": "Region 6",
            "slug": "region-6",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        Region.objects.create(name="Region 1", slug="region-1")
        Region.objects.create(name="Region 2", slug="region-2")
        Region.objects.create(name="Region 3", slug="region-3")


class SiteTest(APIViewTestCases.APIViewTestCase):
    model = Site
    brief_fields = ["display", "id", "name", "slug", "url"]
    bulk_update_data = {
        "status": "planned",
    }
    choices_fields = ["status"]

    @classmethod
    def setUpTestData(cls):

        regions = (
            Region.objects.create(name="Test Region 1", slug="test-region-1"),
            Region.objects.create(name="Test Region 2", slug="test-region-2"),
        )

        Site.objects.create(region=regions[0], name="Site 1", slug="site-1")
        Site.objects.create(region=regions[0], name="Site 2", slug="site-2")
        Site.objects.create(region=regions[0], name="Site 3", slug="site-3")

        # FIXME(jathan): The writable serializer for `Device.status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "name": "Site 4",
                "slug": "site-4",
                "region": regions[1].pk,
                "status": "active",
            },
            {
                "name": "Site 5",
                "slug": "site-5",
                "region": regions[1].pk,
                "status": "active",
            },
            {
                "name": "Site 6",
                "slug": "site-6",
                "region": regions[1].pk,
                "status": "active",
            },
        ]

    def test_time_zone_field_post_null(self):
        """
        Test allow_null to time_zone field on site.

        See: https://github.com/nautobot/nautobot/issues/342
        """
        self.add_permissions("dcim.add_site")
        url = reverse("dcim-api:site-list")
        site = {"name": "foo", "slug": "foo", "status": "active", "time_zone": None}

        # Attempt to create new site with null time_zone attr.
        response = self.client.post(url, **self.header, data=site, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["time_zone"], None)

    def test_time_zone_field_post_blank(self):
        """
        Test disallowed blank time_zone field on site.

        See: https://github.com/nautobot/nautobot/issues/342
        """
        self.add_permissions("dcim.add_site")
        url = reverse("dcim-api:site-list")
        site = {"name": "foo", "slug": "foo", "status": "active", "time_zone": ""}

        # Attempt to create new site with blank time_zone attr.
        response = self.client.post(url, **self.header, data=site, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["time_zone"], ["A valid timezone is required."])

    def test_time_zone_field_post_valid(self):
        """
        Test valid time_zone field on site.

        See: https://github.com/nautobot/nautobot/issues/342
        """
        self.add_permissions("dcim.add_site")
        url = reverse("dcim-api:site-list")
        time_zone = "UTC"
        site = {"name": "foo", "slug": "foo", "status": "active", "time_zone": time_zone}

        # Attempt to create new site with valid time_zone attr.
        response = self.client.post(url, **self.header, data=site, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["time_zone"], time_zone)

    def test_time_zone_field_post_invalid(self):
        """
        Test invalid time_zone field on site.

        See: https://github.com/nautobot/nautobot/issues/342
        """
        self.add_permissions("dcim.add_site")
        url = reverse("dcim-api:site-list")
        time_zone = "IDONOTEXIST"
        site = {"name": "foo", "slug": "foo", "status": "active", "time_zone": time_zone}

        # Attempt to create new site with invalid time_zone attr.
        response = self.client.post(url, **self.header, data=site, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["time_zone"],
            ["A valid timezone is required."],
        )

    def test_time_zone_field_get_blank(self):
        """
        Test that a site's time_zone field defaults to null.

        See: https://github.com/nautobot/nautobot/issues/342
        """

        self.add_permissions("dcim.view_site")
        site = Site.objects.get(slug="site-1")
        url = reverse("dcim-api:site-detail", kwargs={"pk": site.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["time_zone"], None)


class RackGroupTest(APIViewTestCases.APIViewTestCase):
    model = RackGroup
    brief_fields = ["_depth", "display", "id", "name", "rack_count", "slug", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        )

        parent_rack_groups = (
            RackGroup.objects.create(site=sites[0], name="Parent Rack Group 1", slug="parent-rack-group-1"),
            RackGroup.objects.create(site=sites[1], name="Parent Rack Group 2", slug="parent-rack-group-2"),
        )

        RackGroup.objects.create(
            site=sites[0],
            name="Rack Group 1",
            slug="rack-group-1",
            parent=parent_rack_groups[0],
        )
        RackGroup.objects.create(
            site=sites[0],
            name="Rack Group 2",
            slug="rack-group-2",
            parent=parent_rack_groups[0],
        )
        RackGroup.objects.create(
            site=sites[0],
            name="Rack Group 3",
            slug="rack-group-3",
            parent=parent_rack_groups[0],
        )

        cls.create_data = [
            {
                "name": "Test Rack Group 4",
                "slug": "test-rack-group-4",
                "site": sites[1].pk,
                "parent": parent_rack_groups[1].pk,
            },
            {
                "name": "Test Rack Group 5",
                "slug": "test-rack-group-5",
                "site": sites[1].pk,
                "parent": parent_rack_groups[1].pk,
            },
            {
                "name": "Test Rack Group 6",
                "slug": "test-rack-group-6",
                "site": sites[1].pk,
                "parent": parent_rack_groups[1].pk,
            },
        ]


class RackRoleTest(APIViewTestCases.APIViewTestCase):
    model = RackRole
    brief_fields = ["display", "id", "name", "rack_count", "slug", "url"]
    create_data = [
        {
            "name": "Rack Role 4",
            "slug": "rack-role-4",
            "color": "ffff00",
        },
        {
            "name": "Rack Role 5",
            "slug": "rack-role-5",
            "color": "ffff00",
        },
        {
            "name": "Rack Role 6",
            "slug": "rack-role-6",
            "color": "ffff00",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        RackRole.objects.create(name="Rack Role 1", slug="rack-role-1", color="ff0000")
        RackRole.objects.create(name="Rack Role 2", slug="rack-role-2", color="00ff00")
        RackRole.objects.create(name="Rack Role 3", slug="rack-role-3", color="0000ff")


class RackTest(APIViewTestCases.APIViewTestCase):
    model = Rack
    brief_fields = ["device_count", "display", "id", "name", "url"]
    bulk_update_data = {
        "status": "planned",
    }
    choices_fields = ["outer_unit", "status", "type", "width"]

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        )

        rack_groups = (
            RackGroup.objects.create(site=sites[0], name="Rack Group 1", slug="rack-group-1"),
            RackGroup.objects.create(site=sites[1], name="Rack Group 2", slug="rack-group-2"),
        )

        rack_roles = (
            RackRole.objects.create(name="Rack Role 1", slug="rack-role-1", color="ff0000"),
            RackRole.objects.create(name="Rack Role 2", slug="rack-role-2", color="00ff00"),
        )

        statuses = Status.objects.get_for_model(Rack)

        Rack.objects.create(
            site=sites[0],
            group=rack_groups[0],
            role=rack_roles[0],
            name="Rack 1",
            status=statuses[0],
        )
        Rack.objects.create(
            site=sites[0],
            group=rack_groups[0],
            role=rack_roles[0],
            name="Rack 2",
            status=statuses[0],
        )
        Rack.objects.create(
            site=sites[0],
            group=rack_groups[0],
            role=rack_roles[0],
            name="Rack 3",
            status=statuses[0],
        )

        # FIXME(jathan): The writable serializer for `Device.status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "name": "Test Rack 4",
                "site": sites[1].pk,
                "group": rack_groups[1].pk,
                "role": rack_roles[1].pk,
                "status": "available",
            },
            {
                "name": "Test Rack 5",
                "site": sites[1].pk,
                "group": rack_groups[1].pk,
                "role": rack_roles[1].pk,
                "status": "available",
            },
            {
                "name": "Test Rack 6",
                "site": sites[1].pk,
                "group": rack_groups[1].pk,
                "role": rack_roles[1].pk,
                "status": "available",
            },
        ]

    def test_get_rack_elevation(self):
        """
        GET a single rack elevation.
        """
        rack = Rack.objects.first()
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-elevation", kwargs={"pk": rack.pk})

        # Retrieve all units
        response = self.client.get(url, **self.header)
        self.assertEqual(response.data["count"], 42)

        # Search for specific units
        response = self.client.get(f"{url}?q=3", **self.header)
        self.assertEqual(response.data["count"], 13)
        response = self.client.get(f"{url}?q=U3", **self.header)
        self.assertEqual(response.data["count"], 11)
        response = self.client.get(f"{url}?q=U10", **self.header)
        self.assertEqual(response.data["count"], 1)

    def test_filter_rack_elevation(self):
        """
        Test filtering the list of rack elevations.

        See: https://github.com/nautobot/nautobot/issues/81
        """
        rack = Rack.objects.first()
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-elevation", kwargs={"pk": rack.pk})
        params = {"brief": "true", "face": "front", "exclude": "a85a31aa-094f-4de9-8ba6-16cb088a1b74"}
        response = self.client.get(url, params, **self.header)
        self.assertHttpStatus(response, 200)

    def test_get_rack_elevation_svg(self):
        """
        GET a single rack elevation in SVG format.
        """
        rack = Rack.objects.first()
        self.add_permissions("dcim.view_rack")
        url = "{}?render=svg".format(reverse("dcim-api:rack-elevation", kwargs={"pk": rack.pk}))

        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.get("Content-Type"), "image/svg+xml")


class RackReservationTest(APIViewTestCases.APIViewTestCase):
    model = RackReservation
    brief_fields = ["display", "id", "units", "url", "user"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="user1", is_active=True)
        site = Site.objects.create(name="Test Site 1", slug="test-site-1")

        cls.racks = (
            Rack.objects.create(site=site, name="Rack 1"),
            Rack.objects.create(site=site, name="Rack 2"),
        )

        RackReservation.objects.create(rack=cls.racks[0], units=[1, 2, 3], user=user, description="Reservation #1")
        RackReservation.objects.create(rack=cls.racks[0], units=[4, 5, 6], user=user, description="Reservation #2")
        RackReservation.objects.create(rack=cls.racks[0], units=[7, 8, 9], user=user, description="Reservation #3")

    def setUp(self):
        super().setUp()

        # We have to set creation data under setUp() because we need access to the test user.
        self.create_data = [
            {
                "rack": self.racks[1].pk,
                "units": [10, 11, 12],
                "user": self.user.pk,
                "description": "Reservation #4",
            },
            {
                "rack": self.racks[1].pk,
                "units": [13, 14, 15],
                "user": self.user.pk,
                "description": "Reservation #5",
            },
            {
                "rack": self.racks[1].pk,
                "units": [16, 17, 18],
                "user": self.user.pk,
                "description": "Reservation #6",
            },
        ]


class ManufacturerTest(APIViewTestCases.APIViewTestCase):
    model = Manufacturer
    brief_fields = ["devicetype_count", "display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "Manufacturer 4",
            "slug": "manufacturer-4",
        },
        {
            "name": "Manufacturer 5",
            "slug": "manufacturer-5",
        },
        {
            "name": "Manufacturer 6",
            "slug": "manufacturer-6",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        Manufacturer.objects.create(name="Manufacturer 2", slug="manufacturer-2")
        Manufacturer.objects.create(name="Manufacturer 3", slug="manufacturer-3")


class DeviceTypeTest(APIViewTestCases.APIViewTestCase):
    model = DeviceType
    brief_fields = [
        "device_count",
        "display",
        "id",
        "manufacturer",
        "model",
        "slug",
        "url",
    ]
    bulk_update_data = {
        "part_number": "ABC123",
    }
    choices_fields = ["subdevice_role"]

    @classmethod
    def setUpTestData(cls):

        manufacturers = (
            Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1"),
            Manufacturer.objects.create(name="Manufacturer 2", slug="manufacturer-2"),
        )

        DeviceType.objects.create(manufacturer=manufacturers[0], model="Device Type 1", slug="device-type-1")
        DeviceType.objects.create(manufacturer=manufacturers[0], model="Device Type 2", slug="device-type-2")
        DeviceType.objects.create(manufacturer=manufacturers[0], model="Device Type 3", slug="device-type-3")

        cls.create_data = [
            {
                "manufacturer": manufacturers[1].pk,
                "model": "Device Type 4",
                "slug": "device-type-4",
            },
            {
                "manufacturer": manufacturers[1].pk,
                "model": "Device Type 5",
                "slug": "device-type-5",
            },
            {
                "manufacturer": manufacturers[1].pk,
                "model": "Device Type 6",
                "slug": "device-type-6",
            },
        ]


class ConsolePortTemplateTest(APIViewTestCases.APIViewTestCase):
    model = ConsolePortTemplate
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")

        ConsolePortTemplate.objects.create(device_type=devicetype, name="Console Port Template 1")
        ConsolePortTemplate.objects.create(device_type=devicetype, name="Console Port Template 2")
        ConsolePortTemplate.objects.create(device_type=devicetype, name="Console Port Template 3")

        cls.create_data = [
            {
                "device_type": devicetype.pk,
                "name": "Console Port Template 4",
            },
            {
                "device_type": devicetype.pk,
                "name": "Console Port Template 5",
            },
            {
                "device_type": devicetype.pk,
                "name": "Console Port Template 6",
            },
        ]


class ConsoleServerPortTemplateTest(APIViewTestCases.APIViewTestCase):
    model = ConsoleServerPortTemplate
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")

        ConsoleServerPortTemplate.objects.create(device_type=devicetype, name="Console Server Port Template 1")
        ConsoleServerPortTemplate.objects.create(device_type=devicetype, name="Console Server Port Template 2")
        ConsoleServerPortTemplate.objects.create(device_type=devicetype, name="Console Server Port Template 3")

        cls.create_data = [
            {
                "device_type": devicetype.pk,
                "name": "Console Server Port Template 4",
            },
            {
                "device_type": devicetype.pk,
                "name": "Console Server Port Template 5",
            },
            {
                "device_type": devicetype.pk,
                "name": "Console Server Port Template 6",
            },
        ]


class PowerPortTemplateTest(APIViewTestCases.APIViewTestCase):
    model = PowerPortTemplate
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")

        PowerPortTemplate.objects.create(device_type=devicetype, name="Power Port Template 1")
        PowerPortTemplate.objects.create(device_type=devicetype, name="Power Port Template 2")
        PowerPortTemplate.objects.create(device_type=devicetype, name="Power Port Template 3")

        cls.create_data = [
            {
                "device_type": devicetype.pk,
                "name": "Power Port Template 4",
            },
            {
                "device_type": devicetype.pk,
                "name": "Power Port Template 5",
            },
            {
                "device_type": devicetype.pk,
                "name": "Power Port Template 6",
            },
        ]


class PowerOutletTemplateTest(APIViewTestCases.APIViewTestCase):
    model = PowerOutletTemplate
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["feed_leg", "type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")

        PowerOutletTemplate.objects.create(device_type=devicetype, name="Power Outlet Template 1")
        PowerOutletTemplate.objects.create(device_type=devicetype, name="Power Outlet Template 2")
        PowerOutletTemplate.objects.create(device_type=devicetype, name="Power Outlet Template 3")

        cls.create_data = [
            {
                "device_type": devicetype.pk,
                "name": "Power Outlet Template 4",
            },
            {
                "device_type": devicetype.pk,
                "name": "Power Outlet Template 5",
            },
            {
                "device_type": devicetype.pk,
                "name": "Power Outlet Template 6",
            },
        ]


class InterfaceTemplateTest(APIViewTestCases.APIViewTestCase):
    model = InterfaceTemplate
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")

        InterfaceTemplate.objects.create(device_type=devicetype, name="Interface Template 1", type="1000base-t")
        InterfaceTemplate.objects.create(device_type=devicetype, name="Interface Template 2", type="1000base-t")
        InterfaceTemplate.objects.create(device_type=devicetype, name="Interface Template 3", type="1000base-t")

        cls.create_data = [
            {
                "device_type": devicetype.pk,
                "name": "Interface Template 4",
                "type": "1000base-t",
            },
            {
                "device_type": devicetype.pk,
                "name": "Interface Template 5",
                "type": "1000base-t",
            },
            {
                "device_type": devicetype.pk,
                "name": "Interface Template 6",
                "type": "1000base-t",
            },
        ]


class FrontPortTemplateTest(APIViewTestCases.APIViewTestCase):
    model = FrontPortTemplate
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")

        rear_port_templates = (
            RearPortTemplate.objects.create(
                device_type=devicetype,
                name="Rear Port Template 1",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                name="Rear Port Template 2",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                name="Rear Port Template 3",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                name="Rear Port Template 4",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                name="Rear Port Template 5",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                name="Rear Port Template 6",
                type=PortTypeChoices.TYPE_8P8C,
            ),
        )

        FrontPortTemplate.objects.create(
            device_type=devicetype,
            name="Front Port Template 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_port_templates[0],
        ),
        FrontPortTemplate.objects.create(
            device_type=devicetype,
            name="Front Port Template 2",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_port_templates[1],
        ),
        FrontPortTemplate.objects.create(
            device_type=devicetype,
            name="Front Port Template 3",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_port_templates[2],
        ),

        cls.create_data = [
            {
                "device_type": devicetype.pk,
                "name": "Front Port Template 4",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_port_templates[3].pk,
                "rear_port_position": 1,
            },
            {
                "device_type": devicetype.pk,
                "name": "Front Port Template 5",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_port_templates[4].pk,
                "rear_port_position": 1,
            },
            {
                "device_type": devicetype.pk,
                "name": "Front Port Template 6",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_port_templates[5].pk,
                "rear_port_position": 1,
            },
        ]


class RearPortTemplateTest(APIViewTestCases.APIViewTestCase):
    model = RearPortTemplate
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")

        RearPortTemplate.objects.create(
            device_type=devicetype,
            name="Rear Port Template 1",
            type=PortTypeChoices.TYPE_8P8C,
        )
        RearPortTemplate.objects.create(
            device_type=devicetype,
            name="Rear Port Template 2",
            type=PortTypeChoices.TYPE_8P8C,
        )
        RearPortTemplate.objects.create(
            device_type=devicetype,
            name="Rear Port Template 3",
            type=PortTypeChoices.TYPE_8P8C,
        )

        cls.create_data = [
            {
                "device_type": devicetype.pk,
                "name": "Rear Port Template 4",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "device_type": devicetype.pk,
                "name": "Rear Port Template 5",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "device_type": devicetype.pk,
                "name": "Rear Port Template 6",
                "type": PortTypeChoices.TYPE_8P8C,
            },
        ]


class DeviceBayTemplateTest(APIViewTestCases.APIViewTestCase):
    model = DeviceBayTemplate
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Device Type 1",
            slug="device-type-1",
            subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
        )

        DeviceBayTemplate.objects.create(device_type=devicetype, name="Device Bay Template 1")
        DeviceBayTemplate.objects.create(device_type=devicetype, name="Device Bay Template 2")
        DeviceBayTemplate.objects.create(device_type=devicetype, name="Device Bay Template 3")

        cls.create_data = [
            {
                "device_type": devicetype.pk,
                "name": "Device Bay Template 4",
            },
            {
                "device_type": devicetype.pk,
                "name": "Device Bay Template 5",
            },
            {
                "device_type": devicetype.pk,
                "name": "Device Bay Template 6",
            },
        ]


class DeviceRoleTest(APIViewTestCases.APIViewTestCase):
    model = DeviceRole
    brief_fields = ["device_count", "display", "id", "name", "slug", "url", "virtualmachine_count"]
    create_data = [
        {
            "name": "Device Role 4",
            "slug": "device-role-4",
            "color": "ffff00",
        },
        {
            "name": "Device Role 5",
            "slug": "device-role-5",
            "color": "ffff00",
        },
        {
            "name": "Device Role 6",
            "slug": "device-role-6",
            "color": "ffff00",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ff0000")
        DeviceRole.objects.create(name="Device Role 2", slug="device-role-2", color="00ff00")
        DeviceRole.objects.create(name="Device Role 3", slug="device-role-3", color="0000ff")


class PlatformTest(APIViewTestCases.APIViewTestCase):
    model = Platform
    brief_fields = ["device_count", "display", "id", "name", "slug", "url", "virtualmachine_count"]
    create_data = [
        {
            "name": "Platform 4",
            "slug": "platform-4",
        },
        {
            "name": "Platform 5",
            "slug": "platform-5",
        },
        {
            "name": "Platform 6",
            "slug": "platform-6",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        Platform.objects.create(name="Platform 1", slug="platform-1")
        Platform.objects.create(name="Platform 2", slug="platform-2")
        Platform.objects.create(name="Platform 3", slug="platform-3")


class DeviceTest(APIViewTestCases.APIViewTestCase):
    model = Device
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "status": "failed",
    }
    choices_fields = ["face", "status"]

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        )

        racks = (
            Rack.objects.create(name="Rack 1", site=sites[0]),
            Rack.objects.create(name="Rack 2", site=sites[1]),
        )

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")

        device_types = (
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1"),
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 2", slug="device-type-2"),
        )

        device_roles = (
            DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ff0000"),
            DeviceRole.objects.create(name="Device Role 2", slug="device-role-2", color="00ff00"),
        )

        device_statuses = Status.objects.get_for_model(Device)

        cluster_type = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")

        clusters = (
            Cluster.objects.create(name="Cluster 1", type=cluster_type),
            Cluster.objects.create(name="Cluster 2", type=cluster_type),
        )

        Device.objects.create(
            device_type=device_types[0],
            device_role=device_roles[0],
            status=device_statuses[0],
            name="Device 1",
            site=sites[0],
            rack=racks[0],
            cluster=clusters[0],
            local_context_data={"A": 1},
        ),
        Device.objects.create(
            device_type=device_types[0],
            device_role=device_roles[0],
            status=device_statuses[0],
            name="Device 2",
            site=sites[0],
            rack=racks[0],
            cluster=clusters[0],
            local_context_data={"B": 2},
        ),
        Device.objects.create(
            device_type=device_types[0],
            device_role=device_roles[0],
            status=device_statuses[0],
            name="Device 3",
            site=sites[0],
            rack=racks[0],
            cluster=clusters[0],
            local_context_data={"C": 3},
        ),

        # FIXME(jathan): The writable serializer for `Device.status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "device_type": device_types[1].pk,
                "device_role": device_roles[1].pk,
                "status": "offline",
                "name": "Test Device 4",
                "site": sites[1].pk,
                "rack": racks[1].pk,
                "cluster": clusters[1].pk,
            },
            {
                "device_type": device_types[1].pk,
                "device_role": device_roles[1].pk,
                "status": "offline",
                "name": "Test Device 5",
                "site": sites[1].pk,
                "rack": racks[1].pk,
                "cluster": clusters[1].pk,
            },
            {
                "device_type": device_types[1].pk,
                "device_role": device_roles[1].pk,
                "status": "offline",
                "name": "Test Device 6",
                "site": sites[1].pk,
                "rack": racks[1].pk,
                "cluster": clusters[1].pk,
            },
        ]

    def test_config_context_included_by_default_in_list_view(self):
        """
        Check that config context data is included by default in the devices list.
        """
        self.add_permissions("dcim.view_device")
        url = reverse("dcim-api:device-list") + "?slug=device-with-context-data"
        response = self.client.get(url, **self.header)

        self.assertEqual(response.data["results"][0].get("config_context", {}).get("A"), 1)

    def test_config_context_excluded(self):
        """
        Check that config context data can be excluded by passing ?exclude=config_context.
        """
        self.add_permissions("dcim.view_device")
        url = reverse("dcim-api:device-list") + "?exclude=config_context"
        response = self.client.get(url, **self.header)

        self.assertFalse("config_context" in response.data["results"][0])

    def test_unique_name_per_site_constraint(self):
        """
        Check that creating a device with a duplicate name within a site fails.
        """
        device = Device.objects.first()
        data = {
            "device_type": device.device_type.pk,
            "device_role": device.device_role.pk,
            "site": device.site.pk,
            "name": device.name,
        }

        self.add_permissions("dcim.add_device")
        url = reverse("dcim-api:device-list")
        response = self.client.post(url, data, format="json", **self.header)

        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_local_context_schema_validation_pass(self):
        """
        Given a config context schema
        And a device with local context that conforms to that schema
        Assert that the local context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"A": {"type": "integer"}}}
        )
        self.add_permissions("dcim.change_device")

        patch_data = {"local_context_schema": str(schema.pk)}

        response = self.client.patch(
            self._get_detail_url(Device.objects.get(name="Device 1")), patch_data, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["local_context_schema"]["id"], str(schema.pk))

    def test_local_context_schema_schema_validation_fails(self):
        """
        Given a config context schema
        And a device with local context that *does not* conform to that schema
        Assert that the local context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 2", slug="schema-2", data_schema={"type": "object", "properties": {"B": {"type": "string"}}}
        )
        # Add object-level permission
        self.add_permissions("dcim.change_device")

        patch_data = {"local_context_schema": str(schema.pk)}

        response = self.client.patch(
            self._get_detail_url(Device.objects.get(name="Device 2")), patch_data, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)


class ConsolePortTest(Mixins.ComponentTraceMixin, APIViewTestCases.APIViewTestCase):
    model = ConsolePort
    brief_fields = ["cable", "device", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    peer_termination_type = ConsoleServerPort
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device = Device.objects.create(device_type=devicetype, device_role=devicerole, name="Device 1", site=site)

        ConsolePort.objects.create(device=device, name="Console Port 1")
        ConsolePort.objects.create(device=device, name="Console Port 2")
        ConsolePort.objects.create(device=device, name="Console Port 3")

        cls.create_data = [
            {
                "device": device.pk,
                "name": "Console Port 4",
            },
            {
                "device": device.pk,
                "name": "Console Port 5",
            },
            {
                "device": device.pk,
                "name": "Console Port 6",
            },
        ]


class ConsoleServerPortTest(Mixins.ComponentTraceMixin, APIViewTestCases.APIViewTestCase):
    model = ConsoleServerPort
    brief_fields = ["cable", "device", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    peer_termination_type = ConsolePort
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device = Device.objects.create(device_type=devicetype, device_role=devicerole, name="Device 1", site=site)

        ConsoleServerPort.objects.create(device=device, name="Console Server Port 1")
        ConsoleServerPort.objects.create(device=device, name="Console Server Port 2")
        ConsoleServerPort.objects.create(device=device, name="Console Server Port 3")

        cls.create_data = [
            {
                "device": device.pk,
                "name": "Console Server Port 4",
            },
            {
                "device": device.pk,
                "name": "Console Server Port 5",
            },
            {
                "device": device.pk,
                "name": "Console Server Port 6",
            },
        ]


class PowerPortTest(Mixins.ComponentTraceMixin, APIViewTestCases.APIViewTestCase):
    model = PowerPort
    brief_fields = ["cable", "device", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    peer_termination_type = PowerOutlet
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device = Device.objects.create(device_type=devicetype, device_role=devicerole, name="Device 1", site=site)

        PowerPort.objects.create(device=device, name="Power Port 1")
        PowerPort.objects.create(device=device, name="Power Port 2")
        PowerPort.objects.create(device=device, name="Power Port 3")

        cls.create_data = [
            {
                "device": device.pk,
                "name": "Power Port 4",
            },
            {
                "device": device.pk,
                "name": "Power Port 5",
            },
            {
                "device": device.pk,
                "name": "Power Port 6",
            },
        ]


class PowerOutletTest(Mixins.ComponentTraceMixin, APIViewTestCases.APIViewTestCase):
    model = PowerOutlet
    brief_fields = ["cable", "device", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    peer_termination_type = PowerPort
    choices_fields = ["feed_leg", "type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device = Device.objects.create(device_type=devicetype, device_role=devicerole, name="Device 1", site=site)

        PowerOutlet.objects.create(device=device, name="Power Outlet 1")
        PowerOutlet.objects.create(device=device, name="Power Outlet 2")
        PowerOutlet.objects.create(device=device, name="Power Outlet 3")

        cls.create_data = [
            {
                "device": device.pk,
                "name": "Power Outlet 4",
            },
            {
                "device": device.pk,
                "name": "Power Outlet 5",
            },
            {
                "device": device.pk,
                "name": "Power Outlet 6",
            },
        ]


class InterfaceTest(Mixins.ComponentTraceMixin, APIViewTestCases.APIViewTestCase):
    model = Interface
    brief_fields = ["cable", "device", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    peer_termination_type = Interface
    choices_fields = ["mode", "type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device = Device.objects.create(device_type=devicetype, device_role=devicerole, name="Device 1", site=site)

        Interface.objects.create(device=device, name="Interface 1", type="1000base-t")
        Interface.objects.create(device=device, name="Interface 2", type="1000base-t")
        Interface.objects.create(device=device, name="Interface 3", type="1000base-t")

        vlans = (
            VLAN.objects.create(name="VLAN 1", vid=1),
            VLAN.objects.create(name="VLAN 2", vid=2),
            VLAN.objects.create(name="VLAN 3", vid=3),
        )

        cls.create_data = [
            {
                "device": device.pk,
                "name": "Interface 4",
                "type": "1000base-t",
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "tagged_vlans": [vlans[0].pk, vlans[1].pk],
                "untagged_vlan": vlans[2].pk,
            },
            {
                "device": device.pk,
                "name": "Interface 5",
                "type": "1000base-t",
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "tagged_vlans": [vlans[0].pk, vlans[1].pk],
                "untagged_vlan": vlans[2].pk,
            },
            {
                "device": device.pk,
                "name": "Interface 6",
                "type": "1000base-t",
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "tagged_vlans": [vlans[0].pk, vlans[1].pk],
                "untagged_vlan": vlans[2].pk,
            },
        ]


class FrontPortTest(APIViewTestCases.APIViewTestCase):
    model = FrontPort
    brief_fields = ["cable", "device", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    peer_termination_type = Interface
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device = Device.objects.create(device_type=devicetype, device_role=devicerole, name="Device 1", site=site)

        rear_ports = (
            RearPort.objects.create(device=device, name="Rear Port 1", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=device, name="Rear Port 2", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=device, name="Rear Port 3", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=device, name="Rear Port 4", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=device, name="Rear Port 5", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=device, name="Rear Port 6", type=PortTypeChoices.TYPE_8P8C),
        )

        FrontPort.objects.create(
            device=device,
            name="Front Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_ports[0],
        )
        FrontPort.objects.create(
            device=device,
            name="Front Port 2",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_ports[1],
        )
        FrontPort.objects.create(
            device=device,
            name="Front Port 3",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_ports[2],
        )

        cls.create_data = [
            {
                "device": device.pk,
                "name": "Front Port 4",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_ports[3].pk,
                "rear_port_position": 1,
            },
            {
                "device": device.pk,
                "name": "Front Port 5",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_ports[4].pk,
                "rear_port_position": 1,
            },
            {
                "device": device.pk,
                "name": "Front Port 6",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_ports[5].pk,
                "rear_port_position": 1,
            },
        ]


class RearPortTest(APIViewTestCases.APIViewTestCase):
    model = RearPort
    brief_fields = ["cable", "device", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    peer_termination_type = Interface
    choices_fields = ["type"]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device = Device.objects.create(device_type=devicetype, device_role=devicerole, name="Device 1", site=site)

        RearPort.objects.create(device=device, name="Rear Port 1", type=PortTypeChoices.TYPE_8P8C)
        RearPort.objects.create(device=device, name="Rear Port 2", type=PortTypeChoices.TYPE_8P8C)
        RearPort.objects.create(device=device, name="Rear Port 3", type=PortTypeChoices.TYPE_8P8C)

        cls.create_data = [
            {
                "device": device.pk,
                "name": "Rear Port 4",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "device": device.pk,
                "name": "Rear Port 5",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "device": device.pk,
                "name": "Rear Port 6",
                "type": PortTypeChoices.TYPE_8P8C,
            },
        ]


class DeviceBayTest(APIViewTestCases.APIViewTestCase):
    model = DeviceBay
    brief_fields = ["device", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")

        device_types = (
            DeviceType.objects.create(
                manufacturer=manufacturer,
                model="Device Type 1",
                slug="device-type-1",
                subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
            ),
            DeviceType.objects.create(
                manufacturer=manufacturer,
                model="Device Type 2",
                slug="device-type-2",
                subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
            ),
        )

        devices = (
            Device.objects.create(
                device_type=device_types[0],
                device_role=devicerole,
                name="Device 1",
                site=site,
            ),
            Device.objects.create(
                device_type=device_types[1],
                device_role=devicerole,
                name="Device 2",
                site=site,
            ),
            Device.objects.create(
                device_type=device_types[1],
                device_role=devicerole,
                name="Device 3",
                site=site,
            ),
            Device.objects.create(
                device_type=device_types[1],
                device_role=devicerole,
                name="Device 4",
                site=site,
            ),
        )

        DeviceBay.objects.create(device=devices[0], name="Device Bay 1")
        DeviceBay.objects.create(device=devices[0], name="Device Bay 2")
        DeviceBay.objects.create(device=devices[0], name="Device Bay 3")

        cls.create_data = [
            {
                "device": devices[0].pk,
                "name": "Device Bay 4",
                "installed_device": devices[1].pk,
            },
            {
                "device": devices[0].pk,
                "name": "Device Bay 5",
                "installed_device": devices[2].pk,
            },
            {
                "device": devices[0].pk,
                "name": "Device Bay 6",
                "installed_device": devices[3].pk,
            },
        ]


class InventoryItemTest(APIViewTestCases.APIViewTestCase):
    model = InventoryItem
    brief_fields = ["_depth", "device", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device = Device.objects.create(device_type=devicetype, device_role=devicerole, name="Device 1", site=site)

        InventoryItem.objects.create(device=device, name="Inventory Item 1", manufacturer=manufacturer)
        InventoryItem.objects.create(device=device, name="Inventory Item 2", manufacturer=manufacturer)
        InventoryItem.objects.create(device=device, name="Inventory Item 3", manufacturer=manufacturer)

        cls.create_data = [
            {
                "device": device.pk,
                "name": "Inventory Item 4",
                "manufacturer": manufacturer.pk,
            },
            {
                "device": device.pk,
                "name": "Inventory Item 5",
                "manufacturer": manufacturer.pk,
            },
            {
                "device": device.pk,
                "name": "Inventory Item 6",
                "manufacturer": manufacturer.pk,
            },
        ]


class CableTest(APIViewTestCases.APIViewTestCase):
    model = Cable
    brief_fields = ["display", "id", "label", "url"]
    bulk_update_data = {
        "length": 100,
        "length_unit": "m",
    }
    choices_fields = ["termination_a_type", "termination_b_type", "type", "status", "length_unit"]

    # TODO: Allow updating cable terminations
    test_update_object = None

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name="Site 1", slug="site-1")
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ff0000")

        devices = (
            Device.objects.create(
                device_type=devicetype,
                device_role=devicerole,
                name="Device 1",
                site=site,
            ),
            Device.objects.create(
                device_type=devicetype,
                device_role=devicerole,
                name="Device 2",
                site=site,
            ),
        )

        interfaces = []
        for device in devices:
            for i in range(0, 10):
                interfaces.append(
                    Interface.objects.create(
                        device=device,
                        type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                        name=f"eth{i}",
                    )
                )

        statuses = Status.objects.get_for_model(Cable)

        Cable.objects.create(
            termination_a=interfaces[0],
            termination_b=interfaces[10],
            label="Cable 1",
            status=statuses[0],
        )
        Cable.objects.create(
            termination_a=interfaces[1],
            termination_b=interfaces[11],
            label="Cable 2",
            status=statuses[0],
        )
        Cable.objects.create(
            termination_a=interfaces[2],
            termination_b=interfaces[12],
            label="Cable 3",
            status=statuses[0],
        )

        # FIXME(jathan): The writable serializer for `status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "termination_a_type": "dcim.interface",
                "termination_a_id": interfaces[4].pk,
                "termination_b_type": "dcim.interface",
                "termination_b_id": interfaces[14].pk,
                "status": "planned",
                "label": "Cable 4",
            },
            {
                "termination_a_type": "dcim.interface",
                "termination_a_id": interfaces[5].pk,
                "termination_b_type": "dcim.interface",
                "termination_b_id": interfaces[15].pk,
                "status": "planned",
                "label": "Cable 5",
            },
            {
                "termination_a_type": "dcim.interface",
                "termination_a_id": interfaces[6].pk,
                "termination_b_type": "dcim.interface",
                "termination_b_id": interfaces[16].pk,
                "status": "planned",
                "label": "Cable 6",
            },
        ]


class ConnectedDeviceTest(APITestCase):
    def setUp(self):

        super().setUp()

        self.site1 = Site.objects.create(name="Test Site 1", slug="test-site-1")
        self.site2 = Site.objects.create(name="Test Site 2", slug="test-site-2")
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        self.devicetype1 = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Test Device Type 1",
            slug="test-device-type-1",
        )
        self.devicetype2 = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Test Device Type 2",
            slug="test-device-type-2",
        )
        self.devicerole1 = DeviceRole.objects.create(
            name="Test Device Role 1", slug="test-device-role-1", color="ff0000"
        )
        self.devicerole2 = DeviceRole.objects.create(
            name="Test Device Role 2", slug="test-device-role-2", color="00ff00"
        )
        self.device1 = Device.objects.create(
            device_type=self.devicetype1,
            device_role=self.devicerole1,
            name="TestDevice1",
            site=self.site1,
        )
        self.device2 = Device.objects.create(
            device_type=self.devicetype1,
            device_role=self.devicerole1,
            name="TestDevice2",
            site=self.site1,
        )
        self.interface1 = Interface.objects.create(device=self.device1, name="eth0")
        self.interface2 = Interface.objects.create(device=self.device2, name="eth0")

        cable = Cable(termination_a=self.interface1, termination_b=self.interface2)
        cable.save()

    def test_get_connected_device(self):

        url = reverse("dcim-api:connected-device-list")
        response = self.client.get(url + "?peer_device=TestDevice2&peer_interface=eth0", **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.device1.name)


class VirtualChassisTest(APIViewTestCases.APIViewTestCase):
    model = VirtualChassis
    brief_fields = ["display", "id", "master", "member_count", "name", "url"]

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name="Test Site", slug="test-site")
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type", slug="device-type")
        devicerole = DeviceRole.objects.create(name="Device Role", slug="device-role", color="ff0000")

        devices = (
            Device.objects.create(
                name="Device 1",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 2",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 3",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 4",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 5",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 6",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 7",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 8",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 9",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 10",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 11",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
            Device.objects.create(
                name="Device 12",
                device_type=devicetype,
                device_role=devicerole,
                site=site,
            ),
        )

        # Create 12 interfaces per device
        interfaces = []
        for i, device in enumerate(devices):
            for j in range(0, 13):
                interfaces.append(
                    # Interface name starts with parent device's position in VC; e.g. 1/1, 1/2, 1/3...
                    Interface.objects.create(
                        device=device,
                        name=f"{i%3+1}/{j}",
                        type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                    )
                )

        # Create three VirtualChassis with three members each
        virtual_chassis = (
            VirtualChassis.objects.create(name="Virtual Chassis 1", master=devices[0], domain="domain-1"),
            VirtualChassis.objects.create(name="Virtual Chassis 2", master=devices[3], domain="domain-2"),
            VirtualChassis.objects.create(name="Virtual Chassis 3", master=devices[6], domain="domain-3"),
        )
        Device.objects.filter(pk=devices[0].pk).update(virtual_chassis=virtual_chassis[0], vc_position=1)
        Device.objects.filter(pk=devices[1].pk).update(virtual_chassis=virtual_chassis[0], vc_position=2)
        Device.objects.filter(pk=devices[2].pk).update(virtual_chassis=virtual_chassis[0], vc_position=3)
        Device.objects.filter(pk=devices[3].pk).update(virtual_chassis=virtual_chassis[1], vc_position=1)
        Device.objects.filter(pk=devices[4].pk).update(virtual_chassis=virtual_chassis[1], vc_position=2)
        Device.objects.filter(pk=devices[5].pk).update(virtual_chassis=virtual_chassis[1], vc_position=3)
        Device.objects.filter(pk=devices[6].pk).update(virtual_chassis=virtual_chassis[2], vc_position=1)
        Device.objects.filter(pk=devices[7].pk).update(virtual_chassis=virtual_chassis[2], vc_position=2)
        Device.objects.filter(pk=devices[8].pk).update(virtual_chassis=virtual_chassis[2], vc_position=3)

        cls.update_data = {
            "name": "Virtual Chassis X",
            "domain": "domain-x",
            "master": devices[1].pk,
        }

        cls.create_data = [
            {
                "name": "Virtual Chassis 4",
                "domain": "domain-4",
            },
            {
                "name": "Virtual Chassis 5",
                "domain": "domain-5",
            },
            {
                "name": "Virtual Chassis 6",
                "domain": "domain-6",
            },
        ]

        cls.bulk_update_data = {
            "domain": "newdomain",
        }


class PowerPanelTest(APIViewTestCases.APIViewTestCase):
    model = PowerPanel
    brief_fields = ["display", "id", "name", "powerfeed_count", "url"]

    @classmethod
    def setUpTestData(cls):
        sites = (
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        )

        rack_groups = (
            RackGroup.objects.create(name="Rack Group 1", slug="rack-group-1", site=sites[0]),
            RackGroup.objects.create(name="Rack Group 2", slug="rack-group-2", site=sites[0]),
            RackGroup.objects.create(name="Rack Group 3", slug="rack-group-3", site=sites[0]),
            RackGroup.objects.create(name="Rack Group 4", slug="rack-group-3", site=sites[1]),
        )

        PowerPanel.objects.create(site=sites[0], rack_group=rack_groups[0], name="Power Panel 1"),
        PowerPanel.objects.create(site=sites[0], rack_group=rack_groups[1], name="Power Panel 2"),
        PowerPanel.objects.create(site=sites[0], rack_group=rack_groups[2], name="Power Panel 3"),

        cls.create_data = [
            {
                "name": "Power Panel 4",
                "site": sites[0].pk,
                "rack_group": rack_groups[0].pk,
            },
            {
                "name": "Power Panel 5",
                "site": sites[0].pk,
                "rack_group": rack_groups[1].pk,
            },
            {
                "name": "Power Panel 6",
                "site": sites[0].pk,
                "rack_group": rack_groups[2].pk,
            },
        ]

        cls.bulk_update_data = {"site": sites[1].pk, "rack_group": rack_groups[3].pk}


class PowerFeedTest(APIViewTestCases.APIViewTestCase):
    model = PowerFeed
    brief_fields = ["cable", "display", "id", "name", "url"]
    bulk_update_data = {
        "status": "planned",
    }
    choices_fields = ["phase", "status", "supply", "type"]

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name="Site 1", slug="site-1")
        rackgroup = RackGroup.objects.create(site=site, name="Rack Group 1", slug="rack-group-1")
        rackrole = RackRole.objects.create(name="Rack Role 1", slug="rack-role-1", color="ff0000")

        racks = (
            Rack.objects.create(site=site, group=rackgroup, role=rackrole, name="Rack 1"),
            Rack.objects.create(site=site, group=rackgroup, role=rackrole, name="Rack 2"),
            Rack.objects.create(site=site, group=rackgroup, role=rackrole, name="Rack 3"),
            Rack.objects.create(site=site, group=rackgroup, role=rackrole, name="Rack 4"),
        )

        power_panels = (
            PowerPanel.objects.create(site=site, rack_group=rackgroup, name="Power Panel 1"),
            PowerPanel.objects.create(site=site, rack_group=rackgroup, name="Power Panel 2"),
        )

        PRIMARY = PowerFeedTypeChoices.TYPE_PRIMARY
        REDUNDANT = PowerFeedTypeChoices.TYPE_REDUNDANT
        PowerFeed.objects.create(
            power_panel=power_panels[0],
            rack=racks[0],
            name="Power Feed 1A",
            type=PRIMARY,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[1],
            rack=racks[0],
            name="Power Feed 1B",
            type=REDUNDANT,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[0],
            rack=racks[1],
            name="Power Feed 2A",
            type=PRIMARY,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[1],
            rack=racks[1],
            name="Power Feed 2B",
            type=REDUNDANT,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[0],
            rack=racks[2],
            name="Power Feed 3A",
            type=PRIMARY,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[1],
            rack=racks[2],
            name="Power Feed 3B",
            type=REDUNDANT,
        )

        # FIXME(jathan): The writable serializer for `status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for `utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "name": "Power Feed 4A",
                "power_panel": power_panels[0].pk,
                "rack": racks[3].pk,
                "status": "active",
                "type": PRIMARY,
            },
            {
                "name": "Power Feed 4B",
                "power_panel": power_panels[1].pk,
                "rack": racks[3].pk,
                "status": "active",
                "type": REDUNDANT,
            },
        ]
