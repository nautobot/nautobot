import datetime
import json
from unittest import skip

from constance.test import override_config
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from nautobot.core.testing import APITestCase, APIViewTestCases
from nautobot.core.testing.utils import generate_random_device_asset_tag_of_specified_size
from nautobot.dcim.choices import (
    ConsolePortTypeChoices,
    InterfaceModeChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedBreakerPoleChoices,
    PowerFeedTypeChoices,
    PowerOutletTypeChoices,
    PowerPanelTypeChoices,
    PowerPortTypeChoices,
    SoftwareImageFileHashingAlgorithmChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.models import (
    Cable,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Controller,
    ControllerManagedDeviceGroup,
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceFamily,
    DeviceRedundancyGroup,
    DeviceType,
    DeviceTypeToSoftwareImageFile,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceRedundancyGroup,
    InterfaceTemplate,
    InterfaceVDCAssignment,
    InventoryItem,
    Location,
    LocationType,
    Manufacturer,
    Module,
    ModuleBay,
    ModuleBayTemplate,
    ModuleFamily,
    ModuleType,
    Platform,
    PowerFeed,
    PowerOutlet,
    PowerOutletTemplate,
    PowerPanel,
    PowerPort,
    PowerPortTemplate,
    Rack,
    RackGroup,
    RackReservation,
    RearPort,
    RearPortTemplate,
    SoftwareImageFile,
    SoftwareVersion,
    VirtualChassis,
    VirtualDeviceContext,
)
from nautobot.extras.models import ConfigContextSchema, ExternalIntegration, Role, SecretsGroup, Status
from nautobot.ipam.models import IPAddress, Namespace, Prefix, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
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
                location=Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first(),
                device_type=DeviceType.objects.first(),
                role=Role.objects.get_for_model(Device).first(),
                status=Status.objects.get_for_model(Device).first(),
                name="Peer Device",
            )
            if self.peer_termination_type is None:
                raise NotImplementedError("Test case must set peer_termination_type")
            if self.peer_termination_type is Interface:
                intf_status = Status.objects.get_for_model(Interface).first()
                peer_obj = self.peer_termination_type.objects.create(
                    device=peer_device, name="Peer Termination", status=intf_status
                )
            else:
                peer_obj = self.peer_termination_type.objects.create(device=peer_device, name="Peer Termination")
            cable_status = Status.objects.get_for_model(Cable).first()
            cable = Cable(termination_a=obj, termination_b=peer_obj, label="Cable 1", status=cable_status)
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
        bulk_update_data = {
            "description": "New description",
        }
        choices_fields = ["type"]

        @classmethod
        def setUpTestData(cls):
            super().setUpTestData()
            cls.device_type = DeviceType.objects.first()
            cls.manufacturer = cls.device_type.manufacturer
            cls.location = Location.objects.filter(location_type__name="Campus").first()
            cls.device_role = Role.objects.get_for_model(Device).first()
            cls.device_status = Status.objects.get_for_model(Device).first()
            cls.device = Device.objects.create(
                device_type=cls.device_type,
                role=cls.device_role,
                name="Device 1",
                location=cls.location,
                status=cls.device_status,
            )
            cls.module = Module.objects.first()
            cls.module_type = cls.module.module_type

    class BasePortTestMixin(ComponentTraceMixin, BaseComponentTestMixin):
        """Mixin class for all `FooPort` tests."""

        peer_termination_type = None

    class BasePortTemplateTestMixin(BaseComponentTestMixin):
        """Mixin class for all `FooPortTemplate` tests."""

    class SoftwareImageFileRelatedModelMixin:
        """
        The SoftwareImageFile hashing_algorithm field includes some values (md5, sha1, etc.) that are
        considered indicators of sensitive data which cause APITestCase.assert_no_verboten_content() to fail.
        We remove those values from the VERBOTEN_STRINGS property to allow the test to pass for any models
        that could return a SoftwareImageFile representation in a depth > 0 API call.
        """

        VERBOTEN_STRINGS = tuple(
            [
                o
                for o in APITestCase.VERBOTEN_STRINGS
                if o not in SoftwareImageFileHashingAlgorithmChoices.as_dict().keys()
            ]
        )

    class ModularDeviceComponentMixin:
        modular_component_create_data = {}
        device_field = "device"  # field name for the parent device
        module_field = "module"  # field name for the parent module
        update_data = {"label": "updated label", "description": "updated description"}

        def test_module_device_validation(self):
            """Assert that a modular component can have a module or a device but not both."""

            self.add_permissions(
                f"{self.model._meta.app_label}.add_{self.model._meta.model_name}",
                "dcim.view_device",
                "dcim.view_module",
                "extras.view_status",
            )
            data = {
                self.module_field: self.module.pk,
                self.device_field: self.device.pk,
                "name": "test parent module validation",
                **self.modular_component_create_data,
            }
            url = self._get_list_url()
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json(),
                {"non_field_errors": [f"Only one of {self.device_field} or {self.module_field} must be set"]},
            )

            data.pop(self.module_field)
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

            data.pop(self.device_field)
            data[self.module_field] = self.module.pk
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

            data.pop(self.module_field)
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json(),
                {"__all__": [f"Either {self.device_field} or {self.module_field} must be set"]},
            )

        def test_module_device_name_unique_validation(self):
            """Assert uniqueness constraint is enforced for (device,name) and (module,name) fields."""

            self.add_permissions(
                f"{self.model._meta.app_label}.add_{self.model._meta.model_name}",
                "dcim.view_device",
                "dcim.view_module",
                "extras.view_status",
            )
            modules = Module.objects.all()[:2]
            data = {
                self.module_field: modules[0].pk,
                "name": "test modular device component parent validation",
                **self.modular_component_create_data,
            }
            url = self._get_list_url()
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json(),
                {"non_field_errors": [f"The fields {self.module_field}, name must make a unique set."]},
            )

            # same name, different module works
            data[self.module_field] = modules[1].pk
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

            devices = Device.objects.all()[:2]
            data = {
                self.device_field: devices[0].pk,
                "name": "test modular device component parent validation",
                **self.modular_component_create_data,
            }
            url = self._get_list_url()
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json(),
                {"non_field_errors": [f"The fields {self.device_field}, name must make a unique set."]},
            )

            # same name, different device works
            data[self.device_field] = devices[1].pk
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

    class ModularDeviceComponentTemplateMixin:
        modular_component_create_data = {}
        update_data = {"label": "updated label", "description": "updated description"}

        def test_module_type_device_type_validation(self):
            """Assert that a modular component template can have a module_type or a device_type but not both."""

            self.add_permissions(
                f"{self.model._meta.app_label}.add_{self.model._meta.model_name}",
                "dcim.view_devicetype",
                "dcim.view_moduletype",
            )
            data = {
                "module_type": self.module_type.pk,
                "device_type": self.device_type.pk,
                "name": "test parent module_type validation",
                **self.modular_component_create_data,
            }
            url = self._get_list_url()
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json(),
                {"non_field_errors": ["Only one of device_type or module_type must be set"]},
            )

            data.pop("module_type")
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

            data.pop("device_type")
            data["module_type"] = self.module_type.pk
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

            data.pop("module_type")
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json(),
                {"__all__": ["Either device_type or module_type must be set"]},
            )

        def test_module_type_device_type_name_unique_validation(self):
            """Assert uniqueness constraint is enforced for (device_type,name) and (module_type,name) fields."""

            self.add_permissions(
                f"{self.model._meta.app_label}.add_{self.model._meta.model_name}",
                "dcim.view_devicetype",
                "dcim.view_moduletype",
            )
            module_types = ModuleType.objects.all()[:2]
            data = {
                "module_type": module_types[0].pk,
                "name": "test modular device component template parent validation",
                **self.modular_component_create_data,
            }
            url = self._get_list_url()
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json(),
                {"non_field_errors": ["The fields module_type, name must make a unique set."]},
            )

            # same name, different module_type works
            data["module_type"] = module_types[1].pk
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

            device_types = DeviceType.objects.all()[:2]
            data = {
                "device_type": device_types[0].pk,
                "name": "test modular device component template parent validation",
                **self.modular_component_create_data,
            }
            url = self._get_list_url()
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json(),
                {"non_field_errors": ["The fields device_type, name must make a unique set."]},
            )

            # same name, different device_type works
            data["device_type"] = device_types[1].pk
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)


class LocationTypeTest(APIViewTestCases.APIViewTestCase, APIViewTestCases.TreeModelAPIViewTestCaseMixin):
    model = LocationType
    bulk_update_data = {
        "description": "Some generic description of multiple types. Not very useful.",
        "nestable": True,
    }
    choices_fields = []  # TODO: what would we need to get ["content_types"] added as a choices field?

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
                "parent": lt3.pk,
                "content_types": ["dcim.device"],
                "description": "An enclosed space smaller than a room",
            },
        ]


class LocationTest(APIViewTestCases.APIViewTestCase, APIViewTestCases.TreeModelAPIViewTestCaseMixin):
    model = Location
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        cls.lt1 = LocationType.objects.get(name="Campus")
        cls.lt2 = LocationType.objects.get(name="Building")
        cls.lt3 = LocationType.objects.get(name="Floor")
        cls.lt4 = LocationType.objects.get(name="Room")

        cls.location_statuses = Status.objects.get_for_model(Location)
        tenant = Tenant.objects.first()

        cls.loc1 = Location.objects.create(name="RTP", location_type=cls.lt1, status=cls.location_statuses[0])
        cls.loc2 = Location.objects.create(
            name="RTP4E", location_type=cls.lt2, status=cls.location_statuses[0], parent=cls.loc1
        )
        cls.loc3 = Location.objects.create(
            name="RTP4E-3", location_type=cls.lt3, status=cls.location_statuses[0], parent=cls.loc2
        )
        cls.loc4 = Location.objects.create(
            name="RTP4E-3-0101", location_type=cls.lt4, status=cls.location_statuses[1], parent=cls.loc3, tenant=tenant
        )
        for loc in [cls.loc1, cls.loc2, cls.loc3, cls.loc4]:
            loc.validated_save()

        cls.create_data = [
            {
                "name": "Downtown Durham",
                "location_type": cls.lt1.pk,
                "status": cls.location_statuses[0].pk,
            },
            {
                "name": "RTP12",
                "location_type": cls.lt2.pk,
                "parent": cls.loc1.pk,
                "status": cls.location_statuses[0].pk,
            },
            {
                "name": "RTP4E-2",
                "location_type": cls.lt3.pk,
                "parent": cls.loc2.pk,
                "status": cls.location_statuses[0].pk,
                "description": "Second floor of RTP4E",
                "tenant": tenant.pk,
            },
        ]

        # Changing location_type of an existing instance is not permitted
        cls.update_data = {
            "name": "A revised location",
            "status": cls.location_statuses[1].pk,
        }
        cls.bulk_update_data = {
            "status": cls.location_statuses[1].pk,
        }

    def test_time_zone_field_post_null(self):
        """
        Test allow_null to time_zone field on locaton.
        """

        self.add_permissions("dcim.add_location", "dcim.view_locationtype", "extras.view_status")
        url = reverse("dcim-api:location-list")
        location = {
            "name": "foo",
            "status": self.location_statuses[0].pk,
            "time_zone": None,
            "location_type": self.lt1.pk,
        }

        # Attempt to create new location with null time_zone attr.
        response = self.client.post(url, **self.header, data=location, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["time_zone"], None)

    def test_time_zone_field_post_blank(self):
        """
        Test disallowed blank time_zone field on location.
        """

        self.add_permissions("dcim.add_location", "dcim.view_locationtype", "extras.view_status")
        url = reverse("dcim-api:location-list")
        location = {
            "name": "foo",
            "status": self.location_statuses[0].pk,
            "time_zone": "",
            "location_type": self.lt1.pk,
        }

        # Attempt to create new location with blank time_zone attr.
        response = self.client.post(url, **self.header, data=location, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["time_zone"], ["This field may not be blank."])

    def test_time_zone_field_post_valid(self):
        """
        Test valid time_zone field on location.
        """

        self.add_permissions("dcim.add_location", "dcim.view_locationtype", "extras.view_status")
        url = reverse("dcim-api:location-list")
        time_zone = "UTC"
        location = {
            "name": "foo",
            "status": self.location_statuses[0].pk,
            "time_zone": time_zone,
            "location_type": self.lt1.pk,
        }

        # Attempt to create new location with valid time_zone attr.
        response = self.client.post(url, **self.header, data=location, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["time_zone"], time_zone)

    def test_time_zone_field_post_invalid(self):
        """
        Test invalid time_zone field on location.
        """

        self.add_permissions("dcim.add_location", "dcim.view_locationtype", "extras.view_status")
        url = reverse("dcim-api:location-list")
        time_zone = "IDONOTEXIST"
        location = {
            "name": "foo",
            "status": self.location_statuses[0].pk,
            "time_zone": time_zone,
            "location_type": self.lt1.pk,
        }

        # Attempt to create new location with invalid time_zone attr.
        response = self.client.post(url, **self.header, data=location, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["time_zone"],
            ["A valid timezone is required."],
        )

    def test_time_zone_field_get_blank(self):
        """
        Test that a location's time_zone field defaults to null.
        """

        self.add_permissions("dcim.view_location")
        location = Location.objects.filter(time_zone="").first()
        url = reverse("dcim-api:location-detail", kwargs={"pk": location.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["time_zone"], None)


class RackGroupTest(APIViewTestCases.APIViewTestCase, APIViewTestCases.TreeModelAPIViewTestCaseMixin):
    model = RackGroup
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        cls.status = Status.objects.get_for_model(Location).first()
        location_type = LocationType.objects.create(name="Location Type 1")
        location_type.content_types.add(ContentType.objects.get_for_model(RackGroup))

        cls.locations = (
            Location.objects.create(name="Location 1", location_type=location_type, status=cls.status),
            Location.objects.create(name="Location 2", location_type=location_type, status=cls.status),
        )
        cls.parent_rack_groups = (
            RackGroup.objects.create(location=cls.locations[0], name="Parent Rack Group 1"),
            RackGroup.objects.create(location=cls.locations[1], name="Parent Rack Group 2"),
        )

        RackGroup.objects.create(
            location=cls.locations[0],
            name="Rack Group 1",
            parent=cls.parent_rack_groups[0],
        )
        RackGroup.objects.create(
            location=cls.locations[0],
            name="Rack Group 2",
            parent=cls.parent_rack_groups[0],
        )
        RackGroup.objects.create(
            location=cls.locations[0],
            name="Rack Group 3",
            parent=cls.parent_rack_groups[0],
        )

        cls.create_data = [
            {
                "name": "Test Rack Group 4",
                "location": cls.locations[1].pk,
                "parent": cls.parent_rack_groups[1].pk,
            },
            {
                "name": "Test Rack Group 5",
                "location": cls.locations[1].pk,
                "parent": cls.parent_rack_groups[1].pk,
            },
            {
                "name": "Test Rack Group 6",
                "location": cls.locations[1].pk,
                "parent": cls.parent_rack_groups[1].pk,
            },
            {
                "name": "Test Rack Group 7",
                "location": cls.locations[1].pk,
                "parent": cls.parent_rack_groups[1].pk,
            },
        ]

    def test_child_group_location_valid(self):
        """A child group with a location may fall within the parent group's location."""
        self.add_permissions("dcim.add_rackgroup", "dcim.view_rackgroup", "dcim.view_location")
        url = reverse("dcim-api:rackgroup-list")

        parent_group = RackGroup.objects.filter(location=self.locations[0]).first()
        child_location_type = LocationType.objects.create(
            name="Child Location Type", parent=self.locations[0].location_type
        )
        child_location_type.content_types.add(ContentType.objects.get_for_model(RackGroup))
        child_location = Location.objects.create(
            name="Child Location", location_type=child_location_type, parent=self.locations[0], status=self.status
        )

        data = {
            "name": "Good Group",
            "parent": parent_group.pk,
            "location": child_location.pk,
        }
        response = self.client.post(url, **self.header, data=data, format="json")
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

    def test_child_group_location_invalid(self):
        """A child group with a location must not fall outside its parent group's location."""
        self.add_permissions("dcim.add_rackgroup", "dcim.view_location", "dcim.view_rackgroup")
        url = reverse("dcim-api:rackgroup-list")

        parent_group = RackGroup.objects.filter(location=self.locations[0]).first()
        # A sibling of locations[0], not a child of it.
        sibling_location = Location.objects.create(
            name="Location 1B", location_type=self.locations[0].location_type, status=self.status
        )

        data = {
            "name": "Good Group",
            "parent": parent_group.pk,
            "location": sibling_location.pk,
        }
        response = self.client.post(url, **self.header, data=data, format="json")
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["location"],
            [
                f'Location "Location 1B" is not descended from parent rack group "{parent_group.name}" location "Location 1".'
            ],
        )


class RackTest(APIViewTestCases.APIViewTestCase):
    model = Rack
    choices_fields = ["outer_unit", "type", "width"]

    @classmethod
    def setUpTestData(cls):
        locations = Location.objects.filter(devices__isnull=False)[:2]
        for location in locations:
            location.location_type.content_types.add(ContentType.objects.get_for_model(RackGroup))
            location.location_type.content_types.add(ContentType.objects.get_for_model(Rack))

        rack_groups = (
            RackGroup.objects.create(location=locations[0], name="Rack Group 1"),
            RackGroup.objects.create(location=locations[1], name="Rack Group 2"),
        )

        rack_roles = Role.objects.get_for_model(Rack)
        statuses = Status.objects.get_for_model(Rack)

        Rack.objects.create(
            location=locations[0],
            rack_group=rack_groups[0],
            role=rack_roles[0],
            name="Rack 1",
            status=statuses[0],
        )
        Rack.objects.create(
            location=locations[0],
            rack_group=rack_groups[0],
            role=rack_roles[0],
            name="Rack 2",
            status=statuses[0],
        )
        Rack.objects.create(
            location=locations[0],
            rack_group=rack_groups[0],
            role=rack_roles[0],
            name="Rack 3",
            status=statuses[0],
        )

        populated_rack = Rack.objects.create(
            location=locations[0],
            rack_group=rack_groups[0],
            role=rack_roles[0],
            name="Populated Rack",
            status=statuses[0],
        )
        # Place a device in Rack 4
        device = Device.objects.filter(location=populated_rack.location, rack__isnull=True).first()
        # Ensure the device height is non-zero, choosing 1 for simplicity
        device.device_type.u_height = 1
        device.device_type.save()
        device.rack = populated_rack
        device.face = "front"
        device.position = 10
        device.save()

        cls.create_data = [
            {
                "name": "Test Rack 4",
                "location": locations[1].pk,
                "rack_group": rack_groups[1].pk,
                "role": rack_roles[1].pk,
                "status": statuses[1].pk,
            },
            {
                "name": "Test Rack 5",
                "location": locations[1].pk,
                "rack_group": rack_groups[1].pk,
                "role": rack_roles[1].pk,
                "status": statuses[1].pk,
            },
            {
                "name": "Test Rack 6",
                "location": locations[1].pk,
                "rack_group": rack_groups[1].pk,
                "role": rack_roles[1].pk,
                "status": statuses[1].pk,
            },
            # Make sure rack_group is not interpreted as a required field
            {
                "name": "Test Rack 7",
                "location": locations[1].pk,
                "role": rack_roles[1].pk,
                "status": statuses[1].pk,
            },
        ]
        cls.bulk_update_data = {
            "status": statuses[1].pk,
        }

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
        params = {"face": "front", "exclude": "a85a31aa-094f-4de9-8ba6-16cb088a1b74"}
        response = self.client.get(url, params, **self.header)
        self.assertHttpStatus(response, 200)

    def test_filter_rack_elevation_is_occupied(self):
        """
        Test filtering the list of rack elevations by occupied status.
        """
        rack = Rack.objects.get(name="Populated Rack")
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-elevation", kwargs={"pk": rack.pk})
        # Get all units first
        params = {"face": "front"}
        response = self.client.get(url, params, **self.header)
        all_units = response.data["results"]
        # Assert the count is equal to the number of units in the rack
        self.assertEqual(len(all_units), rack.u_height)

        # Next get only unoccupied units
        params = {"face": "front", "is_occupied": False}
        response = self.client.get(url, params, **self.header)
        unoccupied_units = response.data["results"]
        # Assert the count is more than 0
        self.assertGreater(len(unoccupied_units), 0)
        # Assert the unoccupied count is less than the total number of units
        self.assertLess(len(unoccupied_units), len(all_units))

        # Next get only occupied units
        params = {"face": "front", "is_occupied": True}
        response = self.client.get(url, params, **self.header)
        occupied_units = response.data["results"]
        # Assert the count is more than 0
        self.assertGreater(len(occupied_units), 0)
        # Assert the occupied count is less than the total number of units
        self.assertLess(len(occupied_units), len(all_units))

        # Assert that the sum of unoccupied and occupied units is equal to the total number of units
        self.assertEqual(len(unoccupied_units) + len(occupied_units), len(all_units))
        # Assert that the lists are mutually exclusive
        self.assertEqual(len([unit for unit in unoccupied_units if unit in occupied_units]), 0)
        self.assertEqual(len([unit for unit in occupied_units if unit in unoccupied_units]), 0)

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

    @override_settings(
        RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT=False,
        RACK_ELEVATION_DEFAULT_UNIT_HEIGHT=22,
        RACK_ELEVATION_DEFAULT_UNIT_WIDTH=230,
    )
    @override_config(RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT=True)
    def test_get_rack_elevation_unit_svg_settings_overridden(self):
        """
        GET a single rack elevation in SVG format, with Django settings specifying the default RU display format
        """
        rack = Rack.objects.first()
        self.add_permissions("dcim.view_rack")
        reverse_url = reverse("dcim-api:rack-elevation", kwargs={"pk": rack.pk})
        url = f"{reverse_url}?render=svg"

        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.get("Content-Type"), "image/svg+xml")
        self.assertIn(b'<text class="unit" x="15.0" y="915.0">1</text>', response.content)

    @override_settings(RACK_ELEVATION_DEFAULT_UNIT_HEIGHT=22, RACK_ELEVATION_DEFAULT_UNIT_WIDTH=230)
    @override_config(RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT=True)
    def test_get_rack_elevation_unit_svg_config_overridden(self):
        """
        GET a single rack elevation in SVG format, with Constance config specifying the 2-digit RU display format
        """
        rack = Rack.objects.first()
        self.add_permissions("dcim.view_rack")
        reverse_url = reverse("dcim-api:rack-elevation", kwargs={"pk": rack.pk})
        url = f"{reverse_url}?render=svg"

        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.get("Content-Type"), "image/svg+xml")
        self.assertIn(b'<text class="unit" x="15.0" y="915.0">01</text>', response.content)


class RackReservationTest(APIViewTestCases.APIViewTestCase):
    model = RackReservation
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="user1", is_active=True)
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        rack_status = Status.objects.get_for_model(Rack).first()

        cls.racks = (
            Rack.objects.create(location=location, name="Rack 1", status=rack_status),
            Rack.objects.create(location=location, name="Rack 2", status=rack_status),
        )

        RackReservation.objects.create(rack=cls.racks[0], units=[1, 2, 3], user=user, description="Reservation #1")
        RackReservation.objects.create(rack=cls.racks[0], units=[4, 5, 6], user=user, description="Reservation #2")
        RackReservation.objects.create(rack=cls.racks[0], units=[7, 8, 9], user=user, description="Reservation #3")

        cls.create_data = [
            {
                "rack": cls.racks[1].pk,
                "units": [10, 11, 12],
                "user": user.pk,
                "description": "Reservation #4",
            },
            {
                "rack": cls.racks[1].pk,
                "units": [13, 14, 15],
                "user": user.pk,
                "description": "Reservation #5",
            },
            {
                "rack": cls.racks[1].pk,
                "units": [16, 17, 18],
                "user": user.pk,
                "description": "Reservation #6",
            },
        ]


class DeviceFamilyTest(APIViewTestCases.APIViewTestCase):
    model = DeviceFamily
    create_data = [
        {
            "name": "Device Family 4",
            "description": "Fourth Device Family",
        },
        {
            "name": "Device Family 5",
        },
        {
            "name": "Device Family 6",
            "description": "Sixth Device Family",
        },
        {
            "name": "Device Family 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        DeviceFamily.objects.create(name="Deletable Device Family 1")
        DeviceFamily.objects.create(name="Deletable Device Family 2", description="Delete this one")
        DeviceFamily.objects.create(name="Deletable Device Family 3")


class ManufacturerTest(APIViewTestCases.APIViewTestCase):
    model = Manufacturer
    create_data = [
        {
            "name": "Test Manufacturer 4",
        },
        {
            "name": "Test Manufacturer 5",
        },
        {
            "name": "Test Manufacturer 6",
        },
        {
            "name": "Test Manufacturer 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    def get_deletable_object(self):
        mf = Manufacturer.objects.create(name="Deletable Manufacturer")
        return mf

    def get_deletable_object_pks(self):
        mfs = [
            Manufacturer.objects.create(name="Deletable Manufacturer 1"),
            Manufacturer.objects.create(name="Deletable Manufacturer 2"),
            Manufacturer.objects.create(name="Deletable Manufacturer 3"),
        ]
        return [mf.pk for mf in mfs]


class DeviceTypeTest(Mixins.SoftwareImageFileRelatedModelMixin, APIViewTestCases.APIViewTestCase):
    model = DeviceType
    bulk_update_data = {
        "part_number": "ABC123",
    }
    choices_fields = ["subdevice_role"]

    @classmethod
    def setUpTestData(cls):
        manufacturer_id = Manufacturer.objects.first().pk
        device_family_id = DeviceFamily.objects.first().pk

        cls.create_data = [
            {
                "manufacturer": manufacturer_id,
                "model": "Device Type 4",
                "device_family": device_family_id,
            },
            {
                "manufacturer": manufacturer_id,
                "model": "Device Type 5",
                "device_family": device_family_id,
            },
            {
                "manufacturer": manufacturer_id,
                "model": "Device Type 6",
            },
            {
                "manufacturer": manufacturer_id,
                "model": "Device Type 7",
            },
        ]


class ModuleTypeTest(APIViewTestCases.APIViewTestCase):
    model = ModuleType
    bulk_update_data = {
        "part_number": "ABC123",
        "comments": "changed comment",
    }

    @classmethod
    def setUpTestData(cls):
        manufacturer_id = Manufacturer.objects.first().pk

        cls.create_data = [
            {
                "manufacturer": manufacturer_id,
                "model": "Module Type 1",
                "part_number": "123456",
                "comments": "test comment",
            },
            {
                "manufacturer": manufacturer_id,
                "model": "Module Type 2",
            },
            {
                "manufacturer": manufacturer_id,
                "model": "Module Type 3",
            },
            {
                "manufacturer": manufacturer_id,
                "model": "Module Type 4",
            },
        ]


class ConsolePortTemplateTest(Mixins.ModularDeviceComponentTemplateMixin, Mixins.BasePortTemplateTestMixin):
    model = ConsolePortTemplate
    modular_component_create_data = {"type": ConsolePortTypeChoices.TYPE_RJ45}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Console Port Template 4",
            },
            {
                "module_type": cls.module_type.pk,
                "name": "Console Port Template 5",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Console Port Template 6",
            },
        ]


class ConsoleServerPortTemplateTest(Mixins.ModularDeviceComponentTemplateMixin, Mixins.BasePortTemplateTestMixin):
    model = ConsoleServerPortTemplate
    modular_component_create_data = {"type": ConsolePortTypeChoices.TYPE_RJ45}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Console Server Port Template 4",
            },
            {
                "module_type": cls.module_type.pk,
                "name": "Console Server Port Template 5",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Console Server Port Template 6",
            },
        ]


class PowerPortTemplateTest(Mixins.ModularDeviceComponentTemplateMixin, Mixins.BasePortTemplateTestMixin):
    model = PowerPortTemplate
    modular_component_create_data = {"type": PowerPortTypeChoices.TYPE_NEMA_1030P}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Power Port Template 4",
            },
            {
                "module_type": cls.module_type.pk,
                "name": "Power Port Template 5",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Power Port Template 6",
            },
        ]


class PowerOutletTemplateTest(Mixins.ModularDeviceComponentTemplateMixin, Mixins.BasePortTemplateTestMixin):
    model = PowerOutletTemplate
    choices_fields = ["feed_leg", "type"]
    modular_component_create_data = {"type": PowerOutletTypeChoices.TYPE_IEC_C13}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Power Outlet Template 4",
            },
            {
                "module_type": cls.module_type.pk,
                "name": "Power Outlet Template 5",
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Power Outlet Template 6",
            },
        ]


class InterfaceTemplateTest(Mixins.ModularDeviceComponentTemplateMixin, Mixins.BasePortTemplateTestMixin):
    model = InterfaceTemplate
    modular_component_create_data = {"type": InterfaceTypeChoices.TYPE_1GE_FIXED}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Interface Template 4",
                "type": "1000base-t",
            },
            {
                "module_type": cls.module_type.pk,
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
    update_data = {"label": "updated label", "description": "updated description"}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.module_type = ModuleType.objects.first()
        cls.module_rear_port_templates = (
            RearPortTemplate.objects.create(module_type=cls.module_type, name="Test FrontPort RP1", positions=100),
            RearPortTemplate.objects.create(module_type=cls.module_type, name="Test FrontPort RP2", positions=100),
        )
        cls.device_type = DeviceType.objects.first()
        cls.device_rear_port_templates = (
            RearPortTemplate.objects.create(device_type=cls.device_type, name="Test FrontPort RP3", positions=100),
            RearPortTemplate.objects.create(device_type=cls.device_type, name="Test FrontPort RP4", positions=100),
        )

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Front Port Template 4",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port_template": cls.device_rear_port_templates[0].pk,
                "rear_port_position": 1,
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Front Port Template 5",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port_template": cls.device_rear_port_templates[1].pk,
                "rear_port_position": 1,
            },
            {
                "module_type": cls.module_type.pk,
                "name": "Front Port Template 6",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port_template": cls.module_rear_port_templates[0].pk,
                "rear_port_position": 1,
            },
        ]

    def test_module_type_device_type_validation(self):
        """Assert that a modular component template can have a module_type or a device_type but not both."""

        self.add_permissions(
            "dcim.add_frontporttemplate", "dcim.view_rearporttemplate", "dcim.view_devicetype", "dcim.view_moduletype"
        )
        data = {
            "module_type": self.module_type.pk,
            "device_type": self.device_type.pk,
            "name": "test parent module_type validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port_template": self.device_rear_port_templates[0].pk,
            "rear_port_position": 2,
        }
        url = self._get_list_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["Only one of device_type or module_type must be set"]},
        )

        data.pop("module_type")
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data.pop("device_type")
        data["module_type"] = self.module_type.pk
        data["rear_port_template"] = self.module_rear_port_templates[0].pk
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

    def test_module_type_device_type_name_unique_validation(self):
        """Assert uniqueness constraint is enforced for (device_type,name) and (module_type,name) fields."""

        self.add_permissions(
            "dcim.add_frontporttemplate", "dcim.view_rearporttemplate", "dcim.view_moduletype", "dcim.view_devicetype"
        )
        data = {
            "module_type": self.module_type.pk,
            "name": "test modular device_type component parent validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port_template": self.module_rear_port_templates[0].pk,
            "rear_port_position": 2,
        }
        url = self._get_list_url()
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data = {
            "module_type": self.module_type.pk,
            "name": "test modular device_type component parent validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port_template": self.module_rear_port_templates[1].pk,
            "rear_port_position": 2,
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["The fields module_type, name must make a unique set."]},
        )

        data = {
            "device_type": self.device_type.pk,
            "name": "test modular device_type component parent validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port_template": self.device_rear_port_templates[0].pk,
            "rear_port_position": 2,
        }
        url = self._get_list_url()
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data = {
            "device_type": self.device_type.pk,
            "name": "test modular device_type component parent validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port_template": self.device_rear_port_templates[1].pk,
            "rear_port_position": 2,
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["The fields device_type, name must make a unique set."]},
        )


class RearPortTemplateTest(Mixins.ModularDeviceComponentTemplateMixin, Mixins.BasePortTemplateTestMixin):
    model = RearPortTemplate
    modular_component_create_data = {"type": PortTypeChoices.TYPE_8P8C}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Rear Port Template 4",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "module_type": cls.module_type.pk,
                "name": "Rear Port Template 5",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "module_type": cls.module_type.pk,
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


class ModuleBayTemplateTest(Mixins.ModularDeviceComponentTemplateMixin, Mixins.BaseComponentTestMixin):
    model = ModuleBayTemplate
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.module_family = ModuleFamily.objects.create(name="Test Module Family")

        cls.create_data = [
            {
                "device_type": cls.device_type.pk,
                "name": "Test1",
                "module_family": cls.module_family.pk,
            },
            {
                "module_type": cls.module_type.pk,
                "name": "Test2",
                "module_family": cls.module_family.pk,
            },
            {
                "device_type": cls.device_type.pk,
                "name": "Test3",
            },
        ]


class PlatformTest(APIViewTestCases.APIViewTestCase):
    model = Platform
    create_data = [
        {
            "name": "Test Platform 4",
            "network_driver": "cisco_ios",
        },
        {
            "name": "Test Platform 5",
        },
        {
            "name": "Test Platform 6",
        },
        {
            "name": "Test Platform 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
        "network_driver": "cisco_xe",
    }

    @classmethod
    def setUpTestData(cls):
        # Protected FK to SoftwareImageFile prevents deletion
        DeviceTypeToSoftwareImageFile.objects.all().delete()
        # Protected FK to SoftwareVersion prevents deletion
        Device.objects.all().update(software_version=None)

    @override_settings(
        NETWORK_DRIVERS={
            "netmiko": {"cisco_ios": "custom_cisco_netmiko"},
            "custom_tool": {"custom_network_driver": "custom_tool_driver"},
        },
    )
    def test_network_driver_mappings(self):
        """
        Check that network_driver_mappings field is correctly exposed by the API
        """
        platform1 = Platform.objects.create(name="Test network driver mappings 1", network_driver="cisco_ios")
        platform2 = Platform.objects.create(
            name="Test network driver mappings 2", network_driver="custom_network_driver"
        )
        self.add_permissions("dcim.view_platform")

        with self.subTest("Test cisco_ios platform with overridden netmiko driver"):
            url = reverse("dcim-api:platform-detail", kwargs={"pk": platform1.pk})
            response = self.client.get(url, **self.header)
            self.assertDictEqual(platform1.network_driver_mappings, response.data["network_driver_mappings"])

        with self.subTest("Test platform with custom network_driver with custom mapped driver"):
            url = reverse("dcim-api:platform-detail", kwargs={"pk": platform2.pk})
            response = self.client.get(url, **self.header)
            self.assertDictEqual(platform2.network_driver_mappings, response.data["network_driver_mappings"])


class DeviceTest(APIViewTestCases.APIViewTestCase):
    model = Device
    choices_fields = ["face"]

    @classmethod
    def setUpTestData(cls):
        Controller.objects.filter(controller_device__isnull=False).delete()
        Device.objects.all().delete()
        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]

        rack_status = Status.objects.get_for_model(Rack).first()
        racks = (
            Rack.objects.create(name="Rack 1", location=locations[0], status=rack_status),
            Rack.objects.create(name="Rack 2", location=locations[1], status=rack_status),
        )

        device_statuses = Status.objects.get_for_model(Device)

        cluster_type = ClusterType.objects.create(name="Cluster Type 1")

        clusters = (
            Cluster.objects.create(name="Cluster 1", cluster_type=cluster_type),
            Cluster.objects.create(name="Cluster 2", cluster_type=cluster_type),
        )

        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
        )

        device_type = DeviceType.objects.first()
        device_role = Role.objects.get_for_model(Device).first()

        software_version = SoftwareVersion.objects.first()
        software_image_files = (
            SoftwareImageFile.objects.create(
                status=Status.objects.get_for_model(SoftwareImageFile).first(),
                software_version=software_version,
                image_file_name="test_software_image_file_1.bin",
            ),
            SoftwareImageFile.objects.create(
                status=Status.objects.get_for_model(SoftwareImageFile).last(),
                software_version=software_version,
                image_file_name="test_software_image_file_2.bin",
            ),
        )
        for software_image_file in software_image_files:
            software_image_file.device_types.add(device_type)

        Device.objects.create(
            device_type=device_type,
            role=device_role,
            status=device_statuses[0],
            name="Device 1",
            location=locations[0],
            rack=racks[0],
            cluster=clusters[0],
            secrets_group=secrets_groups[0],
            local_config_context_data={"A": 1},
            software_version=software_version,
        )
        Device.objects.create(
            device_type=device_type,
            role=device_role,
            status=device_statuses[0],
            name="Device 2",
            location=locations[0],
            rack=racks[0],
            cluster=clusters[0],
            secrets_group=secrets_groups[0],
            local_config_context_data={"B": 2},
            software_version=software_version,
        )
        Device.objects.create(
            device_type=device_type,
            role=device_role,
            status=device_statuses[0],
            name="Device 3",
            location=locations[0],
            rack=racks[0],
            cluster=clusters[0],
            secrets_group=secrets_groups[0],
            local_config_context_data={"C": 3},
        )

        cls.create_data = [
            {
                "device_type": device_type.pk,
                "role": device_role.pk,
                "asset_tag": generate_random_device_asset_tag_of_specified_size(100),
                "status": device_statuses[1].pk,
                "name": "Test Device 4",
                "location": locations[1].pk,
                "rack": racks[1].pk,
                "cluster": clusters[1].pk,
                "secrets_group": secrets_groups[1].pk,
                "software_version": software_version.pk,
                "software_image_files": [software_image_files[0].pk, software_image_files[1].pk],
            },
            {
                "device_type": device_type.pk,
                "role": device_role.pk,
                "status": device_statuses[1].pk,
                "asset_tag": generate_random_device_asset_tag_of_specified_size(100),
                "name": "Test Device 5",
                "location": locations[1].pk,
                "rack": racks[1].pk,
                "cluster": clusters[1].pk,
                "secrets_group": secrets_groups[1].pk,
                "software_version": software_version.pk,
                "software_image_files": [software_image_files[0].pk],
            },
            {
                "device_type": device_type.pk,
                "role": device_role.pk,
                "status": device_statuses[1].pk,
                "asset_tag": generate_random_device_asset_tag_of_specified_size(100),
                "name": "Test Device 6",
                "location": locations[1].pk,
                "rack": racks[1].pk,
                "cluster": clusters[1].pk,
                "secrets_group": secrets_groups[1].pk,
            },
        ]
        cls.bulk_update_data = {
            "status": device_statuses[1].pk,
        }

    def test_config_context_excluded_by_default_in_list_view(self):
        """
        Check that config context data is excluded by default in the devices list.
        """
        self.add_permissions("dcim.view_device")
        url = reverse("dcim-api:device-list")
        response = self.client.get(url, **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertNotIn("config_context", response.data["results"][0])

    def test_config_context_included(self):
        """
        Check that config context data can be included by passing ?include=config_context.
        """
        self.add_permissions("dcim.view_device")
        url = reverse("dcim-api:device-list") + "?include=config_context"
        response = self.client.get(url, **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("config_context", response.data["results"][0])
        self.assertEqual(response.data["results"][0]["config_context"], {"A": 1})

    def test_unique_name_per_location_constraint(self):
        """
        Check that creating a device with a duplicate name within a location fails.
        """
        device = Device.objects.first()
        data = {
            "device_type": device.device_type.pk,
            "role": device.role.pk,
            "location": device.location.pk,
            "name": device.name,
        }

        self.add_permissions("dcim.add_device")
        url = reverse("dcim-api:device-list")
        response = self.client.post(url, data, format="json", **self.header)

        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_local_config_context_schema_validation_pass(self):
        """
        Given a config context schema
        And a device with local context that conforms to that schema
        Assert that the local context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", data_schema={"type": "object", "properties": {"A": {"type": "integer"}}}
        )
        self.add_permissions("dcim.change_device", "extras.view_configcontextschema")

        patch_data = {"local_config_context_schema": str(schema.pk)}

        response = self.client.patch(
            self._get_detail_url(Device.objects.get(name="Device 1")), patch_data, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(str(response.data["local_config_context_schema"]["url"]), self.absolute_api_url(schema))

    def test_local_config_context_schema_schema_validation_fails(self):
        """
        Given a config context schema
        And a device with local context that *does not* conform to that schema
        Assert that the local context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 2", data_schema={"type": "object", "properties": {"B": {"type": "string"}}}
        )
        # Add object-level permission
        self.add_permissions("dcim.change_device")

        patch_data = {"local_config_context_schema": str(schema.pk)}

        response = self.client.patch(
            self._get_detail_url(Device.objects.get(name="Device 2")), patch_data, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_patching_primary_ip4_success(self):
        """
        Validate we can set primary_ip4 on a device using a PATCH.
        """
        # Add object-level permission
        self.add_permissions("dcim.change_device", "ipam.view_ipaddress")

        dev = Device.objects.get(name="Device 3")
        intf_status = Status.objects.get_for_model(Interface).first()
        dev_intf = Interface.objects.create(name="Ethernet1", device=dev, type="1000base-t", status=intf_status)
        ipaddr_status = Status.objects.get_for_model(IPAddress).first()
        prefix_status = Status.objects.get_for_model(Prefix).first()
        namespace = Namespace.objects.first()
        Prefix.objects.create(prefix="192.0.2.0/24", namespace=namespace, status=prefix_status)
        dev_ip_addr = IPAddress.objects.create(address="192.0.2.1/24", namespace=namespace, status=ipaddr_status)
        dev_intf.add_ip_addresses(dev_ip_addr)

        patch_data = {"primary_ip4": dev_ip_addr.pk}

        response = self.client.patch(
            self._get_detail_url(Device.objects.get(name="Device 3")), patch_data, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        dev.refresh_from_db()
        self.assertEqual(dev.primary_ip4, dev_ip_addr)

    def test_patching_device_redundancy_group(self):
        """
        Validate we can set device redundancy group on a device using a PATCH.
        """
        # Add object-level permission
        self.add_permissions("dcim.change_device", "dcim.view_deviceredundancygroup")

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

    def _parent_device_test_data(self):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        device_status = Status.objects.get_for_model(Device).first()
        device_role = Role.objects.get_for_model(Device).first()
        device_type = DeviceType.objects.first()

        device_type_parent = DeviceType.objects.create(
            manufacturer=device_type.manufacturer,
            model=f"{device_type.model} Parent",
            u_height=device_type.u_height,
            subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
        )
        device_type_child = DeviceType.objects.create(
            manufacturer=device_type.manufacturer,
            model=f"{device_type.model} Child",
            u_height=device_type.u_height,
            subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
        )

        parent_device = Device.objects.create(
            device_type=device_type_parent,
            role=device_role,
            status=device_status,
            name="Device Parent",
            location=location,
        )
        device_bay_1 = DeviceBay.objects.create(name="db1", device_id=parent_device.pk)
        device_bay_2 = DeviceBay.objects.create(name="db2", device_id=parent_device.pk)

        return parent_device, device_bay_1, device_bay_2, device_type_child

    def test_creating_device_with_parent_bay(self):
        # Create test data
        parent_device, device_bay_1, device_bay_2, device_type_child = self._parent_device_test_data()

        self.add_permissions(
            "dcim.add_device",
            "dcim.view_device",
            "dcim.view_devicetype",
            "extras.view_role",
            "extras.view_status",
            "dcim.view_location",
            "dcim.view_devicebay",
        )
        url = reverse("dcim-api:device-list")

        # Test creating device with parent bay by device bay data
        data = {
            "device_type": device_type_child.pk,
            "role": parent_device.role.pk,
            "location": parent_device.location.pk,
            "name": "Device parent bay test #1",
            "status": parent_device.status.pk,
            "parent_bay": {"device": {"name": parent_device.name}, "name": device_bay_1.name},
        }

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        created_device = Device.objects.get(name="Device parent bay test #1")
        self.assertEqual(created_device.parent_bay.pk, device_bay_1.pk)

        # Test creating device with parent bay by device_bay.pk
        data = {
            "device_type": device_type_child.pk,
            "role": parent_device.role.pk,
            "location": parent_device.location.pk,
            "name": "Device parent bay test #2",
            "status": parent_device.status.pk,
            "parent_bay": device_bay_2.pk,
        }

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        created_device = Device.objects.get(name="Device parent bay test #2")
        self.assertEqual(created_device.parent_bay.pk, device_bay_2.pk)

        # Test creating device with parent bay already taken
        data = {
            "device_type": device_type_child.pk,
            "role": parent_device.role.pk,
            "location": parent_device.location.pk,
            "name": "Device parent bay test #3",
            "status": parent_device.status.pk,
            "parent_bay": device_bay_1.pk,
        }

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot install device; parent bay is already taken", response.content.decode(response.charset))

        # Assert that on the #1 device, parent bay stayed the same
        old_device = Device.objects.get(name="Device parent bay test #1")
        self.assertEqual(old_device.parent_bay.pk, device_bay_1.pk)

    def test_update_device_with_parent_bay(self):
        # Create test data
        parent_device, device_bay_1, device_bay_2, device_type_child = self._parent_device_test_data()

        self.add_permissions("dcim.change_device", "dcim.view_devicebay")

        child_device = Device.objects.create(
            device_type=device_type_child,
            role=parent_device.role,
            location=parent_device.location,
            name="Device parent bay test #4",
            status=parent_device.status,
        )
        # Test setting parent bay during the update
        patch_data = {"parent_bay": device_bay_1.pk}
        response = self.client.patch(self._get_detail_url(child_device), patch_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        updated_device = Device.objects.get(name="Device parent bay test #4")
        self.assertEqual(updated_device.parent_bay.pk, device_bay_1.pk)

        # Changing the parent bay is not allowed without removing it first
        patch_data = {"parent_bay": device_bay_2.pk}
        response = self.client.patch(self._get_detail_url(child_device), patch_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            f"Cannot install the specified device; device is already installed in {device_bay_1.name}",
            response.content.decode(response.charset),
        )

        # Assert that parent bay stayed the same
        updated_device = Device.objects.get(name="Device parent bay test #4")
        self.assertEqual(updated_device.parent_bay.pk, device_bay_1.pk)

    def test_reassign_device_to_parent_bay(self):
        # Create test data
        parent_device, device_bay_1, device_bay_2, device_type_child = self._parent_device_test_data()
        device_name = "Device parent bay test #5"
        child_device = Device.objects.create(
            device_type=device_type_child,
            role=parent_device.role,
            location=parent_device.location,
            name=device_name,
            status=parent_device.status,
        )
        device_bay_1.installed_device = child_device
        device_bay_1.save()

        self.add_permissions("dcim.change_device", "dcim.view_device", "dcim.change_devicebay", "dcim.view_devicebay")
        child_device_detail_url = self._get_detail_url(child_device)

        response = self.client.get(child_device_detail_url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.json()["parent_bay"]["id"], str(device_bay_1.pk))

        # Test unassigning parent bay
        patch_data = {"parent_bay": None}
        response = self.client.patch(child_device_detail_url, patch_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        child_device.refresh_from_db()
        with self.assertRaises(DeviceBay.DoesNotExist):
            child_device.parent_bay

        # And assign it again
        patch_data = {"parent_bay": device_bay_2.pk}
        response = self.client.patch(child_device_detail_url, patch_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        child_device.refresh_from_db()
        self.assertEqual(child_device.parent_bay.pk, device_bay_2.pk)

        # Unassign it through device bay
        patch_data = {"installed_device": None}
        response = self.client.patch(self._get_detail_url(device_bay_2), patch_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        child_device.refresh_from_db()
        self.assertFalse(hasattr(child_device, "parent_bay"))

        # And assign through device bay
        patch_data = {"installed_device": child_device.pk}
        response = self.client.patch(self._get_detail_url(device_bay_1), patch_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        child_device.refresh_from_db()
        self.assertEqual(child_device.parent_bay.pk, device_bay_1.pk)


class ModuleTestCase(APIViewTestCases.APIViewTestCase):
    model = Module

    @classmethod
    def setUpTestData(cls):
        cls.module_type = ModuleType.objects.first()
        cls.module_bay = ModuleBay.objects.filter(installed_module__isnull=True).first()
        cls.module_status = Status.objects.get_for_model(Module).first()
        cls.location = Location.objects.get_for_model(Module).first()
        cls.create_data = [
            {
                "module_type": cls.module_type.pk,
                "parent_module_bay": cls.module_bay.pk,
                "status": cls.module_status.pk,
            },
            {
                "module_type": cls.module_type.pk,
                "location": cls.location.pk,
                "status": cls.module_status.pk,
            },
            {
                "module_type": cls.module_type.pk,
                "location": cls.location.pk,
                "serial": "test module serial xyz",
                "asset_tag": "test module 2",
                "status": cls.module_status.pk,
            },
            {
                "module_type": cls.module_type.pk,
                "location": cls.location.pk,
                "asset_tag": "Test Module 3",
                "status": cls.module_status.pk,
            },
            {
                "module_type": cls.module_type.pk,
                "location": cls.location.pk,
                "serial": "test module serial abc",
                "status": cls.module_status.pk,
            },
        ]
        cls.bulk_update_data = {
            "tenant": Tenant.objects.first().pk,
        }

        cls.update_data = {
            "serial": "new serial 789",
            "asset_tag": "new asset tag 789",
            "status": Status.objects.get_for_model(Module).last().pk,
        }

    def get_deletable_object_pks(self):
        # Since Modules and ModuleBays are nestable, we need to delete Modules that don't have any child Modules
        return Module.objects.exclude(module_bays__installed_module__isnull=False).values_list("pk", flat=True)[:3]

    def test_parent_module_bay_location_validation(self):
        """Assert that a module can have a parent_module_bay or a location but not both."""

        self.add_permissions(
            "dcim.add_module", "dcim.view_moduletype", "dcim.view_location", "dcim.view_modulebay", "extras.view_status"
        )
        data = {
            "module_type": self.module_type.pk,
            "location": self.location.pk,
            "parent_module_bay": self.module_bay.pk,
            "status": self.module_status.pk,
        }
        url = self._get_list_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["Only one of parent_module_bay or location must be set"]},
        )

        data.pop("parent_module_bay")
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data.pop("location")
        data["parent_module_bay"] = self.module_bay.pk
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data.pop("parent_module_bay")
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"__all__": ["One of location or parent_module_bay must be set"]},
        )

    def test_serial_module_type_unique_validation(self):
        self.add_permissions("dcim.add_module", "dcim.view_location", "dcim.view_moduletype", "extras.view_status")
        data = {
            "module_type": self.module_type.pk,
            "location": self.location.pk,
            "status": self.module_status.pk,
        }
        url = self._get_list_url()
        # create multiple instances with null serial
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
        data["serial"] = ""
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
        data["serial"] = None
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data["serial"] = "xyz"
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["The fields module_type, serial must make a unique set."]},
        )

    def test_asset_tag_unique_validation(self):
        self.add_permissions("dcim.add_module", "dcim.view_location", "dcim.view_moduletype", "extras.view_status")
        data = {
            "module_type": self.module_type.pk,
            "location": self.location.pk,
            "status": self.module_status.pk,
            "asset_tag": "xyz123",
        }
        url = self._get_list_url()
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"asset_tag": ["module with this Asset tag already exists."]},
        )


class ConsolePortTest(Mixins.ModularDeviceComponentMixin, Mixins.BasePortTestMixin):
    model = ConsolePort
    peer_termination_type = ConsoleServerPort
    modular_component_create_data = {"type": ConsolePortTypeChoices.TYPE_RJ45}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Console Port 1",
            },
            {
                "module": cls.module.pk,
                "name": "Console Port 2",
            },
            {
                "device": cls.device.pk,
                "name": "Console Port 3",
            },
        ]


class ConsoleServerPortTest(Mixins.ModularDeviceComponentMixin, Mixins.BasePortTestMixin):
    model = ConsoleServerPort
    peer_termination_type = ConsolePort
    modular_component_create_data = {"type": ConsolePortTypeChoices.TYPE_RJ45}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Console Server Port 1",
            },
            {
                "module": cls.module.pk,
                "name": "Console Server Port 2",
            },
            {
                "device": cls.device.pk,
                "name": "Console Server Port 3",
            },
        ]


class PowerPortTest(Mixins.ModularDeviceComponentMixin, Mixins.BasePortTestMixin):
    model = PowerPort
    peer_termination_type = PowerOutlet
    modular_component_create_data = {"type": PowerPortTypeChoices.TYPE_NEMA_1030P}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Power Port 1",
            },
            {
                "module": cls.module.pk,
                "name": "Power Port 2",
            },
            {
                "device": cls.device.pk,
                "name": "Power Port 3",
            },
        ]


class PowerOutletTest(Mixins.ModularDeviceComponentMixin, Mixins.BasePortTestMixin):
    model = PowerOutlet
    peer_termination_type = PowerPort
    choices_fields = ["feed_leg", "type"]
    modular_component_create_data = {"type": PowerOutletTypeChoices.TYPE_IEC_C13}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Power Outlet 1",
            },
            {
                "module": cls.module.pk,
                "name": "Power Outlet 2",
            },
            {
                "device": cls.device.pk,
                "name": "Power Outlet 3",
            },
        ]


class InterfaceTest(Mixins.ModularDeviceComponentMixin, Mixins.BasePortTestMixin):
    model = Interface
    peer_termination_type = Interface
    choices_fields = ["mode", "type"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        interface_status = Status.objects.get_for_model(Interface).first()
        cls.modular_component_create_data = {
            "type": InterfaceTypeChoices.TYPE_1GE_FIXED,
            "status": interface_status.pk,
        }
        cls.devices = (
            cls.device,
            Device.objects.create(
                device_type=cls.device_type,
                role=cls.device_role,
                status=cls.device_status,
                name="Device 2",
                location=cls.location,
            ),
            Device.objects.create(
                device_type=cls.device_type,
                role=cls.device_role,
                status=cls.device_status,
                name="Device 3",
                location=cls.location,
            ),
        )

        cls.virtual_chassis = VirtualChassis.objects.create(
            name="Virtual Chassis 1", master=cls.devices[0], domain="domain-1"
        )
        Device.objects.filter(id=cls.devices[0].id).update(virtual_chassis=cls.virtual_chassis, vc_position=1)
        Device.objects.filter(id=cls.devices[1].id).update(virtual_chassis=cls.virtual_chassis, vc_position=2)

        # Interfaces have special handling around the "Active" status so let's set our interfaces to something else.
        non_default_status = Status.objects.get_for_model(Interface).exclude(name="Active").first()
        intf_role = Role.objects.get_for_model(Interface).first()
        cls.interfaces = (
            Interface.objects.create(
                device=cls.devices[0],
                name="Test Interface 1",
                type="1000base-t",
                status=non_default_status,
                role=intf_role,
            ),
            Interface.objects.create(
                device=cls.devices[0],
                name="Test Interface 2",
                type="1000base-t",
                status=non_default_status,
            ),
            Interface.objects.create(
                device=cls.devices[0],
                name="Test Interface 3",
                type=InterfaceTypeChoices.TYPE_BRIDGE,
                status=non_default_status,
                role=intf_role,
            ),
            Interface.objects.create(
                device=cls.devices[1],
                name="Test Interface 4",
                type=InterfaceTypeChoices.TYPE_1GE_GBIC,
                status=non_default_status,
                role=intf_role,
            ),
            Interface.objects.create(
                device=cls.devices[1],
                name="Test Interface 5",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=non_default_status,
            ),
            Interface.objects.create(
                device=cls.devices[2],
                name="Test Interface 6",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=non_default_status,
                role=intf_role,
            ),
            Interface.objects.create(
                device=cls.devices[2],
                name="Test Interface 7",
                type=InterfaceTypeChoices.TYPE_1GE_GBIC,
                status=non_default_status,
                role=intf_role,
            ),
        )

        vlan_group = VLANGroup.objects.create(name="Test VLANGroup 1")
        vlan_status = Status.objects.get_for_model(VLAN).first()
        cls.vlans = (
            VLAN.objects.create(name="VLAN 1", vid=1, status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(name="VLAN 2", vid=2, status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(name="VLAN 3", vid=3, status=vlan_status, vlan_group=vlan_group),
        )

        cls.create_data = [
            {
                "device": cls.devices[0].pk,
                "name": "Test Interface 8",
                "type": "1000base-t",
                "status": interface_status.pk,
                "role": intf_role.pk,
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "tagged_vlans": [cls.vlans[0].pk, cls.vlans[1].pk],
                "untagged_vlan": cls.vlans[2].pk,
                "mac_address": "00-01-02-03-04-05",
            },
            {
                "device": cls.devices[0].pk,
                "name": "Test Interface 9",
                "type": "1000base-t",
                "status": interface_status.pk,
                "role": intf_role.pk,
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "bridge": cls.interfaces[3].pk,
                "tagged_vlans": [cls.vlans[0].pk, cls.vlans[1].pk],
                "untagged_vlan": cls.vlans[2].pk,
                "mac_address": None,
            },
            {
                "device": cls.devices[0].pk,
                "name": "Test Interface 10",
                "type": "virtual",
                "status": interface_status.pk,
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
            "status": interface_status.pk,
            "untagged_vlan": cls.vlans[0].pk,
        }

        cls.common_device_or_vc_data = [
            {
                "device": cls.devices[0].pk,
                "name": "interface test 1",
                "type": InterfaceTypeChoices.TYPE_VIRTUAL,
                "status": interface_status.pk,
                "parent_interface": cls.interfaces[3].id,  # belongs to different device but same vc
                "bridge": cls.interfaces[2].id,  # belongs to different device but same vc
            },
            {
                "device": cls.devices[0].pk,
                "name": "interface test 2",
                "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
                "status": interface_status.pk,
                "lag": cls.interfaces[4].id,  # belongs to different device but same vc
            },
        ]

        cls.interfaces_not_belonging_to_same_device_data = [
            [
                "parent",
                {
                    "device": cls.devices[0].pk,
                    "name": "interface test 1",
                    "role": intf_role.pk,
                    "type": InterfaceTypeChoices.TYPE_VIRTUAL,
                    "status": interface_status.pk,
                    "parent_interface": cls.interfaces[6].id,  # do not belong to same device or vc
                },
            ],
            [
                "bridge",
                {
                    "device": cls.devices[0].pk,
                    "name": "interface test 2",
                    "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
                    "role": intf_role.pk,
                    "status": interface_status.pk,
                    "bridge": cls.interfaces[6].id,  # does not belong to same device or vc
                },
            ],
            [
                "lag",
                {
                    "device": cls.devices[0].pk,
                    "name": "interface test 3",
                    "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
                    "status": interface_status.pk,
                    "lag": cls.interfaces[6].id,  # does not belong to same device or vc
                },
            ],
        ]

    def test_untagged_vlan_requires_mode(self):
        """Test that when an `untagged_vlan` is specified, `mode` is also required."""
        self.add_permissions("dcim.add_interface", "dcim.view_device", "extras.view_status", "ipam.view_vlan")

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

    def test_tagged_vlan_must_be_in_the_location_or_parent_locations_of_the_parent_device(self):
        self.add_permissions(
            "dcim.add_interface", "dcim.view_interface", "dcim.view_device", "extras.view_status", "ipam.view_vlan"
        )

        interface_status = Status.objects.get_for_model(Interface).first()
        location = self.devices[0].location
        location_ids = [ancestor.id for ancestor in location.ancestors()]
        non_valid_locations = Location.objects.exclude(pk__in=location_ids)
        faulty_vlan = self.vlans[0]
        faulty_vlan.locations.set([non_valid_locations.first().pk])
        faulty_vlan.validated_save()
        faulty_data = {
            "device": self.devices[0].pk,
            "name": "Test Vlans Interface",
            "type": "virtual",
            "status": interface_status.pk,
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "parent_interface": self.interfaces[1].pk,
            "tagged_vlans": [faulty_vlan.pk, self.vlans[1].pk],
            "untagged_vlan": self.vlans[2].pk,
        }
        response = self.client.post(self._get_list_url(), data=faulty_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            b"must have the same location as the interface's parent device, or is in one of the parents of the interface's parent device's location, or "
            b"it must be global.",
            response.content,
        )

    def test_interface_belonging_to_common_device_or_vc_allowed(self):
        """Test parent, bridge, and LAG interfaces belonging to common device or VC is valid"""
        self.add_permissions("dcim.add_interface", "dcim.view_device", "dcim.view_interface", "extras.view_status")

        response = self.client.post(
            self._get_list_url(), data=self.common_device_or_vc_data[0], format="json", **self.header
        )

        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        queryset = Interface.objects.get(name="interface test 1", device=self.devices[0])
        self.assertEqual(queryset.parent_interface, self.interfaces[3])
        self.assertEqual(queryset.bridge, self.interfaces[2])

        # Assert LAG
        response = self.client.post(
            self._get_list_url(), data=self.common_device_or_vc_data[1], format="json", **self.header
        )

        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        queryset = Interface.objects.get(name="interface test 2", device=self.devices[0])
        self.assertEqual(queryset.lag, self.interfaces[4])

    def test_interface_not_belonging_to_common_device_or_vc_not_allowed(self):
        """Test parent, bridge, and LAG interfaces not belonging to common device or VC is invalid"""

        self.add_permissions(
            "dcim.add_interface", "dcim.view_device", "dcim.view_interface", "extras.view_status", "extras.view_role"
        )

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
        self.add_permissions(
            "dcim.add_interface", "dcim.change_interface", "dcim.view_device", "extras.view_status", "ipam.view_vlan"
        )
        with self.subTest("On create, assert 400 status."):
            payload = {
                "device": self.devices[0].pk,
                "name": "Tagged Interface",
                "type": "1000base-t",
                "status": Status.objects.get_for_model(Interface)[0].pk,
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
                status=Status.objects.get_for_model(Interface).first(),
                role=Role.objects.get_for_model(Interface).first(),
            )
            interface.tagged_vlans.add(self.vlans[0])
            payload = {"mode": None, "tagged_vlans": [self.vlans[2].pk]}
            response = self.client.patch(self._get_detail_url(interface), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["tagged_vlans"][0], "Mode must be set to tagged when specifying tagged_vlans"
            )

    def test_change_mode_from_tagged_to_others(self):
        self.add_permissions("dcim.change_interface")
        interface = Interface.objects.first()
        interface.mode = InterfaceModeChoices.MODE_TAGGED
        interface.validated_save()
        interface.tagged_vlans.add(self.vlans[0])

        with self.subTest("Update Fail"):
            payload = {"mode": InterfaceModeChoices.MODE_ACCESS}
            response = self.client.patch(self._get_detail_url(interface), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["tagged_vlans"][0], "Clear tagged_vlans to set mode to access")

        with self.subTest("Update Successful"):
            payload = {"mode": InterfaceModeChoices.MODE_ACCESS, "tagged_vlans": []}
            response = self.client.patch(self._get_detail_url(interface), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)


class FrontPortTest(Mixins.BasePortTestMixin):
    model = FrontPort
    peer_termination_type = Interface
    update_data = {"label": "updated label", "description": "updated description"}

    def test_trace(self):
        """FrontPorts don't support trace."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.module = Module.objects.first()
        cls.module_rear_ports = (
            RearPort.objects.create(module=cls.module, name="Test FrontPort RP1", positions=100),
            RearPort.objects.create(module=cls.module, name="Test FrontPort RP2", positions=100),
        )
        cls.device = Device.objects.first()
        cls.device_rear_ports = (
            RearPort.objects.create(device=cls.device, name="Test FrontPort RP3", positions=100),
            RearPort.objects.create(device=cls.device, name="Test FrontPort RP4", positions=100),
        )

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Front Port 1",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": cls.device_rear_ports[0].pk,
                "rear_port_position": 1,
            },
            {
                "device": cls.device.pk,
                "name": "Front Port 2",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": cls.device_rear_ports[1].pk,
                "rear_port_position": 1,
            },
            {
                "module": cls.module.pk,
                "name": "Front Port 3",
                "type": PortTypeChoices.TYPE_8P8C,
                "rear_port": cls.module_rear_ports[0].pk,
                "rear_port_position": 1,
            },
        ]

    def test_module_device_validation(self):
        """Assert that a modular component can have a module or a device but not both."""

        self.add_permissions("dcim.add_frontport", "dcim.view_device", "dcim.view_module", "dcim.view_rearport")
        data = {
            "module": self.module.pk,
            "device": self.device.pk,
            "name": "test parent module validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port": self.device_rear_ports[0].pk,
            "rear_port_position": 2,
        }
        url = self._get_list_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["Only one of device or module must be set"]},
        )

        data.pop("module")
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data.pop("device")
        data["module"] = self.module.pk
        data["rear_port"] = self.module_rear_ports[0].pk
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data.pop("module")
        data["rear_port_position"] = 3
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"__all__": ["Either device or module must be set"]},
        )

    def test_module_device_name_unique_validation(self):
        """Assert uniqueness constraint is enforced for (device,name) and (module,name) fields."""

        self.add_permissions("dcim.add_frontport", "dcim.view_module", "dcim.view_rearport", "dcim.view_device")
        data = {
            "module": self.module.pk,
            "name": "test modular device component parent validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port": self.module_rear_ports[0].pk,
            "rear_port_position": 2,
        }
        url = self._get_list_url()
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data = {
            "module": self.module.pk,
            "name": "test modular device component parent validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port": self.module_rear_ports[1].pk,
            "rear_port_position": 2,
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["The fields module, name must make a unique set."]},
        )

        data = {
            "device": self.device.pk,
            "name": "test modular device component parent validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port": self.device_rear_ports[0].pk,
            "rear_port_position": 2,
        }
        url = self._get_list_url()
        self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)

        data = {
            "device": self.device.pk,
            "name": "test modular device component parent validation",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port": self.device_rear_ports[1].pk,
            "rear_port_position": 2,
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["The fields device, name must make a unique set."]},
        )


class RearPortTest(Mixins.ModularDeviceComponentMixin, Mixins.BasePortTestMixin):
    model = RearPort
    peer_termination_type = Interface
    modular_component_create_data = {"type": PortTypeChoices.TYPE_8P8C}

    def test_trace(self):
        """RearPorts don't support trace."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Rear Port 1",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "module": cls.module.pk,
                "name": "Rear Port 2",
                "type": PortTypeChoices.TYPE_8P8C,
            },
            {
                "device": cls.device.pk,
                "name": "Rear Port 3",
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
            # "Device 1" was already created in super().setUpTestData
            Device.objects.create(
                device_type=device_types[0],
                role=cls.device_role,
                status=cls.device_status,
                name="Device 2",
                location=cls.location,
            ),
            Device.objects.create(
                device_type=device_types[1],
                role=cls.device_role,
                status=cls.device_status,
                name="Device 3",
                location=cls.location,
            ),
            Device.objects.create(
                device_type=device_types[1],
                role=cls.device_role,
                status=cls.device_status,
                name="Device 4",
                location=cls.location,
            ),
            Device.objects.create(
                device_type=device_types[1],
                role=cls.device_role,
                status=cls.device_status,
                name="Device 5",
                location=cls.location,
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


class InventoryItemTest(Mixins.BaseComponentTestMixin, APIViewTestCases.TreeModelAPIViewTestCaseMixin):
    model = InventoryItem
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        software_versions = SoftwareVersion.objects.all()[:3]

        InventoryItem.objects.create(device=cls.device, name="Inventory Item 1", manufacturer=cls.manufacturer)
        InventoryItem.objects.create(device=cls.device, name="Inventory Item 2", manufacturer=cls.manufacturer)
        InventoryItem.objects.create(device=cls.device, name="Inventory Item 3", manufacturer=cls.manufacturer)

        cls.create_data = [
            {
                "device": cls.device.pk,
                "name": "Inventory Item 4",
                "manufacturer": cls.manufacturer.pk,
                "software_version": software_versions[0].pk,
            },
            {
                "device": cls.device.pk,
                "name": "Inventory Item 5",
                "manufacturer": cls.manufacturer.pk,
                "software_version": software_versions[1].pk,
            },
            {
                "device": cls.device.pk,
                "name": "Inventory Item 6",
                "manufacturer": cls.manufacturer.pk,
            },
        ]

    # TODO: Unskip after resolving #2908, #2909
    @skip("DRF's built-in InventoryItem nautral_key is infinitely recursive")
    def test_list_objects_ascending_ordered(self):
        pass

    @skip("DRF's built-in InventoryItem nautral_key is infinitely recursive")
    def test_list_objects_descending_ordered(self):
        pass


class ModuleBayTest(Mixins.ModularDeviceComponentMixin, Mixins.BaseComponentTestMixin):
    model = ModuleBay
    choices_fields = []
    device_field = "parent_device"
    module_field = "parent_module"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "parent_device": cls.device.pk,
                "name": "Test1",
            },
            {
                "parent_module": cls.module.pk,
                "name": "Test2",
            },
            {
                "parent_device": cls.device.pk,
                "name": "Test3",
            },
        ]

    def get_deletable_object_pks(self):
        # Since Modules and ModuleBays are nestable, we need to delete ModuleBays that don't have any child ModuleBays
        return ModuleBay.objects.filter(installed_module__isnull=True).values_list("pk", flat=True)[:3]


class CableTest(Mixins.BaseComponentTestMixin):
    model = Cable
    bulk_update_data = {
        "length": 100,
        "length_unit": "m",
    }
    choices_fields = ["termination_a_type", "termination_b_type", "type", "length_unit"]

    # TODO: Allow updating cable terminations
    test_update_object = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        devices = (
            Device.objects.create(
                device_type=cls.device_type,
                role=cls.device_role,
                status=cls.device_status,
                name="Device 2",
                location=cls.location,
            ),
            Device.objects.create(
                device_type=cls.device_type,
                role=cls.device_role,
                status=cls.device_status,
                name="Device 3",
                location=cls.location,
            ),
        )

        interfaces = []
        interface_status = Status.objects.get_for_model(Interface).first()
        interface_role = Role.objects.get_for_model(Interface).first()
        for device in devices:
            for i in range(0, 10):
                interfaces.append(
                    Interface.objects.create(
                        device=device,
                        type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                        name=f"eth{i}",
                        status=interface_status,
                        role=interface_role,
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

        cls.create_data = [
            {
                "termination_a_type": "dcim.interface",
                "termination_a_id": interfaces[4].pk,
                "termination_b_type": "dcim.interface",
                "termination_b_id": interfaces[14].pk,
                "status": statuses[1].pk,
                "label": "Cable 4",
            },
            {
                "termination_a_type": "dcim.interface",
                "termination_a_id": interfaces[5].pk,
                "termination_b_type": "dcim.interface",
                "termination_b_id": interfaces[15].pk,
                "status": statuses[1].pk,
                "label": "Cable 5",
            },
            {
                "termination_a_type": "dcim.interface",
                "termination_a_id": interfaces[6].pk,
                "termination_b_type": "dcim.interface",
                "termination_b_id": interfaces[16].pk,
                "status": statuses[1].pk,
                "label": "Cable 6",
            },
        ]


class ConnectedDeviceTest(APITestCase):
    def setUp(self):
        super().setUp()

        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        device_type = DeviceType.objects.exclude(manufacturer__isnull=True).first()
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()

        cable_status = Status.objects.get_for_model(Cable).get(name="Connected")

        self.device1 = Device.objects.create(
            device_type=device_type,
            role=device_role,
            status=device_status,
            name="TestDevice1",
            location=location,
        )
        device2 = Device.objects.create(
            device_type=device_type,
            role=device_role,
            status=device_status,
            name="TestDevice2",
            location=location,
        )
        interface_status = Status.objects.get_for_model(Interface).first()
        interface1 = Interface.objects.create(
            device=self.device1,
            name="eth0",
            status=interface_status,
        )
        interface2 = Interface.objects.create(
            device=device2,
            name="eth0",
            status=interface_status,
        )

        cable = Cable(termination_a=interface1, termination_b=interface2, status=cable_status)
        cable.validated_save()

    def test_get_connected_device(self):
        url = reverse("dcim-api:connected-device-list")
        response = self.client.get(url + "?peer_device=TestDevice2&peer_interface=eth0", **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)

        self.add_permissions("dcim.view_interface")
        response = self.client.get(url + "?peer_device=TestDevice2&peer_interface=eth0", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.device1.name)


class VirtualChassisTest(APIViewTestCases.APIViewTestCase):
    model = VirtualChassis

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        device_type = DeviceType.objects.exclude(manufacturer__isnull=True).first()
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()

        devices = (
            Device.objects.create(
                name="Device 1",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 2",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 3",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 4",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 5",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 6",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 7",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 8",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 9",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 10",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 11",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
            Device.objects.create(
                name="Device 12",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=location,
            ),
        )

        # Create 12 interfaces per device
        interface_status = Status.objects.get_for_model(Interface).first()
        interface_role = Role.objects.get_for_model(Interface).first()
        interfaces = []
        for i, device in enumerate(devices):
            for j in range(0, 13):
                interfaces.append(
                    # Interface name starts with parent device's position in VC; e.g. 1/1, 1/2, 1/3...
                    Interface.objects.create(
                        device=device,
                        name=f"{i % 3 + 1}/{j}",
                        type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                        status=interface_status,
                        role=interface_role,
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
        self.assertIsNotNone(virtual_chassis_1["master"])

        # The `master` key will be a URL now, but it contains the PK
        master_device = Device.objects.get(pk=virtual_chassis_1["master"]["url"].split("/")[-2])

        # Set the virtual_chassis of the master device to null
        url = reverse("dcim-api:device-detail", kwargs={"pk": master_device.id})
        payload = {
            "device_type": str(master_device.device_type.id),
            "role": str(master_device.role.id),
            "location": str(master_device.location.id),
            "status": "active",
            "virtual_chassis": None,
        }
        self.add_permissions("dcim.change_device")
        response = self.client.patch(url, data=json.dumps(payload), content_type="application/json", **self.header)

        # Make sure deletion attempt failed
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)


class PowerPanelTest(APIViewTestCases.APIViewTestCase):
    model = PowerPanel
    choices_fields = ["panel_type", "power_path"]

    @classmethod
    def setUpTestData(cls):
        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]
        rack_groups = (
            RackGroup.objects.create(name="Rack Group 1", location=locations[0]),
            RackGroup.objects.create(name="Rack Group 2", location=locations[0]),
            RackGroup.objects.create(name="Rack Group 3", location=locations[0]),
            RackGroup.objects.create(name="Rack Group 4", location=locations[1]),
        )

        PowerPanel.objects.create(location=locations[0], rack_group=rack_groups[0], name="Power Panel 1")
        PowerPanel.objects.create(location=locations[0], rack_group=rack_groups[1], name="Power Panel 2")
        PowerPanel.objects.create(location=locations[0], rack_group=rack_groups[2], name="Power Panel 3")

        cls.create_data = [
            {
                "name": "Power Panel 4",
                "location": locations[0].pk,
                "rack_group": rack_groups[0].pk,
            },
            {
                "name": "Power Panel 5",
                "location": locations[0].pk,
                "rack_group": rack_groups[1].pk,
            },
            {
                "name": "Power Panel 6",
                "location": locations[0].pk,
                "rack_group": rack_groups[2].pk,
            },
        ]

        cls.bulk_update_data = {"location": locations[1].pk, "rack_group": rack_groups[3].pk}


class PowerFeedTest(APIViewTestCases.APIViewTestCase):
    model = PowerFeed
    choices_fields = ["phase", "supply", "type", "breaker_pole_count", "power_path"]

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        rackgroup = RackGroup.objects.create(location=location, name="Rack Group 1")
        rackrole = Role.objects.get_for_model(Rack).first()
        rackstatus = Status.objects.get_for_model(Rack).first()

        racks = (
            Rack.objects.create(
                location=location, rack_group=rackgroup, role=rackrole, name="Rack 1", status=rackstatus
            ),
            Rack.objects.create(
                location=location, rack_group=rackgroup, role=rackrole, name="Rack 2", status=rackstatus
            ),
            Rack.objects.create(
                location=location, rack_group=rackgroup, role=rackrole, name="Rack 3", status=rackstatus
            ),
            Rack.objects.create(
                location=location, rack_group=rackgroup, role=rackrole, name="Rack 4", status=rackstatus
            ),
        )

        power_panels = (
            PowerPanel.objects.create(
                location=location,
                rack_group=rackgroup,
                name="Power Panel 1",
                panel_type=PowerPanelTypeChoices.TYPE_UTILITY,
                breaker_position_count=42,
            ),
            PowerPanel.objects.create(
                location=location,
                rack_group=rackgroup,
                name="Power Panel 2",
                panel_type=PowerPanelTypeChoices.TYPE_RPP,
                breaker_position_count=24,
            ),
        )

        PRIMARY = PowerFeedTypeChoices.TYPE_PRIMARY
        REDUNDANT = PowerFeedTypeChoices.TYPE_REDUNDANT
        pf_status = Status.objects.get_for_model(PowerFeed).first()
        PowerFeed.objects.create(
            power_panel=power_panels[0],
            rack=racks[0],
            name="Power Feed 1A",
            status=pf_status,
            type=PRIMARY,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[1],
            rack=racks[0],
            name="Power Feed 1B",
            status=pf_status,
            type=REDUNDANT,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[0],
            rack=racks[1],
            name="Power Feed 2A",
            status=pf_status,
            type=PRIMARY,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[1],
            rack=racks[1],
            name="Power Feed 2B",
            status=pf_status,
            type=REDUNDANT,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[0],
            rack=racks[2],
            name="Power Feed 3A",
            status=pf_status,
            type=PRIMARY,
        )
        PowerFeed.objects.create(
            power_panel=power_panels[1],
            rack=racks[2],
            name="Power Feed 3B",
            status=pf_status,
            type=REDUNDANT,
        )

        statuses = Status.objects.get_for_model(PowerFeed)

        cls.create_data = [
            {
                "name": "Power Feed 4A",
                "power_panel": power_panels[0].pk,
                "destination_panel": power_panels[1].pk,
                "breaker_position": 5,
                "breaker_pole_count": PowerFeedBreakerPoleChoices.POLE_1,
                "rack": racks[3].pk,
                "status": statuses[0].pk,
                "type": PRIMARY,
            },
            {
                "name": "Power Feed 4B",
                "power_panel": power_panels[1].pk,
                "breaker_position": 10,
                "breaker_pole_count": PowerFeedBreakerPoleChoices.POLE_2,
                "rack": racks[3].pk,
                "status": statuses[0].pk,
                "type": REDUNDANT,
            },
        ]
        cls.bulk_update_data = {
            "status": statuses[1].pk,
        }


class DeviceRedundancyGroupTest(APIViewTestCases.APIViewTestCase):
    model = DeviceRedundancyGroup
    choices_fields = ["failover_strategy"]

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(DeviceRedundancyGroup)
        cls.create_data = [
            {
                "name": "Device Redundancy Group 4",
                "failover_strategy": "active-active",
                "status": statuses[0].pk,
            },
            {
                "name": "Device Redundancy Group 5",
                "failover_strategy": "active-passive",
                "status": statuses[0].pk,
            },
            {
                "name": "Device Redundancy Group 6",
                "failover_strategy": "active-active",
                "status": statuses[0].pk,
            },
        ]
        cls.bulk_update_data = {
            "failover_strategy": "active-passive",
            "status": statuses[1].pk,
        }


class InterfaceRedundancyGroupTestCase(APIViewTestCases.APIViewTestCase):
    model = InterfaceRedundancyGroup
    choices_fields = ["protocol"]

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(InterfaceRedundancyGroup)
        ips = IPAddress.objects.all()
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
            SecretsGroup.objects.create(name="Secrets Group 3"),
        )
        # Populating the data secrets_group and virtual_ip here.
        cls.create_data = [
            {
                "name": "Interface Redundancy Group 4",
                "protocol": "hsrp",
                "status": statuses[0].pk,
                "protocol_group_id": "1",
                "secrets_group": secrets_groups[0].pk,
                "virtual_ip": ips[0].pk,
            },
            {
                "name": "Interface Redundancy Group 5",
                "protocol": "vrrp",
                "status": statuses[1].pk,
                "protocol_group_id": "2",
                "secrets_group": secrets_groups[1].pk,
                "virtual_ip": None,
            },
            {
                "name": "Interface Redundancy Group 6",
                "protocol": "glbp",
                "status": statuses[3].pk,
                "protocol_group_id": "3",
                "secrets_group": None,
                "virtual_ip": ips[1].pk,
            },
        ]
        cls.bulk_update_data = {
            "protocol": "carp",
            "status": statuses[2].pk,
            "virtual_ip": ips[0].pk,
        }

        interface_redundancy_groups = (
            InterfaceRedundancyGroup(
                name="Test Interface Redundancy Group 1",
                protocol="hsrp",
                status=statuses[0],
                virtual_ip=None,
                protocol_group_id="4",
                secrets_group=secrets_groups[0],
            ),
            InterfaceRedundancyGroup(
                name="Test Interface Redundancy Group 2",
                protocol="carp",
                status=statuses[1],
                virtual_ip=ips[1],
                protocol_group_id="5",
                secrets_group=secrets_groups[1],
            ),
            InterfaceRedundancyGroup(
                name="Test Interface Redundancy Group 3",
                protocol="vrrp",
                status=statuses[2],
                virtual_ip=ips[2],
                protocol_group_id="6",
                secrets_group=None,
            ),
        )

        for group in interface_redundancy_groups:
            group.validated_save()

        cls.device_status = Status.objects.get_for_model(Device).first()
        cls.device_type = DeviceType.objects.first()
        cls.device_role = Role.objects.get_for_model(Device).first()
        cls.location = Location.objects.filter(location_type__name="Campus").first()
        cls.device = Device.objects.create(
            device_type=cls.device_type,
            role=cls.device_role,
            name="Device 1",
            location=cls.location,
            status=cls.device_status,
        )
        non_default_status = Status.objects.get_for_model(Interface).exclude(name="Active").first()
        cls.interfaces = (
            Interface.objects.create(
                device=cls.device,
                name="Test Interface 1",
                type="1000base-t",
                status=non_default_status,
            ),
            Interface.objects.create(
                device=cls.device,
                name="Test Interface 2",
                type="1000base-t",
                status=non_default_status,
            ),
            Interface.objects.create(
                device=cls.device,
                name="Test Interface 3",
                type=InterfaceTypeChoices.TYPE_BRIDGE,
                status=non_default_status,
            ),
        )
        for i, interface in enumerate(cls.interfaces):
            interface_redundancy_groups[0].add_interface(interface, i * 100)


class SoftwareImageFileTestCase(Mixins.SoftwareImageFileRelatedModelMixin, APIViewTestCases.APIViewTestCase):
    model = SoftwareImageFile
    choices_fields = ["hashing_algorithm"]

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(SoftwareImageFile)
        software_versions = SoftwareVersion.objects.all()
        external_integrations = ExternalIntegration.objects.all()

        cls.create_data = [
            {
                "software_version": software_versions[0].pk,
                "status": statuses[0].pk,
                "image_file_name": "software_image_file_test_case_1.bin",
                "external_integration": external_integrations[0].pk,
            },
            {
                "software_version": software_versions[1].pk,
                "status": statuses[1].pk,
                "image_file_name": "software_image_file_test_case_2.bin",
                "external_integration": external_integrations[1].pk,
            },
            {
                "software_version": software_versions[2].pk,
                "status": statuses[2].pk,
                "image_file_name": "software_image_file_test_case_3.bin",
                "external_integration": None,
            },
        ]
        cls.bulk_update_data = {
            "software_version": software_versions[0].pk,
            "status": statuses[0].pk,
            "image_file_checksum": "abcdef1234567890",
            "hashing_algorithm": SoftwareImageFileHashingAlgorithmChoices.SHA512,
            "image_file_size": 1234567890,
            "download_url": "https://example.com/software_image_file_test_case.bin",
            "external_integration": external_integrations[0].pk,
        }


class SoftwareVersionTestCase(Mixins.SoftwareImageFileRelatedModelMixin, APIViewTestCases.APIViewTestCase):
    model = SoftwareVersion

    @classmethod
    def setUpTestData(cls):
        DeviceTypeToSoftwareImageFile.objects.all().delete()  # Protected FK to SoftwareImageFile prevents deletion
        statuses = Status.objects.get_for_model(SoftwareVersion)
        platforms = Platform.objects.all()

        cls.create_data = [
            {
                "platform": platforms[0].pk,
                "status": statuses[0].pk,
                "version": "version 1.1.0",
            },
            {
                "platform": platforms[1].pk,
                "status": statuses[1].pk,
                "version": "version 1.2.0",
            },
            {
                "platform": platforms[2].pk,
                "status": statuses[2].pk,
                "version": "version 1.3.0",
            },
        ]
        cls.bulk_update_data = {
            "platform": platforms[0].pk,
            "status": statuses[0].pk,
            "alias": "Version x.y.z",
            "release_date": datetime.date(2001, 12, 31),
            "end_of_support_date": datetime.date(2005, 12, 31),
            "documentation_url": "https://example.com/software_version_test_case/docs2",
            "long_term_support": False,
            "pre_release": True,
        }


class DeviceTypeToSoftwareImageFileTestCase(
    Mixins.SoftwareImageFileRelatedModelMixin, APIViewTestCases.APIViewTestCase
):
    model = DeviceTypeToSoftwareImageFile

    @classmethod
    def setUpTestData(cls):
        DeviceTypeToSoftwareImageFile.objects.all().delete()
        device_types = DeviceType.objects.all()[:4]
        software_image_files = SoftwareImageFile.objects.all()[:3]

        # deletable objects
        DeviceTypeToSoftwareImageFile.objects.create(
            device_type=device_types[0],
            software_image_file=software_image_files[0],
        )
        DeviceTypeToSoftwareImageFile.objects.create(
            device_type=device_types[0],
            software_image_file=software_image_files[1],
        )
        DeviceTypeToSoftwareImageFile.objects.create(
            device_type=device_types[0],
            software_image_file=software_image_files[2],
        )

        cls.create_data = [
            {
                "software_image_file": software_image_files[0].pk,
                "device_type": device_types[1].pk,
            },
            {
                "software_image_file": software_image_files[1].pk,
                "device_type": device_types[2].pk,
            },
            {
                "software_image_file": software_image_files[2].pk,
                "device_type": device_types[3].pk,
            },
        ]


class ControllerTestCase(APIViewTestCases.APIViewTestCase):
    model = Controller

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(Controller)
        roles = Role.objects.get_for_model(Controller)
        platforms = Platform.objects.all()
        locations = Location.objects.get_for_model(Controller).all()

        cls.create_data = [
            {
                "name": "Controller 1",
                "platform": platforms[0].pk,
                "status": statuses[0].pk,
                "role": roles[0].pk,
                "location": locations[0].pk,
                "capabilities": [],
            },
            {
                "name": "Controller 2",
                "platform": platforms[1].pk,
                "status": statuses[1].pk,
                "role": roles[1].pk,
                "location": locations[1].pk,
            },
            {
                "name": "Controller 3",
                "platform": platforms[2].pk,
                "status": statuses[2].pk,
                "role": roles[2].pk,
                "location": locations[2].pk,
                "capabilities": ["wireless"],
            },
        ]
        cls.bulk_update_data = {
            "platform": platforms[0].pk,
            "status": statuses[0].pk,
            "role": roles[0].pk,
        }


class ControllerManagedDeviceGroupTestCase(APIViewTestCases.APIViewTestCase):
    model = ControllerManagedDeviceGroup

    @classmethod
    def setUpTestData(cls):
        controllers = Controller.objects.all()

        cls.create_data = [
            {
                "name": "ControllerManagedDeviceGroup 1",
                "controller": controllers[0].pk,
                "weight": 100,
                "capabilities": [],
            },
            {
                "name": "ControllerManagedDeviceGroup 2",
                "controller": controllers[1].pk,
                "weight": 150,
            },
            {
                "name": "ControllerManagedDeviceGroup 3",
                "controller": controllers[2].pk,
                "weight": 200,
                "capabilities": ["wireless"],
            },
        ]
        # changing controller is error-prone since a child group must have the same controller as its parent
        cls.update_data = {
            "weight": 300,
        }
        cls.bulk_update_data = {
            "weight": 300,
        }


class VirtualDeviceContextTestCase(APIViewTestCases.APIViewTestCase):
    model = VirtualDeviceContext

    @classmethod
    def setUpTestData(cls):
        devices = Device.objects.all()
        vdc_status = Status.objects.get_for_model(VirtualDeviceContext)[0]
        vdc_role = Role.objects.first()
        vdc_role.content_types.add(ContentType.objects.get_for_model(VirtualDeviceContext))
        tenants = Tenant.objects.all()

        cls.create_data = [
            {
                "name": "Virtual Device Context 1",
                "device": devices[0].pk,
                "identifier": 100,
                "status": vdc_status.pk,
                "role": vdc_role.pk,
            },
            {
                "name": "Virtual Device Context 2",
                "device": devices[1].pk,
                "identifier": 200,
                "status": vdc_status.pk,
                "tenant": tenants[1].pk,
            },
            {
                "name": "Virtual Device Context 3",
                "identifier": 300,
                "device": devices[2].pk,
                "status": vdc_status.pk,
                "tenant": tenants[2].pk,
                "role": vdc_role.pk,
            },
        ]
        cls.update_data = {
            "tenant": tenants[3].pk,
            "role": vdc_role.pk,
        }
        cls.bulk_update_data = {
            "tenant": tenants[4].pk,
        }

    def test_patching_primary_ip_success(self):
        """
        Validate we can set primary_ip on a Virtual Device Context using a PATCH.
        """
        # Add object-level permission
        self.add_permissions("dcim.change_virtualdevicecontext", "ipam.view_ipaddress")
        vdc = VirtualDeviceContext.objects.first()
        device = vdc.device
        intf_status = Status.objects.get_for_model(Interface).first()
        intf_role = Role.objects.get_for_model(Interface).first()
        interface = Interface.objects.create(
            name="Int1",
            device=device,
            status=intf_status,
            role=intf_role,
            type=InterfaceTypeChoices.TYPE_100GE_CFP,
        )
        ip_v4 = IPAddress.objects.filter(ip_version=4).first()
        ip_v6 = IPAddress.objects.filter(ip_version=6).first()
        interface.virtual_device_contexts.add(vdc)
        interface.add_ip_addresses([ip_v4, ip_v6])

        with self.subTest("Patch Primary ip4"):
            patch_data = {"primary_ip4": ip_v4.pk}

            response = self.client.patch(self._get_detail_url(vdc), patch_data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            vdc.refresh_from_db()
            self.assertEqual(vdc.primary_ip4, ip_v4)

        with self.subTest("Patch Primary ip6"):
            patch_data = {"primary_ip6": ip_v6.pk}

            response = self.client.patch(self._get_detail_url(vdc), patch_data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            vdc.refresh_from_db()
            self.assertEqual(vdc.primary_ip6, ip_v6)

    def test_changing_device_on_vdc_raise_validation_error(self):
        """
        Validate that changing device on the virutal device context is not allowed.
        """
        self.add_permissions("dcim.change_virtualdevicecontext", "dcim.view_device")
        vdc = VirtualDeviceContext.objects.first()
        old_device = vdc.device
        new_device = Device.objects.exclude(pk=old_device.pk).first()
        patch_data = {"device": new_device.pk}
        response = self.client.patch(self._get_detail_url(vdc), patch_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Changing the device of a VirtualDeviceContext is not allowed.", response.data["non_field_errors"][0]
        )


class InterfaceVDCAssignmentTestCase(APIViewTestCases.APIViewTestCase):
    model = InterfaceVDCAssignment

    @classmethod
    def setUpTestData(cls):
        device = Device.objects.first()
        vdc_status = Status.objects.get_for_model(VirtualDeviceContext)[0]
        interface_status = Status.objects.get_for_model(Interface)[0]
        interfaces = [
            Interface.objects.create(
                device=device,
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                name=f"Interface 00{idx}",
                status=interface_status,
            )
            for idx in range(3)
        ]
        vdcs = [
            VirtualDeviceContext.objects.create(
                device=device,
                status=vdc_status,
                identifier=200 + idx,
                name=f"Test VDC {idx}",
            )
            for idx in range(3)
        ]
        # Create some deletable objects
        InterfaceVDCAssignment.objects.create(
            virtual_device_context=vdcs[0],
            interface=interfaces[1],
        )
        InterfaceVDCAssignment.objects.create(
            virtual_device_context=vdcs[0],
            interface=interfaces[2],
        )
        InterfaceVDCAssignment.objects.create(
            virtual_device_context=vdcs[1],
            interface=interfaces[2],
        )

        cls.create_data = [
            {
                "virtual_device_context": vdcs[0].pk,
                "interface": interfaces[0].pk,
            },
            {
                "virtual_device_context": vdcs[1].pk,
                "interface": interfaces[1].pk,
            },
            {
                "virtual_device_context": vdcs[2].pk,
                "interface": interfaces[2].pk,
            },
        ]

    def test_docs(self):
        """Skip: InterfaceVDCAssignment has no docs yet"""
        # TODO(timizuo): Add docs for Interface VDC Assignment


class ModuleFamilyTest(APIViewTestCases.APIViewTestCase):
    """Test the ModuleFamily API."""

    model = ModuleFamily
    brief_fields = ["display", "id", "name", "url"]
    create_data = [
        {
            "name": "Module Family 4",
            "description": "Fourth family",
        },
        {
            "name": "Module Family 5",
            "description": "Fifth family",
        },
        {
            "name": "Module Family 6",
            "description": "Sixth family",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        """Create test data for API tests."""
        ModuleFamily.objects.create(name="Module Family 1", description="First family")
        ModuleFamily.objects.create(name="Module Family 2", description="Second family")
        ModuleFamily.objects.create(name="Module Family 3", description="Third family")
