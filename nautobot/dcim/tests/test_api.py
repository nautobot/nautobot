import json
from unittest import skip

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from constance.test import override_config

from nautobot.dcim.choices import (
    InterfaceModeChoices,
    InterfaceStatusChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedTypeChoices,
    SubdeviceRoleChoices,
)

from nautobot.dcim.models import (
    Cable,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceRedundancyGroup,
    DeviceRole,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    Location,
    LocationType,
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
from nautobot.extras.models import ConfigContextSchema, SecretsGroup, Status
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.tenancy.models import Tenant
from nautobot.utilities.testing import APITestCase, APIViewTestCases
from nautobot.virtualization.models import Cluster, ClusterType


# Use the proper swappable User model
User = get_user_model()


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("dcim-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


class Mixins:
    class ComponentTraceMixin(APITestCase):
        """Mixin for `ComponentModel` classes that support `trace` tests."""

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

    class BaseComponentTestMixin(APIViewTestCases.APIViewTestCase):
        """Mixin class for all `ComponentModel` model class tests."""

        model = None
        brief_fields = ["device", "display", "id", "name", "url"]
        bulk_update_data = {
            "description": "New description",
        }
        choices_fields = ["type"]

        @classmethod
        def setUpTestData(cls):
            super().setUpTestData()
            cls.device_type = DeviceType.objects.exclude(manufacturer__isnull=True).first()
            cls.manufacturer = cls.device_type.manufacturer
            cls.site = Site.objects.first()
            cls.device_role = DeviceRole.objects.first()
            cls.device = Device.objects.create(
                device_type=cls.device_type, device_role=cls.device_role, name="Device 1", site=cls.site
            )

    class BasePortTestMixin(ComponentTraceMixin, BaseComponentTestMixin):
        """Mixin class for all `FooPort` tests."""

        peer_termination_type = None
        brief_fields = ["cable", "device", "display", "id", "name", "url"]

    class BasePortTemplateTestMixin(BaseComponentTestMixin):
        """Mixin class for all `FooPortTemplate` tests."""

        brief_fields = ["display", "id", "name", "url"]


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
        {"name": "Region 7"},
    ]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"

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
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):

        regions = Region.objects.all()[:2]

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
            {"name": "Site 7", "region": regions[1].pk, "status": "active"},
        ]

    def get_deletable_object_pks(self):
        Sites = [
            Site.objects.create(name="Deletable Site 1"),
            Site.objects.create(name="Deletable Site 2"),
            Site.objects.create(name="Deletable Site 3"),
        ]
        return [site.pk for site in Sites]

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
        site = Site.objects.filter(time_zone="").first()
        url = reverse("dcim-api:site-detail", kwargs={"pk": site.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["time_zone"], None)


class LocationTypeTest(APIViewTestCases.APIViewTestCase):
    model = LocationType
    brief_fields = ["display", "id", "name", "slug", "tree_depth", "url"]
    bulk_update_data = {
        "description": "Some generic description of multiple types. Not very useful.",
        "nestable": True,
    }
    choices_fields = []  # TODO: what would we need to get ["content_types"] added as a choices field?
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):
        lt1 = LocationType.objects.get(name="Building")
        lt2 = LocationType.objects.get(name="Floor")
        lt3 = LocationType.objects.get(name="Room")
        lt4 = LocationType.objects.get(name="Aisle")
        # Deletable Location Types
        LocationType.objects.create(name="Delete Me 1")
        LocationType.objects.create(name="Delete Me 2")
        LocationType.objects.create(name="Delete Me 3")
        for lt in [lt1, lt2, lt3, lt4]:
            lt.content_types.add(ContentType.objects.get_for_model(RackGroup))

        cls.create_data = [
            {
                "name": "Standalone",
                "nestable": True,
            },
            {
                "name": "Elevator Type",
                "parent": lt2.pk,
                "content_types": ["ipam.prefix", "ipam.vlangroup", "ipam.vlan"],
            },
            {
                "name": "Closet",
                "slug": "closet",
                "parent": lt3.pk,
                "content_types": ["dcim.device"],
                "description": "An enclosed space smaller than a room",
            },
        ]


class LocationTest(APIViewTestCases.APIViewTestCase):
    model = Location
    brief_fields = ["display", "id", "name", "slug", "tree_depth", "url"]
    bulk_update_data = {
        "status": "planned",
    }
    choices_fields = ["status"]
    slug_source = ["parent__slug", "name"]

    @classmethod
    def setUpTestData(cls):
        lt1 = LocationType.objects.get(name="Campus")
        lt2 = LocationType.objects.get(name="Building")
        lt3 = LocationType.objects.get(name="Floor")
        lt4 = LocationType.objects.get(name="Room")

        status_active = Status.objects.get(slug="active")
        site = Site.objects.first()
        tenant = Tenant.objects.create(name="Test Tenant")

        loc1 = Location.objects.create(name="RTP", location_type=lt1, status=status_active, site=site)
        loc2 = Location.objects.create(name="RTP4E", location_type=lt2, status=status_active, parent=loc1)
        loc3 = Location.objects.create(name="RTP4E-3", location_type=lt3, status=status_active, parent=loc2)
        loc4 = Location.objects.create(
            name="RTP4E-3-0101", location_type=lt4, status=status_active, parent=loc3, tenant=tenant
        )
        for loc in [loc1, loc2, loc3, loc4]:
            loc.validated_save()

        # FIXME(jathan): The writable serializer for `Device.status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "name": "Downtown Durham",
                "location_type": lt1.pk,
                "site": site.pk,
                "status": "active",
            },
            {
                "name": "RTP12",
                "slug": "rtp-12",
                "location_type": lt2.pk,
                "parent": loc1.pk,
                "status": "active",
            },
            {
                "name": "RTP4E-2",
                "location_type": lt3.pk,
                "parent": loc2.pk,
                "status": "active",
                "description": "Second floor of RTP4E",
                "tenant": tenant.pk,
            },
        ]

        # Changing location_type of an existing instance is not permitted
        cls.update_data = {
            "name": "A revised location",
            "slug": "a-different-slug",
            "status": "planned",
        }


class RackGroupTest(APIViewTestCases.APIViewTestCase):
    model = RackGroup
    brief_fields = ["_depth", "display", "id", "name", "rack_count", "slug", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):
        cls.active = Status.objects.get(slug="active")

        cls.sites = Site.objects.all()[:2]

        cls.parent_rack_groups = (
            RackGroup.objects.create(site=cls.sites[0], name="Parent Rack Group 1", slug="parent-rack-group-1"),
            RackGroup.objects.create(site=cls.sites[1], name="Parent Rack Group 2", slug="parent-rack-group-2"),
        )

        location_type = LocationType.objects.create(name="Location Type 1")
        location_type.content_types.add(ContentType.objects.get_for_model(RackGroup))

        cls.locations = (
            Location.objects.create(
                name="Location 1", location_type=location_type, site=cls.sites[0], status=cls.active
            ),
            Location.objects.create(
                name="Location 2", location_type=location_type, site=cls.sites[1], status=cls.active
            ),
        )

        RackGroup.objects.create(
            site=cls.sites[0],
            name="Rack Group 1",
            slug="rack-group-1",
            parent=cls.parent_rack_groups[0],
        )
        RackGroup.objects.create(
            site=cls.sites[0],
            name="Rack Group 2",
            slug="rack-group-2",
            parent=cls.parent_rack_groups[0],
        )
        RackGroup.objects.create(
            site=cls.sites[0],
            location=cls.locations[0],
            name="Rack Group 3",
            slug="rack-group-3",
            parent=cls.parent_rack_groups[0],
        )

        cls.create_data = [
            {
                "name": "Test Rack Group 4",
                "slug": "test-rack-group-4",
                "site": cls.sites[1].pk,
                "parent": cls.parent_rack_groups[1].pk,
            },
            {
                "name": "Test Rack Group 5",
                "slug": "test-rack-group-5",
                "site": cls.sites[1].pk,
                "parent": cls.parent_rack_groups[1].pk,
            },
            {
                "name": "Test Rack Group 6",
                "slug": "test-rack-group-6",
                "site": cls.sites[1].pk,
                "location": cls.locations[1].pk,
                "parent": cls.parent_rack_groups[1].pk,
            },
            {
                "name": "Test Rack Group 7",
                "site": cls.sites[1].pk,
                "parent": cls.parent_rack_groups[1].pk,
            },
        ]

    def test_site_location_mismatch(self):
        """The specified location (if any) must belong to the specified site."""
        self.add_permissions("dcim.add_rackgroup")
        url = reverse("dcim-api:rackgroup-list")
        location = Location.objects.create(
            name="Peer Location", location_type=LocationType.objects.first(), site=self.sites[0], status=self.active
        )
        data = {
            "name": "Bad Group",
            "parent": self.parent_rack_groups[1].pk,
            "site": self.sites[1].pk,
            "location": location.pk,
        }

        response = self.client.post(url, **self.header, data=data, format="json")
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("location", response.json())
        self.assertEqual(
            response.json()["location"], [f'Location "Peer Location" does not belong to site "{self.sites[1].name}".']
        )

    def test_child_group_location_valid(self):
        """A child group with a location may fall within the parent group's location."""
        self.add_permissions("dcim.add_rackgroup")
        url = reverse("dcim-api:rackgroup-list")

        parent_group = RackGroup.objects.filter(site=self.sites[0], location=self.locations[0]).first()
        child_location_type = LocationType.objects.create(
            name="Child Location Type", parent=self.locations[0].location_type
        )
        child_location_type.content_types.add(ContentType.objects.get_for_model(RackGroup))
        child_location = Location.objects.create(
            name="Child Location", location_type=child_location_type, parent=self.locations[0], status=self.active
        )

        data = {
            "name": "Good Group",
            "parent": parent_group.pk,
            "site": self.sites[0].pk,
            "location": child_location.pk,
        }
        response = self.client.post(url, **self.header, data=data, format="json")
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

    def test_child_group_location_invalid(self):
        """A child group with a location must not fall outside its parent group's location."""
        self.add_permissions("dcim.add_rackgroup")
        url = reverse("dcim-api:rackgroup-list")

        parent_group = RackGroup.objects.filter(site=self.sites[0], location=self.locations[0]).first()
        # Same site, but a sibling of locations[0], not a child of it.
        sibling_location = Location.objects.create(
            name="Location 1B", location_type=self.locations[0].location_type, site=self.sites[0], status=self.active
        )

        data = {
            "name": "Good Group",
            "parent": parent_group.pk,
            "site": self.sites[0].pk,
            "location": sibling_location.pk,
        }
        response = self.client.post(url, **self.header, data=data, format="json")
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["location"],
            ['Location "Location 1B" is not descended from parent rack group "Rack Group 3" location "Location 1".'],
        )


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
        {
            "name": "Rack Role 7",
            "color": "ffff00",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"

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

        sites = Site.objects.all()[:2]

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
        reverse_url = reverse("dcim-api:rack-elevation", kwargs={"pk": rack.pk})
        url = f"{reverse_url}?render=svg"

        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.get("Content-Type"), "image/svg+xml")
        self.assertIn(b'class="slot" height="22" width="230"', response.content)

    @override_settings(RACK_ELEVATION_DEFAULT_UNIT_HEIGHT=27, RACK_ELEVATION_DEFAULT_UNIT_WIDTH=255)
    @override_config(RACK_ELEVATION_DEFAULT_UNIT_HEIGHT=19, RACK_ELEVATION_DEFAULT_UNIT_WIDTH=190)
    def test_get_rack_elevation_svg_settings_overridden(self):
        """
        GET a single rack elevation in SVG format, with Django settings specifying a non-standard unit size.
        """
        rack = Rack.objects.first()
        self.add_permissions("dcim.view_rack")
        reverse_url = reverse("dcim-api:rack-elevation", kwargs={"pk": rack.pk})
        url = f"{reverse_url}?render=svg"

        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.get("Content-Type"), "image/svg+xml")
        self.assertIn(b'class="slot" height="27" width="255"', response.content)

    @override_config(RACK_ELEVATION_DEFAULT_UNIT_HEIGHT=19, RACK_ELEVATION_DEFAULT_UNIT_WIDTH=190)
    def test_get_rack_elevation_svg_config_overridden(self):
        """
        GET a single rack elevation in SVG format, with Constance config specifying a non-standard unit size.
        """
        rack = Rack.objects.first()
        self.add_permissions("dcim.view_rack")
        reverse_url = reverse("dcim-api:rack-elevation", kwargs={"pk": rack.pk})
        url = f"{reverse_url}?render=svg"

        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.get("Content-Type"), "image/svg+xml")
        self.assertIn(b'class="slot" height="19" width="190"', response.content)


class RackReservationTest(APIViewTestCases.APIViewTestCase):
    model = RackReservation
    brief_fields = ["display", "id", "units", "url", "user"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="user1", is_active=True)
        site = Site.objects.first()

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
            "name": "Test Manufacturer 4",
            "slug": "test-manufacturer-4",
        },
        {
            "name": "Test Manufacturer 5",
            "slug": "test-manufacturer-5",
        },
        {
            "name": "Test Manufacturer 6",
            "slug": "test-manufacturer-6",
        },
        {
            "name": "Test Manufacturer 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):

        # FIXME(jathan): This has to be replaced with# `get_deletable_object` and
        # `get_deletable_object_pks` but this is a workaround just so all of these objects are
        # deletable for now.
        DeviceType.objects.all().delete()
        Platform.objects.all().delete()


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
    slug_source = "model"

    @classmethod
    def setUpTestData(cls):
        manufacturer_id = Manufacturer.objects.first().pk

        cls.create_data = [
            {
                "manufacturer": manufacturer_id,
                "model": "Device Type 4",
                "slug": "device-type-4",
            },
            {
                "manufacturer": manufacturer_id,
                "model": "Device Type 5",
                "slug": "device-type-5",
            },
            {
                "manufacturer": manufacturer_id,
                "model": "Device Type 6",
                "slug": "device-type-6",
            },
            {
                "manufacturer": manufacturer_id,
                "model": "Device Type 7",
            },
        ]


class ConsolePortTemplateTest(Mixins.BasePortTemplateTestMixin):
    model = ConsolePortTemplate

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ConsolePortTemplate.objects.create(device_type=cls.device_type, name="Console Port Template 1")
        ConsolePortTemplate.objects.create(device_type=cls.device_type, name="Console Port Template 2")
        ConsolePortTemplate.objects.create(device_type=cls.device_type, name="Console Port Template 3")

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Console Port Template 4",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Console Port Template 5",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Console Port Template 6",
            },
        ]


class ConsoleServerPortTemplateTest(Mixins.BasePortTemplateTestMixin):
    model = ConsoleServerPortTemplate

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ConsoleServerPortTemplate.objects.create(device_type=cls.device_type, name="Console Server Port Template 1")
        ConsoleServerPortTemplate.objects.create(device_type=cls.device_type, name="Console Server Port Template 2")
        ConsoleServerPortTemplate.objects.create(device_type=cls.device_type, name="Console Server Port Template 3")

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Console Server Port Template 4",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Console Server Port Template 5",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Console Server Port Template 6",
            },
        ]


class PowerPortTemplateTest(Mixins.BasePortTemplateTestMixin):
    model = PowerPortTemplate

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        PowerPortTemplate.objects.create(device_type=cls.device_type, name="Power Port Template 1")
        PowerPortTemplate.objects.create(device_type=cls.device_type, name="Power Port Template 2")
        PowerPortTemplate.objects.create(device_type=cls.device_type, name="Power Port Template 3")

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Power Port Template 4",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Power Port Template 5",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Power Port Template 6",
            },
        ]


class PowerOutletTemplateTest(Mixins.BasePortTemplateTestMixin):
    model = PowerOutletTemplate
    choices_fields = ["feed_leg", "type"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        PowerOutletTemplate.objects.create(device_type=cls.device_type, name="Power Outlet Template 1")
        PowerOutletTemplate.objects.create(device_type=cls.device_type, name="Power Outlet Template 2")
        PowerOutletTemplate.objects.create(device_type=cls.device_type, name="Power Outlet Template 3")

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Power Outlet Template 4",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Power Outlet Template 5",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Power Outlet Template 6",
            },
        ]


class InterfaceTemplateTest(Mixins.BasePortTemplateTestMixin):
    model = InterfaceTemplate

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        InterfaceTemplate.objects.create(device_type=cls.device_type, name="Interface Template 1", type="1000base-t")
        InterfaceTemplate.objects.create(device_type=cls.device_type, name="Interface Template 2", type="1000base-t")
        InterfaceTemplate.objects.create(device_type=cls.device_type, name="Interface Template 3", type="1000base-t")

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Interface Template 4",
                "type": "1000base-t",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Interface Template 5",
                "type": "1000base-t",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Interface Template 6",
                "type": "1000base-t",
            },
        ]


class FrontPortTemplateTest(Mixins.BasePortTemplateTestMixin):
    model = FrontPortTemplate

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        rear_port_templates = (
            RearPortTemplate.objects.create(
                device_type=cls.device_type,
                name="Rear Port Template 1",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=cls.device_type,
                name="Rear Port Template 2",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=cls.device_type,
                name="Rear Port Template 3",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=cls.device_type,
                name="Rear Port Template 4",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=cls.device_type,
                name="Rear Port Template 5",
                type=PortTypeChoices.TYPE_8P8C,
            ),
            RearPortTemplate.objects.create(
                device_type=cls.device_type,
                name="Rear Port Template 6",
                type=PortTypeChoices.TYPE_8P8C,
            ),
        )

        FrontPortTemplate.objects.create(
            device_type=cls.device_type,
            name="Front Port Template 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_port_templates[0],
        )
        FrontPortTemplate.objects.create(
            device_type=cls.device_type,
            name="Front Port Template 2",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_port_templates[1],
        )
        FrontPortTemplate.objects.create(
            device_type=cls.device_type,
            name="Front Port Template 3",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_port_templates[2],
        )

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Front Port Template 4",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_port_templates[3].pk,
                "rear_port_position": 1,
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Front Port Template 5",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_port_templates[4].pk,
                "rear_port_position": 1,
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Front Port Template 6",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_port_templates[5].pk,
                "rear_port_position": 1,
            },
        ]


class RearPortTemplateTest(Mixins.BasePortTemplateTestMixin):
    model = RearPortTemplate

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        RearPortTemplate.objects.create(
            device_type=cls.device_type,
            name="Rear Port Template 1",
            type=PortTypeChoices.TYPE_8P8C,
        )
        RearPortTemplate.objects.create(
            device_type=cls.device_type,
            name="Rear Port Template 2",
            type=PortTypeChoices.TYPE_8P8C,
        )
        RearPortTemplate.objects.create(
            device_type=cls.device_type,
            name="Rear Port Template 3",
            type=PortTypeChoices.TYPE_8P8C,
        )

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Rear Port Template 4",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Rear Port Template 5",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Rear Port Template 6",
                "type": PortTypeChoices.TYPE_8P8C,
            },
        ]


class DeviceBayTemplateTest(Mixins.BasePortTemplateTestMixin):
    model = DeviceBayTemplate
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        device_type = DeviceType.objects.filter(subdevice_role=SubdeviceRoleChoices.ROLE_PARENT).first()

        DeviceBayTemplate.objects.create(device_type=device_type, name="Device Bay Template 1")
        DeviceBayTemplate.objects.create(device_type=device_type, name="Device Bay Template 2")
        DeviceBayTemplate.objects.create(device_type=device_type, name="Device Bay Template 3")

        cls.create_data = [
            {
                "device_type": device_type.pk,
                "name": "Device Bay Template 4",
            },
            {
                "device_type": device_type.pk,
                "name": "Device Bay Template 5",
            },
            {
                "device_type": device_type.pk,
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
        {
            "name": "Device Role 7",
            "color": "ffff00",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"


class PlatformTest(APIViewTestCases.APIViewTestCase):
    model = Platform
    brief_fields = ["device_count", "display", "id", "name", "slug", "url", "virtualmachine_count"]
    create_data = [
        {
            "name": "Test Platform 4",
            "slug": "test-platform-4",
        },
        {
            "name": "Test Platform 5",
            "slug": "test-platform-5",
        },
        {
            "name": "Test Platform 6",
            "slug": "test-platform-6",
        },
        {
            "name": "Test Platform 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"


class DeviceTest(APIViewTestCases.APIViewTestCase):
    model = Device
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "status": "failed",
    }
    choices_fields = ["face", "status"]

    @classmethod
    def setUpTestData(cls):

        sites = Site.objects.all()[:2]

        racks = (
            Rack.objects.create(name="Rack 1", site=sites[0]),
            Rack.objects.create(name="Rack 2", site=sites[1]),
        )

        device_statuses = Status.objects.get_for_model(Device)

        cluster_type = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")

        clusters = (
            Cluster.objects.create(name="Cluster 1", type=cluster_type),
            Cluster.objects.create(name="Cluster 2", type=cluster_type),
        )

        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1", slug="secrets-group-1"),
            SecretsGroup.objects.create(name="Secrets Group 2", slug="secrets-group-2"),
        )

        device_type = DeviceType.objects.first()
        device_role = DeviceRole.objects.first()

        Device.objects.create(
            device_type=device_type,
            device_role=device_role,
            status=device_statuses[0],
            name="Device 1",
            site=sites[0],
            rack=racks[0],
            cluster=clusters[0],
            secrets_group=secrets_groups[0],
            local_context_data={"A": 1},
        )
        Device.objects.create(
            device_type=device_type,
            device_role=device_role,
            status=device_statuses[0],
            name="Device 2",
            site=sites[0],
            rack=racks[0],
            cluster=clusters[0],
            secrets_group=secrets_groups[0],
            local_context_data={"B": 2},
        )
        Device.objects.create(
            device_type=device_type,
            device_role=device_role,
            status=device_statuses[0],
            name="Device 3",
            site=sites[0],
            rack=racks[0],
            cluster=clusters[0],
            secrets_group=secrets_groups[0],
            local_context_data={"C": 3},
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
                "device_type": device_type.pk,
                "device_role": device_role.pk,
                "status": "offline",
                "name": "Test Device 4",
                "site": sites[1].pk,
                "rack": racks[1].pk,
                "cluster": clusters[1].pk,
                "secrets_group": secrets_groups[1].pk,
            },
            {
                "device_type": device_type.pk,
                "device_role": device_role.pk,
                "status": "offline",
                "name": "Test Device 5",
                "site": sites[1].pk,
                "rack": racks[1].pk,
                "cluster": clusters[1].pk,
                "secrets_group": secrets_groups[1].pk,
            },
            {
                "device_type": device_type.pk,
                "device_role": device_role.pk,
                "status": "offline",
                "name": "Test Device 6",
                "site": sites[1].pk,
                "rack": racks[1].pk,
                "cluster": clusters[1].pk,
                "secrets_group": secrets_groups[1].pk,
            },
        ]

    def test_config_context_included_by_default_in_list_view(self):
        """
        Check that config context data is included by default in the devices list.
        """
        self.add_permissions("dcim.view_device")
        url = reverse("dcim-api:device-list")
        response = self.client.get(url, **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0].get("config_context", {}).get("A"), 1)

    def test_config_context_excluded(self):
        """
        Check that config context data can be excluded by passing ?exclude=config_context.
        """
        self.add_permissions("dcim.view_device")
        url = reverse("dcim-api:device-list") + "?exclude=config_context"
        response = self.client.get(url, **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
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

    def test_patching_primary_ip4_success(self):
        """
        Validate we can set primary_ip4 on a device using a PATCH.
        """
        # Add object-level permission
        self.add_permissions("dcim.change_device")

        dev = Device.objects.get(name="Device 3")
        dev_intf = Interface.objects.create(name="Ethernet1", device=dev, type="1000base-t")
        dev_ip_addr = IPAddress.objects.create(address="192.0.2.1/24", assigned_object=dev_intf)

        patch_data = {"primary_ip4": dev_ip_addr.pk}

        response = self.client.patch(
            self._get_detail_url(Device.objects.get(name="Device 3")), patch_data, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_patching_device_redundancy_group(self):
        """
        Validate we can set device redundancy group on a device using a PATCH.
        """
        # Add object-level permission
        self.add_permissions("dcim.change_device")

        device_redundancy_group = DeviceRedundancyGroup.objects.first()

        d3 = Device.objects.get(name="Device 3")

        # Validate set both redundancy group membership only
        patch_data = {"device_redundancy_group": device_redundancy_group.pk}

        response = self.client.patch(self._get_detail_url(d3), patch_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        d3.refresh_from_db()

        self.assertEqual(
            d3.device_redundancy_group,
            device_redundancy_group,
        )
        # Validate set both redundancy group membership and priority
        patch_data = {"device_redundancy_group": device_redundancy_group.pk, "device_redundancy_group_priority": 1}

        response = self.client.patch(self._get_detail_url(d3), patch_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        d3.refresh_from_db()

        self.assertEqual(
            d3.device_redundancy_group_priority,
            1,
        )

        # Validate error on priority patch only
        patch_data = {"device_redundancy_group_priority": 1}

        response = self.client.patch(
            self._get_detail_url(Device.objects.get(name="Device 2")), patch_data, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)


class ConsolePortTest(Mixins.BasePortTestMixin):
    model = ConsolePort
    peer_termination_type = ConsoleServerPort

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ConsolePort.objects.create(device=cls.device, name="Console Port 1")
        ConsolePort.objects.create(device=cls.device, name="Console Port 2")
        ConsolePort.objects.create(device=cls.device, name="Console Port 3")

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Console Port 4",
            },
            {
                "device": cls.device.pk,
                "name": "Console Port 5",
            },
            {
                "device": cls.device.pk,
                "name": "Console Port 6",
            },
        ]


class ConsoleServerPortTest(Mixins.BasePortTestMixin):
    model = ConsoleServerPort
    peer_termination_type = ConsolePort

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ConsoleServerPort.objects.create(device=cls.device, name="Console Server Port 1")
        ConsoleServerPort.objects.create(device=cls.device, name="Console Server Port 2")
        ConsoleServerPort.objects.create(device=cls.device, name="Console Server Port 3")

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Console Server Port 4",
            },
            {
                "device": cls.device.pk,
                "name": "Console Server Port 5",
            },
            {
                "device": cls.device.pk,
                "name": "Console Server Port 6",
            },
        ]


class PowerPortTest(Mixins.BasePortTestMixin):
    model = PowerPort
    peer_termination_type = PowerOutlet

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        PowerPort.objects.create(device=cls.device, name="Power Port 1")
        PowerPort.objects.create(device=cls.device, name="Power Port 2")
        PowerPort.objects.create(device=cls.device, name="Power Port 3")

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Power Port 4",
            },
            {
                "device": cls.device.pk,
                "name": "Power Port 5",
            },
            {
                "device": cls.device.pk,
                "name": "Power Port 6",
            },
        ]


class PowerOutletTest(Mixins.BasePortTestMixin):
    model = PowerOutlet
    peer_termination_type = PowerPort
    choices_fields = ["feed_leg", "type"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        PowerOutlet.objects.create(device=cls.device, name="Power Outlet 1")
        PowerOutlet.objects.create(device=cls.device, name="Power Outlet 2")
        PowerOutlet.objects.create(device=cls.device, name="Power Outlet 3")

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Power Outlet 4",
            },
            {
                "device": cls.device.pk,
                "name": "Power Outlet 5",
            },
            {
                "device": cls.device.pk,
                "name": "Power Outlet 6",
            },
        ]


class InterfaceTestVersion12(Mixins.BasePortTestMixin):
    model = Interface
    peer_termination_type = Interface
    choices_fields = ["mode", "type", "status"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.devices = (
            Device.objects.create(
                device_type=cls.device_type, device_role=cls.device_role, name="Device 1", site=cls.site
            ),
            Device.objects.create(
                device_type=cls.device_type, device_role=cls.device_role, name="Device 2", site=cls.site
            ),
            Device.objects.create(
                device_type=cls.device_type, device_role=cls.device_role, name="Device 3", site=cls.site
            ),
        )

        cls.virtual_chassis = VirtualChassis.objects.create(
            name="Virtual Chassis 1", master=cls.devices[0], domain="domain-1"
        )
        Device.objects.filter(id=cls.devices[0].id).update(virtual_chassis=cls.virtual_chassis, vc_position=1)
        Device.objects.filter(id=cls.devices[1].id).update(virtual_chassis=cls.virtual_chassis, vc_position=2)

        cls.interfaces = (
            Interface.objects.create(device=cls.devices[0], name="Interface 1", type="1000base-t"),
            Interface.objects.create(device=cls.devices[0], name="Interface 2", type="1000base-t"),
            Interface.objects.create(device=cls.devices[0], name="Interface 3", type=InterfaceTypeChoices.TYPE_BRIDGE),
            Interface.objects.create(
                device=cls.devices[1], name="Interface 4", type=InterfaceTypeChoices.TYPE_1GE_GBIC
            ),
            Interface.objects.create(device=cls.devices[1], name="Interface 5", type=InterfaceTypeChoices.TYPE_LAG),
            Interface.objects.create(device=cls.devices[2], name="Interface 6", type=InterfaceTypeChoices.TYPE_LAG),
            Interface.objects.create(
                device=cls.devices[2], name="Interface 7", type=InterfaceTypeChoices.TYPE_1GE_GBIC
            ),
        )

        cls.vlans = (
            VLAN.objects.create(name="VLAN 1", vid=1),
            VLAN.objects.create(name="VLAN 2", vid=2),
            VLAN.objects.create(name="VLAN 3", vid=3),
        )

        cls.create_data = [
            {
                "device": cls.devices[0].pk,
                "name": "Interface 8",
                "type": "1000base-t",
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "tagged_vlans": [cls.vlans[0].pk, cls.vlans[1].pk],
                "untagged_vlan": cls.vlans[2].pk,
            },
            {
                "device": cls.devices[0].pk,
                "name": "Interface 9",
                "type": "1000base-t",
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "bridge": cls.interfaces[3].pk,
                "tagged_vlans": [cls.vlans[0].pk, cls.vlans[1].pk],
                "untagged_vlan": cls.vlans[2].pk,
            },
            {
                "device": cls.devices[0].pk,
                "name": "Interface 10",
                "type": "virtual",
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "parent_interface": cls.interfaces[1].pk,
                "tagged_vlans": [cls.vlans[0].pk, cls.vlans[1].pk],
                "untagged_vlan": cls.vlans[2].pk,
            },
        ]

        cls.untagged_vlan_data = {
            "device": cls.devices[0].pk,
            "name": "expected-to-fail",
            "type": InterfaceTypeChoices.TYPE_VIRTUAL,
            "untagged_vlan": cls.vlans[0].pk,
        }

        cls.common_device_or_vc_data = [
            {
                "device": cls.devices[0].pk,
                "name": "interface test 1",
                "type": InterfaceTypeChoices.TYPE_VIRTUAL,
                "parent_interface": cls.interfaces[3].id,  # belongs to different device but same vc
                "bridge": cls.interfaces[2].id,  # belongs to different device but same vc
            },
            {
                "device": cls.devices[0].pk,
                "name": "interface test 2",
                "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
                "lag": cls.interfaces[4].id,  # belongs to different device but same vc
            },
        ]

        cls.interfaces_not_belonging_to_same_device_data = [
            [
                "parent",
                {
                    "device": cls.devices[0].pk,
                    "name": "interface test 1",
                    "type": InterfaceTypeChoices.TYPE_VIRTUAL,
                    "parent_interface": cls.interfaces[6].id,  # do not belong to same device or vc
                },
            ],
            [
                "bridge",
                {
                    "device": cls.devices[0].pk,
                    "name": "interface test 2",
                    "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
                    "bridge": cls.interfaces[6].id,  # does not belong to same device or vc
                },
            ],
            [
                "lag",
                {
                    "device": cls.devices[0].pk,
                    "name": "interface test 3",
                    "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
                    "lag": cls.interfaces[6].id,  # does not belong to same device or vc
                },
            ],
        ]

    def test_active_status_not_found(self):
        self.add_permissions("dcim.add_interface")

        status_active = Status.objects.get_for_model(Interface).get(slug=InterfaceStatusChoices.STATUS_ACTIVE)
        interface_ct = ContentType.objects.get_for_model(Interface)
        status_active.content_types.remove(interface_ct)

        data = {
            "device": self.device.pk,
            "name": "int-001",
            "type": "1000base-t",
            "mode": InterfaceModeChoices.MODE_TAGGED,
        }

        url = self._get_list_url()
        response = self.client.post(url, data, format="json", **self.header)

        self.assertHttpStatus(response, 400)
        self.assertEqual(
            response.data["status"],
            [
                "Interface default status 'active' does not exist, create 'active' status for Interface or use the latest api_version"
            ],
        )

    def test_untagged_vlan_requires_mode(self):
        """Test that when an `untagged_vlan` is specified, `mode` is also required."""
        self.add_permissions("dcim.add_interface")

        # This will fail.
        url = self._get_list_url()
        self.assertHttpStatus(
            self.client.post(url, self.untagged_vlan_data, format="json", **self.header), status.HTTP_400_BAD_REQUEST
        )

        # Now let's add mode and it will work.
        self.untagged_vlan_data["mode"] = InterfaceModeChoices.MODE_ACCESS
        self.assertHttpStatus(
            self.client.post(url, self.untagged_vlan_data, format="json", **self.header), status.HTTP_201_CREATED
        )

    def test_interface_belonging_to_common_device_or_vc_allowed(self):
        """Test parent, bridge, and LAG interfaces belonging to common device or VC is valid"""
        self.add_permissions("dcim.add_interface")

        response = self.client.post(
            self._get_list_url(), data=self.common_device_or_vc_data[0], format="json", **self.header
        )

        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        queryset = Interface.objects.get(name="interface test 1", device=self.devices[0])
        self.assertEqual(queryset.parent_interface, self.interfaces[3])
        self.assertEqual(queryset.bridge, self.interfaces[2])

        # Assert LAG
        self.add_permissions("dcim.add_interface")

        response = self.client.post(
            self._get_list_url(), data=self.common_device_or_vc_data[1], format="json", **self.header
        )

        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        queryset = Interface.objects.get(name="interface test 2", device=self.devices[0])
        self.assertEqual(queryset.lag, self.interfaces[4])

    def test_interface_not_belonging_to_common_device_or_vc_not_allowed(self):
        """Test parent, bridge, and LAG interfaces not belonging to common device or VC is invalid"""

        self.add_permissions("dcim.add_interface")

        for name, payload in self.interfaces_not_belonging_to_same_device_data:
            response = self.client.post(self._get_list_url(), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

            field_name = name.upper() if name == "lag" else name
            error_field_name = f"{name}_interface" if name == "parent" else name

            interface = Interface.objects.get(id=payload[error_field_name])
            self.assertEqual(
                str(response.data[error_field_name][0]),
                f"The selected {field_name} interface ({interface}) belongs to {interface.parent}, which is "
                f"not part of virtual chassis {self.virtual_chassis}.",
            )

    def test_tagged_vlan_raise_error_if_mode_not_set_to_tagged(self):
        self.add_permissions("dcim.add_interface", "dcim.change_interface")
        with self.subTest("On create, assert 400 status."):
            payload = {
                "device": self.devices[0].pk,
                "name": "Tagged Interface",
                "type": "1000base-t",
                "status": "active",
                "mode": InterfaceModeChoices.MODE_ACCESS,
                "tagged_vlans": [self.vlans[0].pk, self.vlans[1].pk],
                "untagged_vlan": self.vlans[2].pk,
            }
            response = self.client.post(self._get_list_url(), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["tagged_vlans"][0], "Mode must be set to tagged when specifying tagged_vlans"
            )

        with self.subTest("On update, assert 400 status."):
            # Error
            interface = Interface.objects.create(
                device=self.devices[0],
                name="Tagged Interface",
                mode=InterfaceModeChoices.MODE_TAGGED,
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
            )
            interface.tagged_vlans.add(self.vlans[0])
            payload = {"mode": None}
            response = self.client.patch(self._get_detail_url(interface), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["tagged_vlans"][0], "Mode must be set to tagged when specifying tagged_vlans"
            )


class InterfaceTestVersion14(InterfaceTestVersion12):
    api_version = "1.4"
    validation_excluded_fields = ["status"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Add status to all payload because status is required in v1.4
        for i, _ in enumerate(cls.create_data):
            cls.create_data[i]["status"] = "active"

        cls.untagged_vlan_data["status"] = "active"

        for i, _ in enumerate(cls.common_device_or_vc_data):
            cls.common_device_or_vc_data[i]["status"] = "active"

        for i, _ in enumerate(cls.interfaces_not_belonging_to_same_device_data):
            cls.interfaces_not_belonging_to_same_device_data[i][1]["status"] = "active"

    @skip("Test not required in v1.4")
    def test_active_status_not_found(self):
        pass


class FrontPortTest(Mixins.BasePortTestMixin):
    model = FrontPort
    peer_termination_type = Interface

    def test_trace(self):
        """FrontPorts don't support trace."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        rear_ports = (
            RearPort.objects.create(device=cls.device, name="Rear Port 1", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=cls.device, name="Rear Port 2", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=cls.device, name="Rear Port 3", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=cls.device, name="Rear Port 4", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=cls.device, name="Rear Port 5", type=PortTypeChoices.TYPE_8P8C),
            RearPort.objects.create(device=cls.device, name="Rear Port 6", type=PortTypeChoices.TYPE_8P8C),
        )

        FrontPort.objects.create(
            device=cls.device,
            name="Front Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_ports[0],
        )
        FrontPort.objects.create(
            device=cls.device,
            name="Front Port 2",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_ports[1],
        )
        FrontPort.objects.create(
            device=cls.device,
            name="Front Port 3",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rear_ports[2],
        )

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Front Port 4",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_ports[3].pk,
                "rear_port_position": 1,
            },
            {
                "device": cls.device.pk,
                "name": "Front Port 5",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_ports[4].pk,
                "rear_port_position": 1,
            },
            {
                "device": cls.device.pk,
                "name": "Front Port 6",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": rear_ports[5].pk,
                "rear_port_position": 1,
            },
        ]


class RearPortTest(Mixins.BasePortTestMixin):
    model = RearPort
    peer_termination_type = Interface

    def test_trace(self):
        """RearPorts don't support trace."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        RearPort.objects.create(device=cls.device, name="Rear Port 1", type=PortTypeChoices.TYPE_8P8C)
        RearPort.objects.create(device=cls.device, name="Rear Port 2", type=PortTypeChoices.TYPE_8P8C)
        RearPort.objects.create(device=cls.device, name="Rear Port 3", type=PortTypeChoices.TYPE_8P8C)

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Rear Port 4",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "device": cls.device.pk,
                "name": "Rear Port 5",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "device": cls.device.pk,
                "name": "Rear Port 6",
                "type": PortTypeChoices.TYPE_8P8C,
            },
        ]


class DeviceBayTest(Mixins.BaseComponentTestMixin):
    model = DeviceBay
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        device_types = (
            DeviceType.objects.filter(subdevice_role=SubdeviceRoleChoices.ROLE_PARENT).first(),
            DeviceType.objects.filter(subdevice_role=SubdeviceRoleChoices.ROLE_CHILD).first(),
        )

        devices = (
            Device.objects.create(
                device_type=device_types[0],
                device_role=cls.device_role,
                name="Device 1",
                site=cls.site,
            ),
            Device.objects.create(
                device_type=device_types[1],
                device_role=cls.device_role,
                name="Device 2",
                site=cls.site,
            ),
            Device.objects.create(
                device_type=device_types[1],
                device_role=cls.device_role,
                name="Device 3",
                site=cls.site,
            ),
            Device.objects.create(
                device_type=device_types[1],
                device_role=cls.device_role,
                name="Device 4",
                site=cls.site,
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


class InventoryItemTest(Mixins.BaseComponentTestMixin):
    model = InventoryItem
    brief_fields = ["_depth", "device", "display", "id", "name", "url"]
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        InventoryItem.objects.create(device=cls.device, name="Inventory Item 1", manufacturer=cls.manufacturer)
        InventoryItem.objects.create(device=cls.device, name="Inventory Item 2", manufacturer=cls.manufacturer)
        InventoryItem.objects.create(device=cls.device, name="Inventory Item 3", manufacturer=cls.manufacturer)

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Inventory Item 4",
                "manufacturer": cls.manufacturer.pk,
            },
            {
                "device": cls.device.pk,
                "name": "Inventory Item 5",
                "manufacturer": cls.manufacturer.pk,
            },
            {
                "device": cls.device.pk,
                "name": "Inventory Item 6",
                "manufacturer": cls.manufacturer.pk,
            },
        ]


class CableTest(Mixins.BaseComponentTestMixin):
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
        super().setUpTestData()

        devices = (
            Device.objects.create(
                device_type=cls.device_type,
                device_role=cls.device_role,
                name="Device 2",
                site=cls.site,
            ),
            Device.objects.create(
                device_type=cls.device_type,
                device_role=cls.device_role,
                name="Device 3",
                site=cls.site,
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

        site = Site.objects.first()
        device_type = DeviceType.objects.exclude(manufacturer__isnull=True).first()
        device_role = DeviceRole.objects.first()

        cable_status = Status.objects.get_for_model(Cable).get(slug="connected")

        self.device1 = Device.objects.create(
            device_type=device_type,
            device_role=device_role,
            name="TestDevice1",
            site=site,
        )
        device2 = Device.objects.create(
            device_type=device_type,
            device_role=device_role,
            name="TestDevice2",
            site=site,
        )
        interface1 = Interface.objects.create(device=self.device1, name="eth0")
        interface2 = Interface.objects.create(device=device2, name="eth0")

        cable = Cable(termination_a=interface1, termination_b=interface2, status=cable_status)
        cable.validated_save()

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
        site = Site.objects.first()
        device_type = DeviceType.objects.exclude(manufacturer__isnull=True).first()
        device_role = DeviceRole.objects.first()

        devices = (
            Device.objects.create(
                name="Device 1",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 2",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 3",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 4",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 5",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 6",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 7",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 8",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 9",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 10",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 11",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 12",
                device_type=device_type,
                device_role=device_role,
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

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_null_master(self):
        """Test setting the virtual chassis master to null."""
        url = reverse("dcim-api:virtualchassis-list")
        response = self.client.get(url + "?name=Virtual Chassis 1", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        virtual_chassis_1 = response.json()["results"][0]

        # Make sure the master is set
        self.assertNotEqual(virtual_chassis_1["master"], None)

        # Set the master of Virtual Chassis 1 to null
        url = reverse("dcim-api:virtualchassis-detail", kwargs={"pk": virtual_chassis_1["id"]})
        payload = {"name": "Virtual Chassis 1", "master": None}
        self.add_permissions(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}")
        response = self.client.patch(url, data=json.dumps(payload), content_type="application/json", **self.header)

        # Make sure the master is now null
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.json()["master"], None)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_remove_chassis_from_master_device(self):
        """Test removing the virtual chassis from the master device."""
        url = reverse("dcim-api:virtualchassis-list")
        response = self.client.get(url + "?name=Virtual Chassis 1", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        virtual_chassis_1 = response.json()["results"][0]

        # Make sure the master is set
        self.assertNotEqual(virtual_chassis_1["master"], None)

        master_device = Device.objects.get(pk=virtual_chassis_1["master"]["id"])

        # Set the virtual_chassis of the master device to null
        url = reverse("dcim-api:device-detail", kwargs={"pk": master_device.id})
        payload = {
            "device_type": str(master_device.device_type.id),
            "device_role": str(master_device.device_role.id),
            "site": str(master_device.site.id),
            "status": "active",
            "virtual_chassis": None,
        }
        self.add_permissions("dcim.change_device")
        response = self.client.patch(url, data=json.dumps(payload), content_type="application/json", **self.header)

        # Make sure deletion attempt failed
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)


class PowerPanelTest(APIViewTestCases.APIViewTestCase):
    model = PowerPanel
    brief_fields = ["display", "id", "name", "powerfeed_count", "url"]

    @classmethod
    def setUpTestData(cls):
        sites = Site.objects.all()[:2]

        rack_groups = (
            RackGroup.objects.create(name="Rack Group 1", slug="rack-group-1", site=sites[0]),
            RackGroup.objects.create(name="Rack Group 2", slug="rack-group-2", site=sites[0]),
            RackGroup.objects.create(name="Rack Group 3", slug="rack-group-3", site=sites[0]),
            RackGroup.objects.create(name="Rack Group 4", slug="rack-group-3", site=sites[1]),
        )

        PowerPanel.objects.create(site=sites[0], rack_group=rack_groups[0], name="Power Panel 1")
        PowerPanel.objects.create(site=sites[0], rack_group=rack_groups[1], name="Power Panel 2")
        PowerPanel.objects.create(site=sites[0], rack_group=rack_groups[2], name="Power Panel 3")

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
        site = Site.objects.first()
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


class DeviceRedundancyGroupTest(APIViewTestCases.APIViewTestCase):
    model = DeviceRedundancyGroup
    brief_fields = ["display", "failover_strategy", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "Device Redundancy Group 4",
            "failover_strategy": "active-active",
            "status": "active",
        },
        {
            "name": "Device Redundancy Group 5",
            "failover_strategy": "active-passive",
            "status": "planned",
        },
        {
            "name": "Device Redundancy Group 6",
            "failover_strategy": "active-active",
            "status": "staging",
        },
    ]
    bulk_update_data = {
        "failover_strategy": "active-passive",
    }
    choices_fields = ["status", "failover_strategy"]

    @classmethod
    def setUpTestData(cls):
        # FIXME(jathan): The writable serializer for `status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for `utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]
