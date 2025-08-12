import datetime
from decimal import Decimal
import unittest
import zoneinfo

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.test import override_settings
from django.urls import reverse
from netaddr import EUI
import yaml

from nautobot.circuits.choices import CircuitTerminationSideChoices
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.core.templatetags.buttons import job_export_url, job_import_url
from nautobot.core.testing import (
    extract_page_body,
    ModelViewTestCase,
    post_data,
    ViewTestCases,
)
from nautobot.core.testing.utils import (
    generate_random_device_asset_tag_of_specified_size,
)
from nautobot.dcim.choices import (
    CableLengthUnitChoices,
    CableTypeChoices,
    ConsolePortTypeChoices,
    DeviceFaceChoices,
    DeviceRedundancyGroupFailoverStrategyChoices,
    InterfaceModeChoices,
    InterfaceRedundancyGroupProtocolChoices,
    InterfaceTypeChoices,
    LocationDataToContactActionChoices,
    PortTypeChoices,
    PowerFeedPhaseChoices,
    PowerFeedSupplyChoices,
    PowerFeedTypeChoices,
    PowerOutletFeedLegChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    RackDimensionUnitChoices,
    RackTypeChoices,
    RackWidthChoices,
    SoftwareImageFileHashingAlgorithmChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.filters import (
    ConsoleConnectionFilterSet,
    ControllerFilterSet,
    ControllerManagedDeviceGroupFilterSet,
    InterfaceConnectionFilterSet,
    PowerConnectionFilterSet,
    SoftwareImageFileFilterSet,
    SoftwareVersionFilterSet,
    VirtualDeviceContextFilterSet,
)
from nautobot.dcim.models import (
    Cable,
    CablePath,
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
    InterfaceRedundancyGroupAssociation,
    InterfaceTemplate,
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
from nautobot.dcim.views import (
    ConsoleConnectionsListView,
    InterfaceConnectionsListView,
    PowerConnectionsListView,
)
from nautobot.extras.choices import CustomFieldTypeChoices, RelationshipTypeChoices
from nautobot.extras.models import (
    ConfigContextSchema,
    Contact,
    ContactAssociation,
    CustomField,
    CustomFieldChoice,
    ExternalIntegration,
    JobResult,
    Relationship,
    RelationshipAssociation,
    Role,
    SecretsGroup,
    Status,
    Tag,
    Team,
)
from nautobot.ipam.choices import IPAddressTypeChoices
from nautobot.ipam.models import IPAddress, Namespace, Prefix, VLAN, VLANGroup, VRF
from nautobot.tenancy.models import Tenant
from nautobot.users.models import ObjectPermission
from nautobot.virtualization.models import Cluster, ClusterType

# Use the proper swappable User model
User = get_user_model()


def create_test_device(name):
    """
    Convenience method for creating a Device (e.g. for component testing).
    """
    location_type, _ = LocationType.objects.get_or_create(name="Campus")
    location_status = Status.objects.get_for_model(Location).first()
    location, _ = Location.objects.get_or_create(
        name="Test Location 1", location_type=location_type, status=location_status
    )
    manufacturer, _ = Manufacturer.objects.get_or_create(name="Manufacturer 1")
    devicetype, _ = DeviceType.objects.get_or_create(model="Device Type 1", manufacturer=manufacturer)
    devicerole, _ = Role.objects.get_or_create(name="Device Role")
    device_ct = ContentType.objects.get_for_model(Device)
    devicerole.content_types.add(device_ct)
    devicestatus = Status.objects.get_for_model(Device).first()
    device = Device.objects.create(
        name=name,
        location=location,
        device_type=devicetype,
        role=devicerole,
        status=devicestatus,
    )

    return device


class LocationTypeTestCase(ViewTestCases.OrganizationalObjectViewTestCase, ViewTestCases.BulkEditObjectsViewTestCase):
    model = LocationType
    sort_on_field = "nestable"

    @classmethod
    def setUpTestData(cls):
        # note that we need two root objects because the DeleteObjectViewTestCase expects to be able to delete either
        # of the first two objects in the queryset independently; if lt2 were a child of lt1, then deleting lt1 would
        # cascade-delete lt2, resulting in a test failure.
        lt1 = LocationType.objects.get(name="Root")
        lt2 = LocationType.objects.get(name="Campus")
        lt3 = LocationType.objects.get(name="Building")
        lt4 = LocationType.objects.get(name="Floor")
        for lt in [lt1, lt2, lt3, lt4]:
            lt.content_types.add(ContentType.objects.get_for_model(RackGroup))
        # Deletable Location Types
        LocationType.objects.create(name="Delete Me 1")
        LocationType.objects.create(name="Delete Me 2")
        LocationType.objects.create(name="Delete Me 3")

        # Similarly, EditObjectViewTestCase expects to be able to change lt1 with the below form_data,
        # so we need to make sure we're not trying to introduce a reference loop to the LocationType tree...
        cls.form_data = {
            "name": "Intermediate 2",
            "parent": lt1.pk,
            "description": "Another intermediate type",
            "content_types": [
                ContentType.objects.get_for_model(Rack).pk,
                ContentType.objects.get_for_model(Device).pk,
            ],
            "nestable": True,
        }

        cls.bulk_edit_data = {
            "description": "A generic description",
            "add_content_types": [
                ContentType.objects.get_for_model(CircuitTermination).pk,
            ],
        }

    def _get_queryset(self):
        return super()._get_queryset().order_by("-last_updated")


class LocationTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Location

    @classmethod
    def setUpTestData(cls):
        cls.contact_statuses = Status.objects.get_for_model(ContactAssociation)
        cls.contact_roles = Role.objects.get_for_model(ContactAssociation)
        lt1 = LocationType.objects.get(name="Campus")
        lt2 = LocationType.objects.get(name="Building")
        lt3 = LocationType.objects.get(name="Floor")

        status = Status.objects.get_for_model(Location).first()
        tenant = Tenant.objects.first()

        loc1 = Location.objects.create(name="Root 1", location_type=lt1, status=status)
        loc2 = Location.objects.create(name="Root 2", location_type=lt1, status=status, tenant=tenant)
        loc3 = Location.objects.create(name="Intermediate 1", location_type=lt2, parent=loc2, status=status)
        loc4 = Location.objects.create(
            name="Leaf 1",
            location_type=lt3,
            parent=loc3,
            status=status,
            description="Hi!",
        )
        for loc in [loc1, loc2, loc3, loc4]:
            loc.validated_save()

        cls.form_data = {
            "location_type": lt1.pk,
            "parent": None,
            "name": "Root 3",
            "status": status.pk,
            "tenant": tenant.pk,
            "facility": "Facility X",
            "asn": 65001,
            "time_zone": zoneinfo.ZoneInfo("UTC"),
            "physical_address": "742 Evergreen Terrace, Springfield, USA",
            "shipping_address": "742 Evergreen Terrace, Springfield, USA",
            "latitude": Decimal("35.780000"),
            "longitude": Decimal("-78.642000"),
            "contact_name": "Hank Hill",
            "contact_phone": "123-555-9999",
            "contact_email": "hank@stricklandpropane.com",
            "comments": "Test Location",
            "tags": [t.pk for t in Tag.objects.get_for_model(Location)],
            "description": "A new root location",
        }

        cls.bulk_edit_data = {
            "description": "A generic description",
            # Because we have a mix of root and non-root LocationTypes,
            # we can't bulk-edit the parent in this generic test
            "tenant": tenant.pk,
            "status": Status.objects.get_for_model(Location).last().pk,
            "asn": 65009,
            "time_zone": zoneinfo.ZoneInfo("US/Eastern"),
        }

    def _get_queryset(self):
        return super()._get_queryset().filter(location_type__name="Campus")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_child_location_under_a_non_globally_unique_named_parent_location(
        self,
    ):
        self.add_permissions("dcim.add_location")
        status = Status.objects.get_for_model(Location).first()
        region_type = LocationType.objects.create(name="Region")
        site_type = LocationType.objects.create(name="Site", parent=region_type)
        building_type = LocationType.objects.create(name="Building Type", parent=site_type)
        region_1 = Location.objects.create(name="Region 1", location_type=region_type, status=status)
        region_2 = Location.objects.create(name="Region 2", location_type=region_type, status=status)
        site_1 = Location.objects.create(name="Generic Site", location_type=site_type, parent=region_1, status=status)
        Location.objects.create(name="Generic Site", location_type=site_type, parent=region_2, status=status)
        test_form_data = {
            "location_type": building_type.pk,
            "parent": "Generic Site",
            "name": "Root 3",
            "status": status.pk,
            "tags": [t.pk for t in Tag.objects.get_for_model(Location)],
        }
        request = {
            "path": self._get_url("add"),
            "data": post_data(test_form_data),
        }
        response = self.client.post(**request)
        self.assertBodyContains(response, "“Generic Site” is not a valid UUID.")
        test_form_data["parent"] = site_1.pk
        request["data"] = post_data(test_form_data)
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(Location.objects.get(name="Root 3").parent.pk, site_1.pk)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_migrate_location_data_from_location_assign(self):
        self.add_permissions("dcim.change_location")
        location = Location.objects.first()
        location.contact_name = "Should be unique Contact Name"
        location.contact_phone = "123123123"
        location.contact_email = "helloword@example.com"
        location.physical_address = "418 Brown Locks Barrettchester, NM 85792"
        location.shipping_address = "53 blue Locks manchester, NY 12124"
        similar_contact = Contact.objects.first()
        role = self.contact_roles.first().pk
        status = self.contact_statuses.first().pk
        form_data = {
            "action": LocationDataToContactActionChoices.ASSOCIATE_EXISTING_CONTACT,
            "contact": similar_contact.pk,
            "role": role,
            "status": status,
        }
        request = {
            "path": reverse("dcim:location_migrate_data_to_contact", kwargs={"pk": location.pk}),
            "data": post_data(form_data),
        }
        # Assert permission checks are triggered
        self.assertHttpStatus(self.client.post(**request), 200)
        self.add_permissions("extras.add_contactassociation")
        self.assertHttpStatus(self.client.post(**request), 302)
        # assert ContactAssociation is created correctly
        created_contact_association = ContactAssociation.objects.order_by("created").last()
        self.assertEqual(created_contact_association.associated_object_id, location.pk)
        self.assertEqual(created_contact_association.contact.pk, similar_contact.pk)
        self.assertEqual(created_contact_association.role.pk, role)
        self.assertEqual(created_contact_association.status.pk, status)

        # assert location data is cleared out
        location.refresh_from_db()
        self.assertEqual(location.contact_name, "")
        self.assertEqual(location.contact_phone, "")
        self.assertEqual(location.contact_email, "")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_migrate_location_data_from_location_new_contact(self):
        self.add_permissions("dcim.change_location")
        location = Location.objects.first()
        location.contact_name = "Should be unique Contact Name"
        location.contact_phone = "123123123"
        location.contact_email = "helloword@example.com"
        location.physical_address = "418 Brown Locks Barrettchester, NM 85792"
        location.shipping_address = "53 blue Locks manchester, NY 12124"
        role = self.contact_roles.first().pk
        status = self.contact_statuses.first().pk
        form_data = {
            "action": LocationDataToContactActionChoices.CREATE_AND_ASSIGN_NEW_CONTACT,
            "name": "Should be unique Contact Name",
            "phone": "123123123",
            "email": "helloword@example.com",
            "role": role,
            "status": status,
        }
        request = {
            "path": reverse("dcim:location_migrate_data_to_contact", kwargs={"pk": location.pk}),
            "data": post_data(form_data),
        }
        # Assert permission checks are triggered
        self.assertHttpStatus(self.client.post(**request), 200)
        self.add_permissions("extras.add_contactassociation")
        self.add_permissions("extras.add_contact")
        self.assertHttpStatus(self.client.post(**request), 302)
        # assert a new contact is created successfully
        contact = Contact.objects.get(name="Should be unique Contact Name")
        self.assertEqual(contact.name, form_data["name"])
        self.assertEqual(contact.phone, form_data["phone"])
        self.assertEqual(contact.email, form_data["email"])
        # assert ContactAssociation is created correctly
        created_contact_association = ContactAssociation.objects.order_by("created").last()
        self.assertEqual(created_contact_association.associated_object_id, location.pk)
        self.assertEqual(created_contact_association.contact.pk, contact.pk)
        self.assertEqual(created_contact_association.role.pk, role)
        self.assertEqual(created_contact_association.status.pk, status)

        # assert location data is cleared out
        location.refresh_from_db()
        self.assertEqual(location.contact_name, "")
        self.assertEqual(location.contact_phone, "")
        self.assertEqual(location.contact_email, "")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_migrate_location_data_from_location_new_team(self):
        self.add_permissions("dcim.change_location")
        location = Location.objects.first()
        location.contact_name = "Should be unique Team Name"
        location.contact_phone = "123123123"
        location.contact_email = "helloword@example.com"
        location.physical_address = "418 Brown Locks Barrettchester, NM 85792"
        location.shipping_address = "53 blue Locks manchester, NY 12124"
        role = self.contact_roles.first().pk
        status = self.contact_statuses.first().pk
        form_data = {
            "action": LocationDataToContactActionChoices.CREATE_AND_ASSIGN_NEW_TEAM,
            "name": "Should be unique Team Name",
            "phone": "123123123",
            "email": "helloword@example.com",
            "role": role,
            "status": status,
        }
        request = {
            "path": reverse("dcim:location_migrate_data_to_contact", kwargs={"pk": location.pk}),
            "data": post_data(form_data),
        }
        # Assert permission checks are triggered
        self.assertHttpStatus(self.client.post(**request), 200)
        self.add_permissions("extras.add_contactassociation")
        self.add_permissions("extras.add_team")
        self.assertHttpStatus(self.client.post(**request), 302)
        # assert a new team is created successfully
        team = Team.objects.get(name="Should be unique Team Name")
        self.assertEqual(team.name, form_data["name"])
        self.assertEqual(team.phone, form_data["phone"])
        self.assertEqual(team.email, form_data["email"])
        # assert ContactAssociation is created correctly
        created_contact_association = ContactAssociation.objects.order_by("created").last()
        self.assertEqual(created_contact_association.associated_object_id, location.pk)
        self.assertEqual(created_contact_association.team.pk, team.pk)
        self.assertEqual(created_contact_association.role.pk, role)
        self.assertEqual(created_contact_association.status.pk, status)

        # assert location data is cleared out
        location.refresh_from_db()
        self.assertEqual(location.contact_name, "")
        self.assertEqual(location.contact_phone, "")
        self.assertEqual(location.contact_email, "")


class RackGroupTestCase(ViewTestCases.OrganizationalObjectViewTestCase, ViewTestCases.BulkEditObjectsViewTestCase):
    model = RackGroup
    sort_on_field = "name"

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        rack_groups = (
            RackGroup.objects.create(name="Rack Group 1", location=location),
            RackGroup.objects.create(name="Rack Group 2", location=location),
            RackGroup.objects.create(name="Rack Group 3", location=location),
            RackGroup.objects.create(name="Rack Group 8", location=location),
        )
        RackGroup.objects.create(name="Rack Group Child 1", location=location, parent=rack_groups[0])
        RackGroup.objects.create(name="Rack Group Child 2", location=location, parent=rack_groups[0])

        cls.form_data = {
            "name": "Rack Group X",
            "location": location.pk,
            "description": "A new rack group",
        }
        cls.bulk_edit_data = {
            "description": "Updated description",
            "location": location.pk,
        }


class RackReservationTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = RackReservation

    @classmethod
    def setUpTestData(cls):
        user2 = User.objects.create_user(username="testuser2")
        user3 = User.objects.create_user(username="testuser3")

        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        rack_group = RackGroup.objects.create(name="Rack Group 1", location=location)

        rack_status = Status.objects.get_for_model(Rack).first()
        rack = Rack.objects.create(name="Rack 1", location=location, rack_group=rack_group, status=rack_status)

        RackReservation.objects.create(rack=rack, user=user2, units=[1, 2, 3], description="Reservation 1")
        RackReservation.objects.create(rack=rack, user=user2, units=[4, 5, 6], description="Reservation 2")
        RackReservation.objects.create(rack=rack, user=user2, units=[7, 8, 9], description="Reservation 3")

        cls.form_data = {
            "rack": rack.pk,
            "units": "10,11,12",
            "user": user3.pk,
            "tenant": None,
            "description": "Rack reservation",
            "tags": [t.pk for t in Tag.objects.get_for_model(RackReservation)],
        }

        cls.bulk_edit_data = {
            "user": user3.pk,
            "tenant": None,
            "description": "New description",
        }


class RackTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Rack

    @classmethod
    def setUpTestData(cls):
        cls.locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]

        powerpanels = (
            PowerPanel.objects.create(location=cls.locations[0], name="Power Panel 1"),
            PowerPanel.objects.create(location=cls.locations[0], name="Power Panel 2"),
        )

        # Assign power panels generated to the class object for use later.
        cls.powerpanels = powerpanels
        rackgroups = (
            RackGroup.objects.create(name="Rack Group 1", location=cls.locations[0]),
            RackGroup.objects.create(name="Rack Group 2", location=cls.locations[1]),
        )

        rackroles = Role.objects.get_for_model(Rack)[:2]

        statuses = Status.objects.get_for_model(Rack)
        cls.status = statuses[0]

        cable_statuses = Status.objects.get_for_model(Cable)
        cls.cable_connected = cable_statuses.get(name="Connected")

        cls.custom_fields = (
            CustomField.objects.create(
                type=CustomFieldTypeChoices.TYPE_MULTISELECT,
                label="Rack Colors",
                default=[],
            ),
        )

        CustomFieldChoice.objects.create(custom_field=cls.custom_fields[0], value="red")
        CustomFieldChoice.objects.create(custom_field=cls.custom_fields[0], value="green")
        CustomFieldChoice.objects.create(custom_field=cls.custom_fields[0], value="blue")
        for custom_field in cls.custom_fields:
            custom_field.content_types.set([ContentType.objects.get_for_model(Rack)])

        racks = (
            Rack.objects.create(
                name="Rack 1",
                location=cls.locations[0],
                status=cls.status,
                _custom_field_data={"rack_colors": ["red"]},
            ),
            Rack.objects.create(
                name="Rack 2",
                location=cls.locations[0],
                status=cls.status,
                _custom_field_data={"rack_colors": ["green"]},
            ),
            Rack.objects.create(
                name="Rack 3",
                location=cls.locations[0],
                status=cls.status,
                _custom_field_data={"rack_colors": ["blue"]},
            ),
        )

        # Create a class racks variable
        cls.racks = racks

        cls.relationships = (
            Relationship(
                label="Backup Locations",
                key="backup_locations",
                type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
                source_type=ContentType.objects.get_for_model(Rack),
                source_label="Backup location(s)",
                destination_type=ContentType.objects.get_for_model(Location),
                destination_label="Racks using this location as a backup",
            ),
        )
        for relationship in cls.relationships:
            relationship.validated_save()

        for rack in racks:
            RelationshipAssociation(
                relationship=cls.relationships[0],
                source=rack,
                destination=cls.locations[1],
            ).validated_save()

        cls.form_data = {
            "name": "Rack X",
            "facility_id": "Facility X",
            "location": cls.locations[1].pk,
            "rack_group": rackgroups[1].pk,
            "tenant": None,
            "status": statuses[2].pk,
            "role": rackroles[1].pk,
            "serial": "VMWARE-XX XX XX XX XX XX XX XX-XX XX XX XX XX XX XX XX",
            "asset_tag": "ABCDEF",
            "type": RackTypeChoices.TYPE_CABINET,
            "width": RackWidthChoices.WIDTH_19IN,
            "u_height": 48,
            "desc_units": False,
            "outer_width": 500,
            "outer_depth": 500,
            "outer_unit": RackDimensionUnitChoices.UNIT_MILLIMETER,
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(Rack)],
            "cf_rack-colors": ["red", "green", "blue"],
            "cr_backup-location__destination": [cls.locations[0].pk],
        }

        cls.bulk_edit_data = {
            "location": cls.locations[1].pk,
            "rack_group": rackgroups[1].pk,
            "tenant": None,
            "status": statuses[3].pk,
            "role": rackroles[1].pk,
            "serial": "654321-XX XX XX XX XX XX XX XX-XX XX XX XX XX XX XX XX",
            "type": RackTypeChoices.TYPE_4POST,
            "width": RackWidthChoices.WIDTH_23IN,
            "u_height": 49,
            "desc_units": True,
            "outer_width": 30,
            "outer_depth": 30,
            "outer_unit": RackDimensionUnitChoices.UNIT_INCH,
            "comments": "New comments",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_list_rack_elevations(self):
        """
        Test viewing the list of rack elevations.
        """
        response = self.client.get(reverse("dcim:rack_elevation_list"))
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_powerports(self):
        # Create Devices
        manufacturer = Manufacturer.objects.first()

        device_types = (DeviceType.objects.create(model="Device Type 1", manufacturer=manufacturer),)

        device_roles = Role.objects.get_for_model(Device)[:1]

        platforms = Platform.objects.all()[:1]

        devices = (
            Device.objects.create(
                name="Power Panel 1",
                location=self.locations[0],
                rack=self.racks[0],
                device_type=device_types[0],
                role=device_roles[0],
                platform=platforms[0],
                status=self.status,
            ),
            Device.objects.create(
                name="Dev 1",
                location=self.locations[0],
                rack=self.racks[0],
                device_type=device_types[0],
                role=device_roles[0],
                platform=platforms[0],
                status=self.status,
            ),
        )

        # Create Power Port for device
        powerport1 = PowerPort.objects.create(device=devices[0], name="Power Port 11")
        pf_status = Status.objects.get_for_model(PowerFeed).first()
        powerfeed1 = PowerFeed.objects.create(
            power_panel=self.powerpanels[0],
            name="Power Feed 11",
            phase="single-phase",
            voltage=240,
            amperage=20,
            rack=self.racks[0],
            status=pf_status,
        )
        powerfeed2 = PowerFeed.objects.create(
            power_panel=self.powerpanels[0],
            name="Power Feed 12",
            phase="single-phase",
            voltage=240,
            amperage=20,
            rack=self.racks[0],
            status=pf_status,
        )

        # Create power outlet to the power port
        poweroutlet1 = PowerOutlet.objects.create(device=devices[0], name="Power Outlet 11", power_port=powerport1)

        # connect power port to power feed (single-phase)
        cable1 = Cable(
            termination_a=powerfeed1,
            termination_b=powerport1,
            status=self.cable_connected,
        )
        cable1.save()

        # Create power port for 2nd device
        powerport2 = PowerPort.objects.create(device=devices[1], name="Power Port 12", allocated_draw=1200)

        # Connect power port to power outlet (dev1)
        cable2 = Cable(
            termination_a=powerport2,
            termination_b=poweroutlet1,
            status=self.cable_connected,
        )
        cable2.save()

        # Create another power port for 2nd device and directly connect to the second PowerFeed.
        powerport3 = PowerPort.objects.create(device=devices[1], name="Power Port 13", allocated_draw=2400)
        cable3 = Cable(
            termination_a=powerfeed2,
            termination_b=powerport3,
            status=self.cable_connected,
        )
        cable3.save()

        # Test the view
        response = self.client.get(reverse("dcim:rack", args=[self.racks[0].pk]))
        self.assertHttpStatus(response, 200)

        # Validate Power Utilization for PowerFeed 11 is displaying correctly on Rack View.
        power_feed_11_html = """
        <td><div title="Used: 1263&#13;Count: 3840" class="progress text-center">
            <div class="progress-bar progress-bar-success"
                role="progressbar" aria-valuenow="32" aria-valuemin="0" aria-valuemax="100" style="width: 32%">
                32%
            </div>
        </div></td>
        """
        self.assertContains(response, power_feed_11_html, html=True)
        # Validate Power Utilization for PowerFeed12 is displaying correctly on Rack View.
        power_feed_12_html = """
        <td><div title="Used: 2526&#13;Count: 3840" class="progress text-center">
            <div class="progress-bar progress-bar-success"
                role="progressbar" aria-valuenow="65" aria-valuemin="0" aria-valuemax="100" style="width: 65%">
                65%
            </div>
        </div></td>
        """
        self.assertContains(response, power_feed_12_html, html=True)
        # Validate Rack Power Utilization for Combined powerfeeds is displaying correctly on the Rack View
        total_utilization_html = """
        <td><div title="Used: 3789&#13;Count: 7680" class="progress text-center">
            <div class="progress-bar progress-bar-success"
                role="progressbar" aria-valuenow="49" aria-valuemin="0" aria-valuemax="100" style="width: 49%">
                49%
            </div>
        </div></td>
        """
        self.assertContains(response, total_utilization_html, html=True)


class DeviceFamilyTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = DeviceFamily

    @classmethod
    def setUpTestData(cls):
        cls.form_data = {
            "name": "New Device Family",
            "description": "A new device family",
            "tags": [t.pk for t in Tag.objects.get_for_model(DeviceFamily)],
        }
        cls.bulk_edit_data = {
            "description": "A new device family",
        }
        DeviceFamily.objects.create(name="Deletable Device Family 1")
        DeviceFamily.objects.create(name="Deletable Device Family 2", description="Delete this one")
        DeviceFamily.objects.create(name="Deletable Device Family 3")


class ManufacturerTestCase(ViewTestCases.OrganizationalObjectViewTestCase, ViewTestCases.BulkEditObjectsViewTestCase):
    model = Manufacturer

    @classmethod
    def setUpTestData(cls):
        cls.form_data = {
            "name": "Manufacturer X",
            "description": "A new manufacturer",
        }
        cls.bulk_edit_data = {
            "description": "Updated manufacturer description",
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


# TODO: Change base class to PrimaryObjectViewTestCase
# Blocked by absence of bulk import view for DeviceTypes
class DeviceTypeTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = DeviceType

    @classmethod
    def setUpTestData(cls):
        Controller.objects.filter(controller_device__isnull=False).delete()
        Device.objects.all().delete()
        manufacturers = Manufacturer.objects.all()[:2]

        DeviceType.objects.create(model="Test Device Type 1", manufacturer=manufacturers[0])
        DeviceType.objects.create(model="Test Device Type 2", manufacturer=manufacturers[0])
        DeviceType.objects.create(model="Test Device Type 3", manufacturer=manufacturers[0])
        DeviceType.objects.create(model="Test Device Type 4", manufacturer=manufacturers[1])

        cls.form_data = {
            "manufacturer": manufacturers[1].pk,
            "device_family": None,
            "model": "Device Type X",
            "part_number": "123ABC",
            "u_height": 2,
            "is_full_depth": True,
            "subdevice_role": "",  # CharField
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(DeviceType)],
        }

        cls.bulk_edit_data = {
            "u_height": 0,
            "is_full_depth": False,
            "comments": "changed comment",
        }

    def test_list_has_correct_links(self):
        """Assert that the DeviceType list view has import/export buttons for both CSV and YAML/JSON formats."""
        self.add_permissions("dcim.add_devicetype", "dcim.view_devicetype")
        response = self.client.get(reverse("dcim:devicetype_list"))
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))

        yaml_import_url = reverse("dcim:devicetype_import")
        csv_import_url = job_import_url(ContentType.objects.get_for_model(DeviceType))
        # Dropdown provides both YAML/JSON and CSV import as options
        self.assertInHTML(
            f'<a href="{yaml_import_url}"><span class="mdi mdi-database-import text-muted" aria-hidden="true"></span> Import from JSON/YAML (single record)</a>',
            content,
        )
        self.assertInHTML(
            f'<a href="{csv_import_url}"><span class="mdi mdi-database-import text-muted" aria-hidden="true"></span> Import from CSV (multiple records)</a>',
            content,
        )

        export_url = job_export_url()
        # Export is a little trickier to check since it's done as a form submission rather than an <a> element.
        self.assertIn(f'<form action="{export_url}" method="post">', content)
        self.assertInHTML(
            f'<input type="hidden" name="content_type" value="{ContentType.objects.get_for_model(self.model).pk}">',
            content,
        )
        self.assertInHTML('<input type="hidden" name="export_format" value="yaml">', content)
        self.assertInHTML(
            '<button type="submit"><span class="mdi mdi-database-export text-muted" aria-hidden="true"></span> Export as YAML</button>',
            content,
        )
        self.assertInHTML(
            '<button type="submit"><span class="mdi mdi-database-export text-muted" aria-hidden="true"></span> Export as CSV</button>',
            content,
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_import_objects(self):
        """
        Custom import test for YAML-based imports (versus CSV)
        """
        # Note use of "power-outlets.power_port" (not "power_port_template") and "front-ports.rear_port"
        # (not "rear_port_template"). Note also inclusion of "slug" even though we removed DeviceType.slug in 2.0.
        # This is intentional as we are testing backwards compatibility with the netbox/devicetype-library repository.
        manufacturer = Manufacturer.objects.first()
        IMPORT_DATA = f"""
manufacturer: {manufacturer.name}
model: TEST-1000
slug: test-1000
u_height: 2
subdevice_role: parent
comments: test comment
console-ports:
  - name: Console Port 1
    type: de-9
  - name: Console Port 2
    type: de-9
  - name: Console Port 3
    type: de-9
console-server-ports:
  - name: Console Server Port 1
    type: rj-45
  - name: Console Server Port 2
    type: rj-45
  - name: Console Server Port 3
    type: rj-45
power-ports:
  - name: Power Port 1
    type: iec-60320-c14
  - name: Power Port 2
    type: iec-60320-c14
  - name: Power Port 3
    type: iec-60320-c14
power-outlets:
  - name: Power Outlet 1
    type: iec-60320-c13
    power_port: Power Port 1
    feed_leg: A
  - name: Power Outlet 2
    type: iec-60320-c13
    power_port: Power Port 1
    feed_leg: A
  - name: Power Outlet 3
    type: iec-60320-c13
    power_port: Power Port 1
    feed_leg: A
interfaces:
  - name: Interface 1
    type: 1000base-t
    mgmt_only: true
  - name: Interface 2
    type: 1000base-t
  - name: Interface 3
    type: 1000base-t
rear-ports:
  - name: Rear Port 1
    type: 8p8c
  - name: Rear Port 2
    type: 8p8c
  - name: Rear Port 3
    type: 8p8c
front-ports:
  - name: Front Port 1
    type: 8p8c
    rear_port: Rear Port 1
  - name: Front Port 2
    type: 8p8c
    rear_port: Rear Port 2
  - name: Front Port 3
    type: 8p8c
    rear_port: Rear Port 3
device-bays:
  - name: Device Bay 1
  - name: Device Bay 2
  - name: Device Bay 3
module-bays:
  - name: Module Bay 1
    position: 1
  - name: Module Bay 2
    position: 2
  - name: Module Bay 3
    position: 3
"""

        # Add all required permissions to the test user
        self.add_permissions(
            "dcim.view_devicetype",
            "dcim.add_devicetype",
            "dcim.add_consoleporttemplate",
            "dcim.add_consoleserverporttemplate",
            "dcim.add_powerporttemplate",
            "dcim.add_poweroutlettemplate",
            "dcim.add_interfacetemplate",
            "dcim.add_frontporttemplate",
            "dcim.add_rearporttemplate",
            "dcim.add_devicebaytemplate",
            "dcim.add_modulebaytemplate",
        )

        form_data = {"data": IMPORT_DATA, "format": "yaml"}
        response = self.client.post(reverse("dcim:devicetype_import"), data=form_data, follow=True)
        self.assertHttpStatus(response, 200)
        dt = DeviceType.objects.get(model="TEST-1000")
        self.assertEqual(dt.comments, "test comment")

        # Verify all of the components were created
        self.assertEqual(dt.console_port_templates.count(), 3)
        cp1 = dt.console_port_templates.first()
        self.assertEqual(cp1.name, "Console Port 1")
        self.assertEqual(cp1.type, ConsolePortTypeChoices.TYPE_DE9)

        self.assertEqual(dt.console_server_port_templates.count(), 3)
        csp1 = dt.console_server_port_templates.first()
        self.assertEqual(csp1.name, "Console Server Port 1")
        self.assertEqual(csp1.type, ConsolePortTypeChoices.TYPE_RJ45)

        self.assertEqual(dt.power_port_templates.count(), 3)
        pp1 = dt.power_port_templates.first()
        self.assertEqual(pp1.name, "Power Port 1")
        self.assertEqual(pp1.type, PowerPortTypeChoices.TYPE_IEC_C14)

        self.assertEqual(dt.power_outlet_templates.count(), 3)
        po1 = dt.power_outlet_templates.first()
        self.assertEqual(po1.name, "Power Outlet 1")
        self.assertEqual(po1.type, PowerOutletTypeChoices.TYPE_IEC_C13)
        self.assertEqual(po1.power_port_template, pp1)
        self.assertEqual(po1.feed_leg, PowerOutletFeedLegChoices.FEED_LEG_A)

        self.assertEqual(dt.interface_templates.count(), 3)
        iface1 = dt.interface_templates.first()
        self.assertEqual(iface1.name, "Interface 1")
        self.assertEqual(iface1.type, InterfaceTypeChoices.TYPE_1GE_FIXED)
        self.assertTrue(iface1.mgmt_only)

        self.assertEqual(dt.rear_port_templates.count(), 3)
        rp1 = dt.rear_port_templates.first()
        self.assertEqual(rp1.name, "Rear Port 1")

        self.assertEqual(dt.front_port_templates.count(), 3)
        fp1 = dt.front_port_templates.first()
        self.assertEqual(fp1.name, "Front Port 1")
        self.assertEqual(fp1.rear_port_template, rp1)
        self.assertEqual(fp1.rear_port_position, 1)

        self.assertEqual(dt.device_bay_templates.count(), 3)
        db1 = dt.device_bay_templates.first()
        self.assertEqual(db1.name, "Device Bay 1")

        self.assertEqual(dt.module_bay_templates.count(), 3)
        mb1 = dt.module_bay_templates.first()
        self.assertEqual(mb1.name, "Module Bay 1")

    def test_import_objects_unknown_type_enums(self):
        """
        YAML import of data with `type` values that we don't recognize should remap those to "other" rather than fail.
        """
        manufacturer = Manufacturer.objects.first()
        IMPORT_DATA = f"""
manufacturer: {manufacturer.name}
model: TEST-2000
u_height: 0
subdevice_role: parent
comments: "test comment"
console-ports:
  - name: Console Port Alpha-Beta
    type: alpha-beta
console-server-ports:
  - name: Console Server Port Pineapple
    type: pineapple
power-ports:
  - name: Power Port Fred
    type: frederick
power-outlets:
  - name: Power Outlet Rick
    type: frederick
    power_port_template: Power Port Fred
interfaces:
  - name: Interface North
    type: northern
rear-ports:
  - name: Rear Port Foosball
    type: foosball
front-ports:
  - name: Front Port Pickleball
    type: pickleball
    rear_port_template: Rear Port Foosball
device-bays:
  - name: Device Bay of Uncertain Type
    type: unknown  # should be ignored
  - name: Device Bay of Unspecified Type
module-bays:
  - name: Module Bay 1
    position: 1
  - name: Module Bay 2
    position: 2
  - name: Module Bay 3
    position: 3
"""
        # Add all required permissions to the test user
        self.add_permissions(
            "dcim.view_devicetype",
            "dcim.view_manufacturer",
            "dcim.add_devicetype",
            "dcim.add_consoleporttemplate",
            "dcim.add_consoleserverporttemplate",
            "dcim.add_powerporttemplate",
            "dcim.add_poweroutlettemplate",
            "dcim.add_interfacetemplate",
            "dcim.add_frontporttemplate",
            "dcim.add_rearporttemplate",
            "dcim.add_devicebaytemplate",
            "dcim.add_modulebaytemplate",
        )

        form_data = {"data": IMPORT_DATA, "format": "yaml"}
        response = self.client.post(reverse("dcim:devicetype_import"), data=form_data, follow=True)
        self.assertHttpStatus(response, 200)
        dt = DeviceType.objects.get(model="TEST-2000")
        self.assertEqual(dt.comments, "test comment")

        # Verify all of the components were created with appropriate "other" types
        self.assertEqual(dt.console_port_templates.count(), 1)
        cpt = ConsolePortTemplate.objects.filter(device_type=dt).first()
        self.assertEqual(cpt.name, "Console Port Alpha-Beta")
        self.assertEqual(cpt.type, ConsolePortTypeChoices.TYPE_OTHER)

        self.assertEqual(dt.console_server_port_templates.count(), 1)
        cspt = ConsoleServerPortTemplate.objects.filter(device_type=dt).first()
        self.assertEqual(cspt.name, "Console Server Port Pineapple")
        self.assertEqual(cspt.type, ConsolePortTypeChoices.TYPE_OTHER)

        self.assertEqual(dt.power_port_templates.count(), 1)
        ppt = PowerPortTemplate.objects.filter(device_type=dt).first()
        self.assertEqual(ppt.name, "Power Port Fred")
        self.assertEqual(ppt.type, PowerPortTypeChoices.TYPE_OTHER)

        self.assertEqual(dt.power_outlet_templates.count(), 1)
        pot = PowerOutletTemplate.objects.filter(device_type=dt).first()
        self.assertEqual(pot.name, "Power Outlet Rick")
        self.assertEqual(pot.type, PowerOutletTypeChoices.TYPE_OTHER)
        self.assertEqual(pot.power_port_template, ppt)

        self.assertEqual(dt.interface_templates.count(), 1)
        it = InterfaceTemplate.objects.filter(device_type=dt).first()
        self.assertEqual(it.name, "Interface North")
        self.assertEqual(it.type, InterfaceTypeChoices.TYPE_OTHER)

        self.assertEqual(dt.rear_port_templates.count(), 1)
        rpt = RearPortTemplate.objects.filter(device_type=dt).first()
        self.assertEqual(rpt.name, "Rear Port Foosball")
        self.assertEqual(rpt.type, PortTypeChoices.TYPE_OTHER)

        self.assertEqual(dt.front_port_templates.count(), 1)
        fpt = FrontPortTemplate.objects.filter(device_type=dt).first()
        self.assertEqual(fpt.name, "Front Port Pickleball")
        self.assertEqual(fpt.type, PortTypeChoices.TYPE_OTHER)

        self.assertEqual(dt.device_bay_templates.count(), 2)
        # DeviceBayTemplate doesn't have a type field.

        self.assertEqual(dt.module_bay_templates.count(), 3)
        # ModuleBayTemplate doesn't have a type field.
        mbt = ModuleBayTemplate.objects.filter(device_type=dt).first()
        self.assertEqual(mbt.position, "1")
        self.assertEqual(mbt.name, "Module Bay 1")

    def test_devicetype_export(self):
        url = reverse("dcim:devicetype_list")
        self.add_permissions("dcim.view_devicetype")

        response = self.client.get(f"{url}?export")
        self.assertEqual(response.status_code, 200)
        data = list(yaml.load_all(response.content, Loader=yaml.SafeLoader))
        device_types = DeviceType.objects.all()
        device_type = device_types.first()

        self.assertEqual(len(data), device_types.count())
        self.assertEqual(data[0]["manufacturer"], device_type.manufacturer.name)
        self.assertEqual(data[0]["model"], device_type.model)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_rack_height_bulk_edit_set_zero(self):
        """Test that rack height can be set to "0" in bulk_edit."""
        self.add_permissions("dcim.change_devicetype")
        url = self._get_url("bulk_edit")
        pk_list = list(self._get_queryset().values_list("pk", flat=True)[:3])

        data = {
            "u_height": 0,
            "pk": pk_list,
            "_apply": True,  # Form button
        }

        response = self.client.post(url, data)
        job_result = JobResult.objects.filter(name="Bulk Edit Objects").first()
        # Assert successfull redirect to Job Results; whcih means no form validation error was raised
        self.assertRedirects(
            response,
            reverse("extras:jobresult", args=[job_result.pk]),
            status_code=302,
            target_status_code=200,
        )
        self.assertHttpStatus(response, 302)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_rack_height_bulk_edit_invalid(self):
        """Test that a rack height cannot be set to an invalid value in bulk_edit."""
        self.add_permissions("dcim.change_devicetype")
        url = self._get_url("bulk_edit")
        pk_list = list(self._get_queryset().values_list("pk", flat=True)[:3])

        data = {
            "u_height": -1,  # Invalid rack height
            "pk": pk_list,
            "_apply": True,  # Form button
        }

        response = self.client.post(url, data)
        response_content = response.content.decode(response.charset)
        self.assertHttpStatus(response, 200)
        self.assertInHTML(
            '<strong class="panel-title">U height</strong>: <ul class="errorlist"><li>Ensure this value is greater than or equal to 0.</li></ul>',
            response_content,
        )


class ModuleTypeTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ModuleType

    @classmethod
    def setUpTestData(cls):
        manufacturers = Manufacturer.objects.all()[:2]
        Module.objects.all().delete()
        ModuleType.objects.all().delete()

        ModuleType.objects.create(
            model="Test Module Type 1",
            manufacturer=manufacturers[0],
            comments="test comment",
        )
        ModuleType.objects.create(
            model="Test Module Type 2",
            manufacturer=manufacturers[0],
        )
        ModuleType.objects.create(
            model="Test Module Type 3",
            manufacturer=manufacturers[0],
        )
        ModuleType.objects.create(
            model="Test Module Type 4",
            manufacturer=manufacturers[1],
        )

        cls.form_data = {
            "manufacturer": manufacturers[0].pk,
            "model": "Test Module Type X",
            "part_number": "123ABC",
            "tags": [t.pk for t in Tag.objects.get_for_model(ModuleType)],
            "comments": "test comment",
        }

        cls.bulk_edit_data = {
            "manufacturer": manufacturers[1].pk,
            "comments": "changed comment",
        }

    def test_list_has_correct_links(self):
        """Assert that the ModuleType list view has import/export buttons for both CSV and YAML/JSON formats."""
        self.add_permissions("dcim.add_moduletype", "dcim.view_moduletype")
        response = self.client.get(reverse("dcim:moduletype_list"))
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))

        yaml_import_url = reverse("dcim:moduletype_import")
        csv_import_url = job_import_url(ContentType.objects.get_for_model(ModuleType))
        # Dropdown provides both YAML/JSON and CSV import as options
        self.assertInHTML(
            f'<a href="{yaml_import_url}"><span class="mdi mdi-database-import text-muted" aria-hidden="true"></span> Import from JSON/YAML (single record)</a>',
            content,
        )
        self.assertInHTML(
            f'<a href="{csv_import_url}"><span class="mdi mdi-database-import text-muted" aria-hidden="true"></span> Import from CSV (multiple records)</a>',
            content,
        )

        export_url = job_export_url()
        # Export is a little trickier to check since it's done as a form submission rather than an <a> element.
        self.assertIn(f'<form action="{export_url}" method="post">', content)
        self.assertInHTML(
            f'<input type="hidden" name="content_type" value="{ContentType.objects.get_for_model(self.model).pk}">',
            content,
        )
        self.assertInHTML('<input type="hidden" name="export_format" value="yaml">', content)
        self.assertInHTML(
            '<button type="submit"><span class="mdi mdi-database-export text-muted" aria-hidden="true"></span> Export as YAML</button>',
            content,
        )
        self.assertInHTML(
            '<button type="submit"><span class="mdi mdi-database-export text-muted" aria-hidden="true"></span> Export as CSV</button>',
            content,
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_import_objects(self):
        """
        Custom import test for YAML-based imports (versus CSV)
        """
        # Note use of "power-outlets.power_port" (not "power_port_template") and "front-ports.rear_port"
        # (not "rear_port_template"). Note also inclusion of "slug" even though we removed DeviceType.slug in 2.0.
        # This is intentional as we are testing backwards compatibility with the netbox/devicetype-library repository.
        manufacturer = Manufacturer.objects.first()
        IMPORT_DATA = f"""
manufacturer: {manufacturer.name}
model: TEST-1000
slug: test-1000
console-ports:
  - name: Console Port 1
    type: de-9
  - name: Console Port 2
    type: de-9
  - name: Console Port 3
    type: de-9
console-server-ports:
  - name: Console Server Port 1
    type: rj-45
  - name: Console Server Port 2
    type: rj-45
  - name: Console Server Port 3
    type: rj-45
power-ports:
  - name: Power Port 1
    type: iec-60320-c14
  - name: Power Port 2
    type: iec-60320-c14
  - name: Power Port 3
    type: iec-60320-c14
power-outlets:
  - name: Power Outlet 1
    type: iec-60320-c13
    power_port: Power Port 1
    feed_leg: A
  - name: Power Outlet 2
    type: iec-60320-c13
    power_port: Power Port 1
    feed_leg: A
  - name: Power Outlet 3
    type: iec-60320-c13
    power_port: Power Port 1
    feed_leg: A
interfaces:
  - name: Interface 1
    type: 1000base-t
    mgmt_only: true
  - name: Interface 2
    type: 1000base-t
  - name: Interface 3
    type: 1000base-t
rear-ports:
  - name: Rear Port 1
    type: 8p8c
  - name: Rear Port 2
    type: 8p8c
  - name: Rear Port 3
    type: 8p8c
front-ports:
  - name: Front Port 1
    type: 8p8c
    rear_port: Rear Port 1
  - name: Front Port 2
    type: 8p8c
    rear_port: Rear Port 2
  - name: Front Port 3
    type: 8p8c
    rear_port: Rear Port 3
module-bays:
  - name: Module Bay 1
    position: 1
  - name: Module Bay 2
    position: 2
  - name: Module Bay 3
    position: 3
"""

        # Add all required permissions to the test user
        self.add_permissions(
            "dcim.view_moduletype",
            "dcim.add_moduletype",
            "dcim.add_consoleporttemplate",
            "dcim.add_consoleserverporttemplate",
            "dcim.add_powerporttemplate",
            "dcim.add_poweroutlettemplate",
            "dcim.add_interfacetemplate",
            "dcim.add_frontporttemplate",
            "dcim.add_rearporttemplate",
            "dcim.add_modulebaytemplate",
        )

        form_data = {"data": IMPORT_DATA, "format": "yaml"}
        response = self.client.post(reverse("dcim:moduletype_import"), data=form_data, follow=True)
        self.assertHttpStatus(response, 200)
        mt = ModuleType.objects.get(model="TEST-1000")

        # Verify all of the components were created
        self.assertEqual(mt.console_port_templates.count(), 3)
        cp1 = mt.console_port_templates.first()
        self.assertEqual(cp1.name, "Console Port 1")
        self.assertEqual(cp1.type, ConsolePortTypeChoices.TYPE_DE9)

        self.assertEqual(mt.console_server_port_templates.count(), 3)
        csp1 = mt.console_server_port_templates.first()
        self.assertEqual(csp1.name, "Console Server Port 1")
        self.assertEqual(csp1.type, ConsolePortTypeChoices.TYPE_RJ45)

        self.assertEqual(mt.power_port_templates.count(), 3)
        pp1 = mt.power_port_templates.first()
        self.assertEqual(pp1.name, "Power Port 1")
        self.assertEqual(pp1.type, PowerPortTypeChoices.TYPE_IEC_C14)

        self.assertEqual(mt.power_outlet_templates.count(), 3)
        po1 = mt.power_outlet_templates.first()
        self.assertEqual(po1.name, "Power Outlet 1")
        self.assertEqual(po1.type, PowerOutletTypeChoices.TYPE_IEC_C13)
        self.assertEqual(po1.power_port_template, pp1)
        self.assertEqual(po1.feed_leg, PowerOutletFeedLegChoices.FEED_LEG_A)

        self.assertEqual(mt.interface_templates.count(), 3)
        iface1 = mt.interface_templates.first()
        self.assertEqual(iface1.name, "Interface 1")
        self.assertEqual(iface1.type, InterfaceTypeChoices.TYPE_1GE_FIXED)
        self.assertTrue(iface1.mgmt_only)

        self.assertEqual(mt.rear_port_templates.count(), 3)
        rp1 = mt.rear_port_templates.first()
        self.assertEqual(rp1.name, "Rear Port 1")

        self.assertEqual(mt.front_port_templates.count(), 3)
        fp1 = mt.front_port_templates.first()
        self.assertEqual(fp1.name, "Front Port 1")
        self.assertEqual(fp1.rear_port_template, rp1)
        self.assertEqual(fp1.rear_port_position, 1)

        self.assertEqual(mt.module_bay_templates.count(), 3)
        mb1 = mt.module_bay_templates.first()
        self.assertEqual(mb1.name, "Module Bay 1")
        self.assertEqual(mb1.position, "1")

    def test_import_objects_unknown_type_enums(self):
        """
        YAML import of data with `type` values that we don't recognize should remap those to "other" rather than fail.
        """
        manufacturer = Manufacturer.objects.first()
        IMPORT_DATA = f"""
manufacturer: {manufacturer.name}
model: TEST-2000
console-ports:
  - name: Console Port Alpha-Beta
    type: alpha-beta
console-server-ports:
  - name: Console Server Port Pineapple
    type: pineapple
power-ports:
  - name: Power Port Fred
    type: frederick
power-outlets:
  - name: Power Outlet Rick
    type: frederick
    power_port_template: Power Port Fred
interfaces:
  - name: Interface North
    type: northern
rear-ports:
  - name: Rear Port Foosball
    type: foosball
front-ports:
  - name: Front Port Pickleball
    type: pickleball
    rear_port_template: Rear Port Foosball
module-bays:
  - name: Module Bay 1
    position: 1
  - name: Module Bay 2
    position: 2
  - name: Module Bay 3
    position: 3
"""
        # Add all required permissions to the test user
        self.add_permissions(
            "dcim.view_moduletype",
            "dcim.view_manufacturer",
            "dcim.add_moduletype",
            "dcim.add_consoleporttemplate",
            "dcim.add_consoleserverporttemplate",
            "dcim.add_powerporttemplate",
            "dcim.add_poweroutlettemplate",
            "dcim.add_interfacetemplate",
            "dcim.add_frontporttemplate",
            "dcim.add_rearporttemplate",
            "dcim.add_modulebaytemplate",
        )

        form_data = {"data": IMPORT_DATA, "format": "yaml"}
        response = self.client.post(reverse("dcim:moduletype_import"), data=form_data, follow=True)
        self.assertHttpStatus(response, 200)
        mt = ModuleType.objects.get(model="TEST-2000")

        # Verify all of the components were created with appropriate "other" types
        self.assertEqual(mt.console_port_templates.count(), 1)
        cpt = ConsolePortTemplate.objects.filter(module_type=mt).first()
        self.assertEqual(cpt.name, "Console Port Alpha-Beta")
        self.assertEqual(cpt.type, ConsolePortTypeChoices.TYPE_OTHER)

        self.assertEqual(mt.console_server_port_templates.count(), 1)
        cspt = ConsoleServerPortTemplate.objects.filter(module_type=mt).first()
        self.assertEqual(cspt.name, "Console Server Port Pineapple")
        self.assertEqual(cspt.type, ConsolePortTypeChoices.TYPE_OTHER)

        self.assertEqual(mt.power_port_templates.count(), 1)
        ppt = PowerPortTemplate.objects.filter(module_type=mt).first()
        self.assertEqual(ppt.name, "Power Port Fred")
        self.assertEqual(ppt.type, PowerPortTypeChoices.TYPE_OTHER)

        self.assertEqual(mt.power_outlet_templates.count(), 1)
        pot = PowerOutletTemplate.objects.filter(module_type=mt).first()
        self.assertEqual(pot.name, "Power Outlet Rick")
        self.assertEqual(pot.type, PowerOutletTypeChoices.TYPE_OTHER)
        self.assertEqual(pot.power_port_template, ppt)

        self.assertEqual(mt.interface_templates.count(), 1)
        it = InterfaceTemplate.objects.filter(module_type=mt).first()
        self.assertEqual(it.name, "Interface North")
        self.assertEqual(it.type, InterfaceTypeChoices.TYPE_OTHER)

        self.assertEqual(mt.rear_port_templates.count(), 1)
        rpt = RearPortTemplate.objects.filter(module_type=mt).first()
        self.assertEqual(rpt.name, "Rear Port Foosball")
        self.assertEqual(rpt.type, PortTypeChoices.TYPE_OTHER)

        self.assertEqual(mt.front_port_templates.count(), 1)
        fpt = FrontPortTemplate.objects.filter(module_type=mt).first()
        self.assertEqual(fpt.name, "Front Port Pickleball")
        self.assertEqual(fpt.type, PortTypeChoices.TYPE_OTHER)

        self.assertEqual(mt.module_bay_templates.count(), 3)
        # ModuleBayTemplate doesn't have a type field.
        mbt = ModuleBayTemplate.objects.filter(module_type=mt).first()
        self.assertEqual(mbt.position, "1")
        self.assertEqual(mbt.name, "Module Bay 1")

    def test_moduletype_export(self):
        url = reverse("dcim:moduletype_list")
        self.add_permissions("dcim.view_moduletype")

        response = self.client.get(f"{url}?export")
        self.assertEqual(response.status_code, 200)
        data = list(yaml.load_all(response.content, Loader=yaml.SafeLoader))
        module_types = ModuleType.objects.all()
        module_type = module_types.first()

        self.assertEqual(len(data), module_types.count())
        self.assertEqual(data[0]["manufacturer"], module_type.manufacturer.name)
        self.assertEqual(data[0]["model"], module_type.model)


#
# DeviceType components
#


class ConsolePortTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = ConsolePortTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        devicetypes = (
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1"),
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 2"),
        )

        ConsolePortTemplate.objects.create(device_type=devicetypes[0], name="Console Port Template 1")
        ConsolePortTemplate.objects.create(device_type=devicetypes[0], name="Console Port Template 2")
        ConsolePortTemplate.objects.create(device_type=devicetypes[0], name="Console Port Template 3")

        cls.form_data = {
            "device_type": devicetypes[1].pk,
            "name": "Console Port Template X",
            "type": ConsolePortTypeChoices.TYPE_RJ45,
        }

        cls.bulk_create_data = {
            "device_type": devicetypes[1].pk,
            "name_pattern": "Console Port Template [4-6]",
            "description": "View Test Bulk Create Console Ports",
            "type": ConsolePortTypeChoices.TYPE_RJ45,
        }

        cls.bulk_edit_data = {
            "type": ConsolePortTypeChoices.TYPE_RJ45,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": getattr(getattr(test_instance, "device_type", None), "pk", None),
            "module_type": getattr(getattr(test_instance, "module_type", None), "pk", None),
            "label": "new test label",
            "description": "new test description",
        }


class ConsoleServerPortTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = ConsoleServerPortTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        devicetypes = (
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1"),
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 2"),
        )

        ConsoleServerPortTemplate.objects.create(device_type=devicetypes[0], name="Console Server Port Template 1")
        ConsoleServerPortTemplate.objects.create(device_type=devicetypes[0], name="Console Server Port Template 2")
        ConsoleServerPortTemplate.objects.create(device_type=devicetypes[0], name="Console Server Port Template 3")

        cls.form_data = {
            "device_type": devicetypes[1].pk,
            "name": "Console Server Port Template X",
            "type": ConsolePortTypeChoices.TYPE_RJ45,
        }

        cls.bulk_create_data = {
            "device_type": devicetypes[1].pk,
            "name_pattern": "Console Server Port Template [4-6]",
            "description": "View Test Bulk Create Console Server Ports",
            "type": ConsolePortTypeChoices.TYPE_RJ45,
        }

        cls.bulk_edit_data = {
            "type": ConsolePortTypeChoices.TYPE_RJ45,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": getattr(getattr(test_instance, "device_type", None), "pk", None),
            "module_type": getattr(getattr(test_instance, "module_type", None), "pk", None),
            "label": "new test label",
            "description": "new test description",
        }


class PowerPortTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = PowerPortTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        devicetypes = (
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1"),
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 2"),
        )

        PowerPortTemplate.objects.create(device_type=devicetypes[0], name="Power Port Template 1")
        PowerPortTemplate.objects.create(device_type=devicetypes[0], name="Power Port Template 2")
        PowerPortTemplate.objects.create(device_type=devicetypes[0], name="Power Port Template 3")

        cls.form_data = {
            "device_type": devicetypes[1].pk,
            "name": "Power Port Template X",
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
            "power_factor": Decimal("0.95"),
        }

        cls.bulk_create_data = {
            "device_type": devicetypes[1].pk,
            "name_pattern": "Power Port Template [4-6]",
            "description": "View Test Bulk Create Power Ports",
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
            "power_factor": Decimal("0.95"),
        }

        cls.bulk_edit_data = {
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": getattr(getattr(test_instance, "device_type", None), "pk", None),
            "module_type": getattr(getattr(test_instance, "module_type", None), "pk", None),
            "power_factor": Decimal("0.95"),
            "label": "new test label",
            "description": "new test description",
        }


class PowerOutletTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = PowerOutletTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")

        PowerOutletTemplate.objects.create(device_type=devicetype, name="Power Outlet Template 1")
        PowerOutletTemplate.objects.create(device_type=devicetype, name="Power Outlet Template 2")
        PowerOutletTemplate.objects.create(device_type=devicetype, name="Power Outlet Template 3")

        powerports = (PowerPortTemplate.objects.create(device_type=devicetype, name="Power Port Template 1"),)

        cls.form_data = {
            "device_type": devicetype.pk,
            "name": "Power Outlet Template X",
            "type": PowerOutletTypeChoices.TYPE_IEC_C13,
            "power_port_template": powerports[0].pk,
            "feed_leg": PowerOutletFeedLegChoices.FEED_LEG_B,
        }

        cls.bulk_create_data = {
            "device_type": devicetype.pk,
            "name_pattern": "Power Outlet Template [4-6]",
            "description": "View Test Bulk Create Power Outlets",
            "type": PowerOutletTypeChoices.TYPE_IEC_C13,
            "power_port_template": powerports[0].pk,
            "feed_leg": PowerOutletFeedLegChoices.FEED_LEG_B,
        }

        cls.bulk_edit_data = {
            "type": PowerOutletTypeChoices.TYPE_IEC_C13,
            "feed_leg": PowerOutletFeedLegChoices.FEED_LEG_B,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": getattr(getattr(test_instance, "device_type", None), "pk", None),
            "module_type": getattr(getattr(test_instance, "module_type", None), "pk", None),
            # power_port_template must match the parent device/module type
            "power_port_template": getattr(test_instance.power_port_template, "pk", None),
            "label": "new test label",
            "description": "new test description",
        }


class InterfaceTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = InterfaceTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        devicetypes = (
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1"),
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 2"),
        )

        InterfaceTemplate.objects.create(
            device_type=devicetypes[0],
            type=InterfaceTypeChoices.TYPE_100GE_QSFP_DD,
            name="Interface Template 1",
        )
        InterfaceTemplate.objects.create(
            device_type=devicetypes[0],
            type=InterfaceTypeChoices.TYPE_100GE_QSFP_DD,
            name="Interface Template 2",
        )
        InterfaceTemplate.objects.create(
            device_type=devicetypes[0],
            type=InterfaceTypeChoices.TYPE_100GE_QSFP_DD,
            name="Interface Template 3",
        )

        cls.form_data = {
            "device_type": devicetypes[1].pk,
            "name": "Interface Template X",
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "mgmt_only": True,
        }

        cls.bulk_create_data = {
            "device_type": devicetypes[1].pk,
            "name_pattern": "Interface Template [4-6]",
            # Test that a label can be applied to each generated interface templates
            "label_pattern": "Interface Template Label [3-5]",
            "description": "View Test Bulk Create Interfaces",
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "mgmt_only": True,
        }

        cls.bulk_edit_data = {
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "mgmt_only": True,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": getattr(getattr(test_instance, "device_type", None), "pk", None),
            "module_type": getattr(getattr(test_instance, "module_type", None), "pk", None),
            "type": test_instance.type,
            "label": "new test label",
            "description": "new test description",
        }


class FrontPortTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = FrontPortTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")

        rearports = (
            RearPortTemplate.objects.create(
                device_type=devicetype,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port Template 1",
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port Template 2",
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port Template 3",
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port Template 4",
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port Template 5",
            ),
            RearPortTemplate.objects.create(
                device_type=devicetype,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port Template 6",
            ),
        )

        FrontPortTemplate.objects.create(
            device_type=devicetype,
            name="View Test Front Port Template 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=rearports[0],
            rear_port_position=1,
        )
        FrontPortTemplate.objects.create(
            device_type=devicetype,
            name="View Test Front Port Template 2",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=rearports[1],
            rear_port_position=1,
        )
        FrontPortTemplate.objects.create(
            device_type=devicetype,
            name="View Test Front Port Template 3",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=rearports[2],
            rear_port_position=1,
        )

        cls.form_data = {
            "device_type": devicetype.pk,
            "name": "Front Port X",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port_template": rearports[3].pk,
            "rear_port_position": 1,
        }

        cls.bulk_create_data = {
            "device_type": devicetype.pk,
            "name_pattern": "View Test Front Port [4-6]",
            "description": "View Test Bulk Create Front Ports",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port_template_set": [f"{rp.pk}:1" for rp in rearports[3:6]],
        }

        cls.bulk_edit_data = {
            "type": PortTypeChoices.TYPE_4P4C,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": getattr(getattr(test_instance, "device_type", None), "pk", None),
            "module_type": getattr(getattr(test_instance, "module_type", None), "pk", None),
            "rear_port_template": test_instance.rear_port_template.pk,
            "rear_port_position": test_instance.rear_port_position,
            "type": test_instance.type,
            "label": "new test label",
            "description": "new test description",
        }


class RearPortTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = RearPortTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        devicetypes = (
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1"),
            DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 2"),
        )

        RearPortTemplate.objects.create(
            device_type=devicetypes[0],
            type=PortTypeChoices.TYPE_8P8C,
            positions=24,
            name="Rear Port Template 1",
        )
        RearPortTemplate.objects.create(
            device_type=devicetypes[0],
            type=PortTypeChoices.TYPE_8P8C,
            positions=24,
            name="Rear Port Template 2",
        )
        RearPortTemplate.objects.create(
            device_type=devicetypes[0],
            type=PortTypeChoices.TYPE_8P8C,
            positions=24,
            name="Rear Port Template 3",
        )

        cls.form_data = {
            "device_type": devicetypes[1].pk,
            "name": "Rear Port Template X",
            "type": PortTypeChoices.TYPE_8P8C,
            "positions": 2,
        }

        cls.bulk_create_data = {
            "device_type": devicetypes[1].pk,
            "name_pattern": "Rear Port Template [4-6]",
            "description": "View Test Bulk Create Rear Ports",
            "type": PortTypeChoices.TYPE_8P8C,
            "positions": 2,
        }

        cls.bulk_edit_data = {
            "type": PortTypeChoices.TYPE_8P8C,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": getattr(getattr(test_instance, "device_type", None), "pk", None),
            "module_type": getattr(getattr(test_instance, "module_type", None), "pk", None),
            "positions": test_instance.positions,
            "type": test_instance.type,
            "label": "new test label",
            "description": "new test description",
        }


class DeviceBayTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = DeviceBayTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        devicetypes = (
            DeviceType.objects.create(
                manufacturer=manufacturer,
                model="Device Type 1",
                subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
            ),
            DeviceType.objects.create(
                manufacturer=manufacturer,
                model="Device Type 2",
                subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
            ),
        )

        DeviceBayTemplate.objects.create(device_type=devicetypes[0], name="Device Bay Template 1")
        DeviceBayTemplate.objects.create(device_type=devicetypes[0], name="Device Bay Template 2")
        DeviceBayTemplate.objects.create(device_type=devicetypes[0], name="Device Bay Template 3")

        cls.form_data = {
            "device_type": devicetypes[1].pk,
            "name": "Device Bay Template X",
        }

        cls.bulk_create_data = {
            "device_type": devicetypes[1].pk,
            "name_pattern": "Device Bay Template [4-6]",
            "description": "View Test Bulk Create Device Bays",
        }

        cls.bulk_edit_data = {
            "description": "Foo bar",
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": test_instance.device_type.pk,
            "label": "new test label",
            "description": "new test description",
        }


class ModuleBayTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = ModuleBayTemplate

    @classmethod
    def setUpTestData(cls):
        device_type = DeviceType.objects.first()
        module_type = ModuleType.objects.first()
        module_family = ModuleFamily.objects.create(name="Test Module Family")

        cls.form_data = {
            "device_type": device_type.pk,
            "module_type": None,
            "name": "Module Bay Template X",
            "position": "Test modulebaytemplate position",
            "description": "Test modulebaytemplate description",
            "label": "Test modulebaytemplate label",
            "module_family": module_family.pk,
        }

        cls.bulk_create_data = {
            "module_type": module_type.pk,
            "name_pattern": "Test Module Bay Template [5-7]",
            "position_pattern": "Test Module Bay Template Position [10-12]",
            "label_pattern": "Test modulebaytemplate label [1-3]",
            "description": "Test modulebaytemplate description",
            "module_family": module_family.pk,
        }

        cls.bulk_edit_data = {
            "description": "Description changed",
            "module_family": module_family.pk,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": getattr(getattr(test_instance, "device_type", None), "pk", None),
            "module_type": getattr(getattr(test_instance, "module_type", None), "pk", None),
            "position": "new test position",
            "label": "new test label",
            "description": "new test description",
            "module_family": module_family.pk,
        }


class PlatformTestCase(ViewTestCases.OrganizationalObjectViewTestCase, ViewTestCases.BulkEditObjectsViewTestCase):
    model = Platform

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()

        # Protected FK to SoftwareImageFile prevents deletion
        DeviceTypeToSoftwareImageFile.objects.all().delete()
        # Protected FK to SoftwareVersion prevents deletion
        Device.objects.all().update(software_version=None)

        cls.form_data = {
            "name": "Platform X",
            "manufacturer": manufacturer.pk,
            "napalm_driver": "junos",
            "napalm_args": None,
            "network_driver": "juniper_junos",
            "description": "A new platform",
        }
        cls.bulk_edit_data = {
            "manufacturer": manufacturer.pk,
            "napalm_driver": "iosxr",
            "napalm_args": '{"timeout": 30, "retries": 3}',
            "network_driver": "cisco_ios",
            "description": "Updated platform description",
        }


class DeviceTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Device

    @classmethod
    def setUpTestData(cls):
        Controller.objects.filter(controller_device__isnull=False).delete()
        Device.objects.all().delete()
        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]

        rack_group = RackGroup.objects.create(location=locations[0], name="Rack Group 1")

        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(name="Cluster 1", cluster_type=cluster_type)

        rack_status = Status.objects.get_for_model(Rack).first()
        racks = (
            Rack.objects.create(
                name="Rack 1",
                location=locations[0],
                rack_group=rack_group,
                status=rack_status,
            ),
            Rack.objects.create(name="Rack 2", location=locations[1], status=rack_status),
        )

        manufacturer = Manufacturer.objects.first()

        devicetypes = (
            DeviceType.objects.create(model="Device Type 1", manufacturer=manufacturer),
            DeviceType.objects.create(model="Device Type 2", manufacturer=manufacturer),
        )

        deviceroles = Role.objects.get_for_model(Device)[:2]

        platforms = Platform.objects.all()[:2]
        for platform in platforms:
            platform.manufacturer = manufacturer
            platform.save()

        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
        )

        statuses = Status.objects.get_for_model(Device)
        status_active = statuses[0]

        # We want unique sets of software image files for each device type
        software_image_files = list(SoftwareImageFile.objects.filter(default_image=False)[:4])
        software_versions = list(SoftwareVersion.objects.filter(software_image_files__isnull=False)[:2])
        software_image_files[0].software_version = software_versions[0]
        software_image_files[1].software_version = software_versions[0]
        software_image_files[2].software_version = software_versions[1]
        software_image_files[3].software_version = software_versions[1]
        for software_image_file in software_image_files:
            software_image_file.save()
        devicetypes[0].software_image_files.set(software_image_files[:2])
        devicetypes[1].software_image_files.set(software_image_files[2:])
        # Only valid software image files are those that belong to the device type or default images
        valid_software_image_files = [
            *software_image_files[2:],
            SoftwareImageFile.objects.filter(default_image=True).first(),
        ]

        cls.custom_fields = (
            CustomField.objects.create(
                type=CustomFieldTypeChoices.TYPE_INTEGER,
                label="Crash Counter",
                default=0,
            ),
        )
        cls.custom_fields[0].content_types.set([ContentType.objects.get_for_model(Device)])

        devices = (
            Device.objects.create(
                name="Device 1",
                location=locations[0],
                rack=racks[0],
                device_type=devicetypes[0],
                role=deviceroles[0],
                platform=platforms[0],
                status=status_active,
                software_version=software_versions[0],
                _custom_field_data={"crash_counter": 5},
            ),
            Device.objects.create(
                name="Device 2",
                location=locations[0],
                rack=racks[0],
                device_type=devicetypes[0],
                role=deviceroles[0],
                platform=platforms[0],
                status=status_active,
                software_version=software_versions[0],
                _custom_field_data={"crash_counter": 10},
            ),
            Device.objects.create(
                name="Device 3",
                location=locations[0],
                rack=racks[0],
                device_type=devicetypes[0],
                role=deviceroles[0],
                platform=platforms[0],
                status=status_active,
                secrets_group=secrets_groups[0],
                _custom_field_data={"crash_counter": 15},
            ),
        )

        cls.relationships = (
            Relationship(
                label="BGP Router-ID",
                key="router_id",
                type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
                source_type=ContentType.objects.get_for_model(Device),
                source_label="BGP Router ID",
                destination_type=ContentType.objects.get_for_model(IPAddress),
                destination_label="Device using this as BGP router-ID",
            ),
        )
        for relationship in cls.relationships:
            relationship.validated_save()

        cls.ipaddr_status = Status.objects.get_for_model(IPAddress).first()
        cls.prefix_status = Status.objects.get_for_model(Prefix).first()
        namespace = Namespace.objects.first()
        Prefix.objects.create(prefix="1.1.1.1/24", namespace=namespace, status=cls.prefix_status)
        Prefix.objects.create(prefix="2.2.2.2/24", namespace=namespace, status=cls.prefix_status)
        Prefix.objects.create(prefix="3.3.3.3/24", namespace=namespace, status=cls.prefix_status)
        ipaddresses = (
            IPAddress.objects.create(address="1.1.1.1/32", namespace=namespace, status=cls.ipaddr_status),
            IPAddress.objects.create(address="2.2.2.2/32", namespace=namespace, status=cls.ipaddr_status),
            IPAddress.objects.create(address="3.3.3.3/32", namespace=namespace, status=cls.ipaddr_status),
        )

        intf_status = Status.objects.get_for_model(Interface).first()
        intf_role = Role.objects.get_for_model(Interface).first()
        cls.interfaces = (
            Interface.objects.create(device=devices[0], name="Interface A1", status=intf_status, role=intf_role),
            Interface.objects.create(device=devices[0], name="Interface A2", status=intf_status),
            Interface.objects.create(device=devices[0], name="Interface A3", status=intf_status, role=intf_role),
        )

        for device, ipaddress in zip(devices, ipaddresses):
            RelationshipAssociation(
                relationship=cls.relationships[0], source=device, destination=ipaddress
            ).validated_save()

        cls.form_data = {
            "device_type": devicetypes[1].pk,
            "role": deviceroles[1].pk,
            "tenant": None,
            "platform": platforms[1].pk,
            "name": "Device X",
            "serial": "VMWARE-XX XX XX XX XX XX XX XX-XX XX XX XX XX XX XX XX",
            "asset_tag": generate_random_device_asset_tag_of_specified_size(100),
            "location": locations[1].pk,
            "rack": racks[1].pk,
            "position": 1,
            "face": DeviceFaceChoices.FACE_FRONT,
            "status": statuses[1].pk,
            "primary_ip4": None,
            "primary_ip6": None,
            "cluster": None,
            "secrets_group": secrets_groups[1].pk,
            "virtual_chassis": None,
            "vc_position": None,
            "vc_priority": None,
            "comments": "A new device",
            "tags": [t.pk for t in Tag.objects.get_for_model(Device)],
            "local_config_context_data": None,
            "cf_crash_counter": -1,
            "cr_router-id": None,
            "software_version": software_versions[1].pk,
            "software_image_files": [f.pk for f in valid_software_image_files],
        }

        cls.bulk_edit_data = {
            "device_type": devicetypes[1].pk,
            "role": deviceroles[1].pk,
            "tenant": None,
            "platform": platforms[1].pk,
            "serial": "VMWARE-XX XX XX XX XX XX XX XX-XX XX XX XX XX XX XX XX",
            "status": statuses[2].pk,
            "location": locations[1].pk,
            "rack": racks[1].pk,
            "cluster": cluster.pk,
            "comments": "An older device",
            "position": None,
            "face": DeviceFaceChoices.FACE_FRONT,
            "secrets_group": secrets_groups[1].pk,
            "software_version": software_versions[1].pk,
            "controller_managed_device_group": ControllerManagedDeviceGroup.objects.first().pk,
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_vdc_panel_includes_add_vdc_btn(self):
        """Assert Add Virtual device Contexts button is in Device detail view: Issue from #6348"""
        device = Device.objects.first()
        url = reverse("dcim:device", kwargs={"pk": device.pk})
        response = self.client.get(url)
        response_body = extract_page_body(response.content.decode(response.charset))

        add_vdc_url = reverse("dcim:virtualdevicecontext_add")
        return_url = device.get_absolute_url()
        expected_add_vdc_button_html = f"""
        <a href="{add_vdc_url}?device={device.id}&amp;return_url={return_url}" class="btn btn-primary btn-xs">
            <span class="mdi mdi-plus-thick" aria-hidden="true"></span> Add virtual device context
        </a>
        """
        self.assertInHTML(expected_add_vdc_button_html, response_body)
        self.assertIn("Add virtual device context", response_body)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_consoleports(self):
        device = Device.objects.first()

        ConsolePort.objects.create(device=device, name="Console Port 1")
        ConsolePort.objects.create(device=device, name="Console Port 2")
        ConsolePort.objects.create(device=device, name="Console Port 3")

        url = reverse("dcim:device_consoleports", kwargs={"pk": device.pk})
        self.assertHttpStatus(self.client.get(url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_consoleserverports(self):
        device = Device.objects.first()

        ConsoleServerPort.objects.create(device=device, name="Console Server Port 1")
        ConsoleServerPort.objects.create(device=device, name="Console Server Port 2")
        ConsoleServerPort.objects.create(device=device, name="Console Server Port 3")

        url = reverse("dcim:device_consoleserverports", kwargs={"pk": device.pk})
        self.assertHttpStatus(self.client.get(url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_powerports(self):
        device = Device.objects.first()

        PowerPort.objects.create(device=device, name="Power Port 1")
        PowerPort.objects.create(device=device, name="Power Port 2")
        PowerPort.objects.create(device=device, name="Power Port 3")

        url = reverse("dcim:device_powerports", kwargs={"pk": device.pk})
        self.assertHttpStatus(self.client.get(url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_poweroutlets(self):
        device = Device.objects.first()

        PowerOutlet.objects.create(device=device, name="Power Outlet 1")
        PowerOutlet.objects.create(device=device, name="Power Outlet 2")
        PowerOutlet.objects.create(device=device, name="Power Outlet 3")

        url = reverse("dcim:device_poweroutlets", kwargs={"pk": device.pk})
        self.assertHttpStatus(self.client.get(url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_interfaces(self):
        device = Device.objects.filter(interfaces__isnull=False).first()
        self.add_permissions("ipam.add_ipaddress", "dcim.change_interface")

        url = reverse("dcim:device_interfaces", kwargs={"pk": device.pk})
        response = self.client.get(url)
        # Assert that "Add IP address" appears for each of the three interfaces
        self.assertBodyContains(response, "Add IP address", count=3)

    def test_device_interface_assign_ipaddress(self):
        device = Device.objects.first()
        self.add_permissions(
            "ipam.add_ipaddress",
            "extras.view_status",
            "ipam.view_namespace",
            "dcim.view_device",
            "dcim.view_interface",
        )
        device_list_url = reverse("dcim:device_interfaces", args=(device.pk,))
        namespace = Namespace.objects.first()
        ipaddresses = [str(ipadress) for ipadress in IPAddress.objects.values_list("pk", flat=True)[:3]]
        add_new_ip_form_data = {
            "namespace": namespace.pk,
            "address": "1.1.1.7/24",
            "tenant": None,
            "status": Status.objects.get_for_model(IPAddress).first().pk,
            "type": IPAddressTypeChoices.TYPE_DHCP,
            "role": None,
            "nat_inside": None,
            "dns_name": None,
            "description": None,
            "tags": [],
            "interface": self.interfaces[0].id,
        }
        add_new_ip_request = {
            "path": reverse("ipam:ipaddress_add") + f"?interface={self.interfaces[0].id}&return_url={device_list_url}",
            "data": post_data(add_new_ip_form_data),
        }
        assign_ip_form_data = {"pk": ipaddresses}
        assign_ip_request = {
            "path": reverse("ipam:ipaddress_assign")
            + f"?interface={self.interfaces[1].id}&return_url={device_list_url}",
            "data": post_data(assign_ip_form_data),
        }

        with self.subTest("Assert Cannot assign IPAddress('Add New') without permission"):
            # Assert Add new IPAddress
            response = self.client.post(**add_new_ip_request, follow=True)
            self.assertBodyContains(response, f"Interface with id &quot;{self.interfaces[0].pk}&quot; not found")
            self.interfaces[0].refresh_from_db()
            self.assertEqual(self.interfaces[0].ip_addresses.all().count(), 0)

        with self.subTest("Assert Cannot assign IPAddress(Existing IP) without permission"):
            # Assert Assign Exsisting IPAddress
            response = self.client.post(**assign_ip_request, follow=True)
            self.assertBodyContains(response, f"Interface with id &quot;{self.interfaces[1].pk}&quot; not found")
            self.interfaces[1].refresh_from_db()
            self.assertEqual(self.interfaces[1].ip_addresses.all().count(), 0)

        self.add_permissions("dcim.change_interface", "ipam.view_ipaddress")

        with self.subTest("Assert Create and Assign IPAddress"):
            self.assertHttpStatus(self.client.post(**add_new_ip_request), 302)
            self.interfaces[0].refresh_from_db()
            self.assertEqual(
                str(self.interfaces[0].ip_addresses.all().first().address),
                add_new_ip_form_data["address"],
            )

        with self.subTest("Assert Assign IPAddress"):
            response = self.client.post(**assign_ip_request)
            self.assertHttpStatus(response, 302)
            self.interfaces[1].refresh_from_db()
            self.assertEqual(self.interfaces[1].ip_addresses.count(), 3)
            interface_ips = [str(ip) for ip in self.interfaces[1].ip_addresses.values_list("pk", flat=True)]
            self.assertEqual(
                sorted(ipaddresses),
                sorted(interface_ips),
            )

        with self.subTest("Assert Assigning IPAddress Without Selecting Any IPAddress Raises Exception"):
            assign_ip_form_data["pk"] = []
            assign_ip_request = {
                "path": reverse("ipam:ipaddress_assign")
                + f"?interface={self.interfaces[1].id}&return_url={device_list_url}",
                "data": post_data(assign_ip_form_data),
            }
            response = self.client.post(**assign_ip_request, follow=True)
            self.assertBodyContains(response, "Please select at least one IP Address from the table.")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_rearports(self):
        device = Device.objects.first()

        RearPort.objects.create(device=device, name="Rear Port 1")
        RearPort.objects.create(device=device, name="Rear Port 2")
        RearPort.objects.create(device=device, name="Rear Port 3")

        url = reverse("dcim:device_rearports", kwargs={"pk": device.pk})
        self.assertHttpStatus(self.client.get(url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_frontports(self):
        device = Device.objects.first()
        rear_ports = (
            RearPort.objects.create(device=device, name="Rear Port 1"),
            RearPort.objects.create(device=device, name="Rear Port 2"),
            RearPort.objects.create(device=device, name="Rear Port 3"),
        )

        FrontPort.objects.create(
            device=device,
            name="Front Port 1",
            rear_port=rear_ports[0],
            rear_port_position=1,
        )
        FrontPort.objects.create(
            device=device,
            name="Front Port 2",
            rear_port=rear_ports[1],
            rear_port_position=1,
        )
        FrontPort.objects.create(
            device=device,
            name="Front Port 3",
            rear_port=rear_ports[2],
            rear_port_position=1,
        )

        url = reverse("dcim:device_frontports", kwargs={"pk": device.pk})
        self.assertHttpStatus(self.client.get(url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_devicebays(self):
        device = Device.objects.first()

        # Device Bay 1 was already created in setUpTestData()
        DeviceBay.objects.create(device=device, name="Device Bay 2")
        DeviceBay.objects.create(device=device, name="Device Bay 3")

        url = reverse("dcim:device_devicebays", kwargs={"pk": device.pk})
        self.assertHttpStatus(self.client.get(url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_inventory(self):
        device = Device.objects.first()

        InventoryItem.objects.create(device=device, name="Inventory Item 1")
        InventoryItem.objects.create(device=device, name="Inventory Item 2")
        InventoryItem.objects.create(device=device, name="Inventory Item 3")

        url = reverse("dcim:device_inventory", kwargs={"pk": device.pk})
        self.assertHttpStatus(self.client.get(url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_device_primary_ips(self):
        """Test assigning a primary IP to a device."""
        self.add_permissions("dcim.change_device")

        # Create an interface and assign an IP to it.
        device = Device.objects.filter(interfaces__isnull=False).first()
        interface = device.interfaces.first()
        namespace = Namespace.objects.first()
        Prefix.objects.create(prefix="1.2.3.0/24", namespace=namespace, status=self.prefix_status)
        ip_address = IPAddress.objects.create(address="1.2.3.4/32", namespace=namespace, status=self.ipaddr_status)
        interface.ip_addresses.add(ip_address)

        # Dupe the form data and populated primary_ip4 w/ ip_address
        form_data = self.form_data.copy()
        form_data["primary_ip4"] = ip_address.pk
        # Assert that update succeeds.
        request = {
            "path": self._get_url("edit", device),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertInstanceEqual(self._get_queryset().order_by("last_updated").last(), form_data)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_local_config_context_schema_validation_pass(self):
        """
        Given a config context schema
        And a device with local context that conforms to that schema
        Assert that the local context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1",
            data_schema={"type": "object", "properties": {"foo": {"type": "string"}}},
        )
        self.add_permissions("dcim.add_device")

        form_data = self.form_data.copy()
        form_data["local_config_context_schema"] = schema.pk
        form_data["local_config_context_data"] = '{"foo": "bar"}'

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(
            self._get_queryset().get(name="Device X").local_config_context_schema.pk,
            schema.pk,
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_local_config_context_schema_validation_fails(self):
        """
        Given a config context schema
        And a device with local context that *does not* conform to that schema
        Assert that the local context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1",
            data_schema={"type": "object", "properties": {"foo": {"type": "integer"}}},
        )
        self.add_permissions("dcim.add_device")

        form_data = self.form_data.copy()
        form_data["local_config_context_schema"] = schema.pk
        form_data["local_config_context_data"] = '{"foo": "bar"}'

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 200)
        self.assertEqual(self._get_queryset().filter(name="Device X").count(), 0)


class ModuleTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Module
    custom_action_required_permissions = {
        "dcim:module_consoleports": ["dcim.view_module", "dcim.view_consoleport"],
        "dcim:module_consoleserverports": ["dcim.view_module", "dcim.view_consoleserverport"],
        "dcim:module_powerports": ["dcim.view_module", "dcim.view_powerport"],
        "dcim:module_poweroutlets": ["dcim.view_module", "dcim.view_poweroutlet"],
        "dcim:module_interfaces": ["dcim.view_module", "dcim.view_interface"],
        "dcim:module_rearports": ["dcim.view_module", "dcim.view_rearport"],
        "dcim:module_frontports": ["dcim.view_module", "dcim.view_frontport"],
        "dcim:module_modulebays": ["dcim.view_module", "dcim.view_modulebay"],
    }

    @classmethod
    def setUpTestData(cls):
        Module.objects.all().delete()
        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]
        manufacturer = Manufacturer.objects.first()

        moduletypes = (
            ModuleType.objects.create(model="Module Type 1", manufacturer=manufacturer),
            ModuleType.objects.create(model="Module Type 2", manufacturer=manufacturer),
        )

        moduleroles = Role.objects.get_for_model(Module)[:2]

        statuses = Status.objects.get_for_model(Module)
        status_active = statuses[0]

        cls.custom_fields = (
            CustomField.objects.create(
                type=CustomFieldTypeChoices.TYPE_INTEGER,
                label="Crash Counter",
                default=0,
            ),
        )
        cls.custom_fields[0].content_types.set([ContentType.objects.get_for_model(Module)])

        modules = (
            Module.objects.create(
                location=locations[0],
                module_type=moduletypes[0],
                role=moduleroles[0],
                status=status_active,
                _custom_field_data={"crash_counter": 5},
            ),
            Module.objects.create(
                location=locations[0],
                module_type=moduletypes[0],
                role=moduleroles[0],
                status=status_active,
                _custom_field_data={"crash_counter": 10},
            ),
            Module.objects.create(
                location=locations[0],
                module_type=moduletypes[0],
                role=moduleroles[0],
                status=status_active,
                _custom_field_data={"crash_counter": 15},
            ),
        )

        cls.relationships = (
            Relationship(
                label="BGP Router-ID",
                key="router_id",
                type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
                source_type=ContentType.objects.get_for_model(Module),
                source_label="BGP Router ID",
                destination_type=ContentType.objects.get_for_model(IPAddress),
                destination_label="Module using this as BGP router-ID",
            ),
        )
        for relationship in cls.relationships:
            relationship.validated_save()

        cls.ipaddr_status = Status.objects.get_for_model(IPAddress).first()
        cls.prefix_status = Status.objects.get_for_model(Prefix).first()
        namespace = Namespace.objects.first()
        Prefix.objects.create(prefix="1.1.1.1/24", namespace=namespace, status=cls.prefix_status)
        Prefix.objects.create(prefix="2.2.2.2/24", namespace=namespace, status=cls.prefix_status)
        Prefix.objects.create(prefix="3.3.3.3/24", namespace=namespace, status=cls.prefix_status)
        ipaddresses = (
            IPAddress.objects.create(address="1.1.1.1/32", namespace=namespace, status=cls.ipaddr_status),
            IPAddress.objects.create(address="2.2.2.2/32", namespace=namespace, status=cls.ipaddr_status),
            IPAddress.objects.create(address="3.3.3.3/32", namespace=namespace, status=cls.ipaddr_status),
        )

        intf_status = Status.objects.get_for_model(Interface).first()
        intf_role = Role.objects.get_for_model(Interface).first()
        cls.interfaces = (
            Interface.objects.create(module=modules[0], name="Interface A1", status=intf_status, role=intf_role),
            Interface.objects.create(module=modules[0], name="Interface A2", status=intf_status),
            Interface.objects.create(module=modules[0], name="Interface A3", status=intf_status, role=intf_role),
        )

        for module, ipaddress in zip(modules, ipaddresses):
            RelationshipAssociation(
                relationship=cls.relationships[0], source=module, destination=ipaddress
            ).validated_save()

        cls.form_data = {
            "module_type": moduletypes[1].pk,
            "role": moduleroles[1].pk,
            "tenant": None,
            "serial": "VMWARE-XX XX XX XX XX XX XX XX-XX XX XX XX XX XX XX XX",
            "asset_tag": generate_random_device_asset_tag_of_specified_size(100),
            "location": locations[1].pk,
            "status": statuses[1].pk,
            "tags": [t.pk for t in Tag.objects.get_for_model(Module)],
            "cf_crash_counter": -1,
            "cr_router-id": None,
        }

        cls.bulk_edit_data = {
            "role": moduleroles[1].pk,
            "tenant": None,
            "status": statuses[2].pk,
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_module_interfaces(self):
        module = Module.objects.filter(interfaces__isnull=False).first()
        self.add_permissions("ipam.add_ipaddress", "dcim.change_interface")

        url = reverse("dcim:module_interfaces", kwargs={"pk": module.pk})
        response = self.client.get(url)
        # Assert that "Add IP address" appears for each of the three interfaces
        self.assertBodyContains(response, "Add IP address", count=3)

    def test_module_interface_assign_ipaddress(self):
        module = Module.objects.first()
        self.add_permissions(
            "ipam.add_ipaddress",
            "extras.view_status",
            "ipam.view_namespace",
            "dcim.view_module",
            "dcim.view_interface",
        )
        module_list_url = reverse("dcim:module_interfaces", args=(module.pk,))
        namespace = Namespace.objects.first()
        ipaddresses = [str(ipadress) for ipadress in IPAddress.objects.values_list("pk", flat=True)[:3]]
        add_new_ip_form_data = {
            "namespace": namespace.pk,
            "address": "1.1.1.7/24",
            "tenant": None,
            "status": Status.objects.get_for_model(IPAddress).first().pk,
            "type": IPAddressTypeChoices.TYPE_DHCP,
            "role": None,
            "nat_inside": None,
            "dns_name": None,
            "description": None,
            "tags": [],
            "interface": self.interfaces[0].id,
        }
        add_new_ip_request = {
            "path": reverse("ipam:ipaddress_add") + f"?interface={self.interfaces[0].id}&return_url={module_list_url}",
            "data": post_data(add_new_ip_form_data),
        }
        assign_ip_form_data = {"pk": ipaddresses}
        assign_ip_request = {
            "path": reverse("ipam:ipaddress_assign")
            + f"?interface={self.interfaces[1].id}&return_url={module_list_url}",
            "data": post_data(assign_ip_form_data),
        }

        with self.subTest("Assert Cannot assign IPAddress('Add New') without permission"):
            # Assert Add new IPAddress
            response = self.client.post(**add_new_ip_request, follow=True)
            self.assertBodyContains(response, f"Interface with id &quot;{self.interfaces[0].pk}&quot; not found")
            self.interfaces[0].refresh_from_db()
            self.assertEqual(self.interfaces[0].ip_addresses.all().count(), 0)

        with self.subTest("Assert Cannot assign IPAddress(Existing IP) without permission"):
            # Assert Assign Exsisting IPAddress
            response = self.client.post(**assign_ip_request, follow=True)
            self.assertBodyContains(response, f"Interface with id &quot;{self.interfaces[1].pk}&quot; not found")
            self.interfaces[1].refresh_from_db()
            self.assertEqual(self.interfaces[1].ip_addresses.all().count(), 0)

        self.add_permissions("dcim.change_interface", "ipam.view_ipaddress")

        with self.subTest("Assert Create and Assign IPAddress"):
            self.assertHttpStatus(self.client.post(**add_new_ip_request), 302)
            self.interfaces[0].refresh_from_db()
            self.assertEqual(
                str(self.interfaces[0].ip_addresses.all().first().address),
                add_new_ip_form_data["address"],
            )

        with self.subTest("Assert Assign IPAddress"):
            response = self.client.post(**assign_ip_request)
            self.assertHttpStatus(response, 302)
            self.interfaces[1].refresh_from_db()
            self.assertEqual(self.interfaces[1].ip_addresses.count(), 3)
            interface_ips = [str(ip) for ip in self.interfaces[1].ip_addresses.values_list("pk", flat=True)]
            self.assertEqual(
                sorted(ipaddresses),
                sorted(interface_ips),
            )


class ConsolePortTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = ConsolePort

    @classmethod
    def setUpTestData(cls):
        device = create_test_device("Device 1")

        console_ports = (
            ConsolePort.objects.create(device=device, name="Console Port 1"),
            ConsolePort.objects.create(device=device, name="Console Port 2"),
            ConsolePort.objects.create(device=device, name="Console Port 3"),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = console_ports
        cls.selected_objects_parent_name = device.name

        cls.form_data = {
            "device": device.pk,
            "name": "Console Port X",
            "type": ConsolePortTypeChoices.TYPE_RJ45,
            "description": "A console port",
            "tags": sorted([t.pk for t in Tag.objects.get_for_model(ConsolePort)]),
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Console Port [4-6]",
            # Test that a label can be applied to each generated console ports
            "label_pattern": "Serial[3-5]",
            "type": ConsolePortTypeChoices.TYPE_RJ45,
            "description": "A console port",
            "tags": sorted([t.pk for t in Tag.objects.get_for_model(ConsolePort)]),
        }

        cls.bulk_edit_data = {
            "type": ConsolePortTypeChoices.TYPE_RJ45,
            "description": "New description",
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device": getattr(getattr(test_instance, "device", None), "pk", None),
            "module": getattr(getattr(test_instance, "module", None), "pk", None),
            "label": "new test label",
            "description": "new test description",
        }


class ConsoleServerPortTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = ConsoleServerPort

    @classmethod
    def setUpTestData(cls):
        device = create_test_device("Device 1")

        console_server_ports = (
            ConsoleServerPort.objects.create(device=device, name="Console Server Port 1"),
            ConsoleServerPort.objects.create(device=device, name="Console Server Port 2"),
            ConsoleServerPort.objects.create(device=device, name="Console Server Port 3"),
        )

        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = console_server_ports
        cls.selected_objects_parent_name = device.name

        cls.form_data = {
            "device": device.pk,
            "name": "Console Server Port X",
            "type": ConsolePortTypeChoices.TYPE_RJ45,
            "description": "A console server port",
            "tags": [t.pk for t in Tag.objects.get_for_model(ConsoleServerPort)],
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Console Server Port [4-6]",
            "type": ConsolePortTypeChoices.TYPE_RJ45,
            "description": "A console server port",
            "tags": [t.pk for t in Tag.objects.get_for_model(ConsoleServerPort)],
        }

        cls.bulk_edit_data = {
            "type": ConsolePortTypeChoices.TYPE_RJ11,
            "description": "New description",
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device": getattr(getattr(test_instance, "device", None), "pk", None),
            "module": getattr(getattr(test_instance, "module", None), "pk", None),
            "label": "new test label",
            "description": "new test description",
        }


class PowerPortTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = PowerPort

    @classmethod
    def setUpTestData(cls):
        device = create_test_device("Device 1")

        power_ports = (
            PowerPort.objects.create(device=device, name="Power Port 1"),
            PowerPort.objects.create(device=device, name="Power Port 2"),
            PowerPort.objects.create(device=device, name="Power Port 3"),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = power_ports
        cls.selected_objects_parent_name = device.name

        cls.form_data = {
            "device": device.pk,
            "name": "Power Port X",
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
            "power_factor": Decimal("0.95"),
            "description": "A power port",
            "tags": [t.pk for t in Tag.objects.get_for_model(PowerPort)],
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Power Port [4-6]",
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
            "power_factor": Decimal("0.95"),
            "description": "A power port",
            "tags": [t.pk for t in Tag.objects.get_for_model(PowerPort)],
        }

        cls.bulk_edit_data = {
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
            "description": "New description",
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device": getattr(getattr(test_instance, "device", None), "pk", None),
            "module": getattr(getattr(test_instance, "module", None), "pk", None),
            "power_factor": Decimal("0.95"),
            "label": "new test label",
            "description": "new test description",
        }


class PowerOutletTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = PowerOutlet

    @classmethod
    def setUpTestData(cls):
        PowerOutlet.objects.all().delete()
        device = create_test_device("Device 1")

        powerports = (
            PowerPort.objects.create(device=device, name="Power Port 1"),
            PowerPort.objects.create(device=device, name="Power Port 2"),
        )

        poweroutlets = (
            PowerOutlet.objects.create(device=device, name="Power Outlet 1", power_port=powerports[0]),
            PowerOutlet.objects.create(device=device, name="Power Outlet 2", power_port=powerports[0]),
            PowerOutlet.objects.create(device=device, name="Power Outlet 3", power_port=powerports[0]),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = poweroutlets
        cls.selected_objects_parent_name = device.name

        cls.form_data = {
            "device": device.pk,
            "name": "Power Outlet X",
            "type": PowerOutletTypeChoices.TYPE_IEC_C13,
            "power_port": powerports[1].pk,
            "feed_leg": PowerOutletFeedLegChoices.FEED_LEG_B,
            "description": "A power outlet",
            "tags": [t.pk for t in Tag.objects.get_for_model(PowerOutlet)],
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Power Outlet [4-6]",
            "type": PowerOutletTypeChoices.TYPE_IEC_C13,
            "power_port": powerports[1].pk,
            "feed_leg": PowerOutletFeedLegChoices.FEED_LEG_B,
            "description": "A power outlet",
            "tags": [t.pk for t in Tag.objects.get_for_model(PowerOutlet)],
        }

        cls.bulk_add_data = {
            "device": device.pk,
            "name_pattern": "Power Outlet [4-6]",
            "type": PowerOutletTypeChoices.TYPE_IEC_C13,
            "feed_leg": PowerOutletFeedLegChoices.FEED_LEG_B,
            "description": "A power outlet",
            "tags": [t.pk for t in Tag.objects.get_for_model(PowerOutlet)],
        }

        cls.bulk_edit_data = {
            "type": PowerOutletTypeChoices.TYPE_IEC_C15,
            "power_port": powerports[1].pk,
            "feed_leg": PowerOutletFeedLegChoices.FEED_LEG_B,
            "description": "New description",
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device_type": getattr(getattr(test_instance, "device_type", None), "pk", None),
            "module_type": getattr(getattr(test_instance, "module_type", None), "pk", None),
            "power_port": getattr(test_instance.power_port, "pk", None),  # power_port must match parent device/module
            "label": "new test label",
            "description": "new test description",
        }


class InterfaceTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = Interface

    @classmethod
    def setUpTestData(cls):
        Interface.objects.all().delete()
        device = create_test_device("Device 1")
        vrfs = list(VRF.objects.all()[:3])
        for vrf in vrfs:
            vrf.add_device(device)

        statuses = Status.objects.get_for_model(Interface)
        status_active = statuses[0]
        role = Role.objects.get_for_model(Interface).first()
        interfaces = (
            Interface.objects.create(device=device, name="Interface A1", status=status_active, role=role),
            Interface.objects.create(device=device, name="Interface A2", status=status_active),
            Interface.objects.create(device=device, name="Interface A3", status=status_active, role=role),
            Interface.objects.create(
                device=device,
                name="LAG",
                status=status_active,
                type=InterfaceTypeChoices.TYPE_LAG,
                role=role,
            ),
            Interface.objects.create(
                device=device,
                name="BRIDGE",
                status=status_active,
                type=InterfaceTypeChoices.TYPE_BRIDGE,
                role=role,
            ),
        )
        cls.lag_interface = interfaces[3]
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = interfaces
        cls.selected_objects_parent_name = device.name

        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlan_group = VLANGroup.objects.first()
        vlans = (
            VLAN.objects.create(
                vid=1,
                name="VLAN1",
                location=device.location,
                status=vlan_status,
                vlan_group=vlan_group,
            ),
            VLAN.objects.create(
                vid=101,
                name="VLAN101",
                location=device.location,
                status=vlan_status,
                vlan_group=vlan_group,
            ),
            VLAN.objects.create(
                vid=102,
                name="VLAN102",
                location=device.location,
                status=vlan_status,
                vlan_group=vlan_group,
            ),
            VLAN.objects.create(
                vid=103,
                name="VLAN103",
                location=device.location,
                status=vlan_status,
                vlan_group=vlan_group,
            ),
        )
        vdcs = [
            VirtualDeviceContext.objects.create(
                name=f"Interface VirtualDeviceContext {i}",
                device=device,
                status=Status.objects.get_for_model(VirtualDeviceContext).first(),
                identifier=100 + i,
            )
            for i in range(2)
        ]

        cls.form_data = {
            "device": device.pk,
            "name": "Interface X",
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "enabled": False,
            "status": status_active.pk,
            "role": role.pk,
            "lag": interfaces[3].pk,
            "mac_address": EUI("01:02:03:04:05:06"),
            "mtu": 2000,
            "mgmt_only": True,
            "description": "A front port",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "untagged_vlan": vlans[0].pk,
            "tagged_vlans": [v.pk for v in vlans[1:4]],
            "virtual_device_contexts": [v.pk for v in vdcs],
            "tags": [t.pk for t in Tag.objects.get_for_model(Interface)],
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Interface [4-6]",
            "label_pattern": "Interface Number [4-6]",
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "enabled": False,
            "bridge": interfaces[4].pk,
            "lag": interfaces[3].pk,
            "mac_address": EUI("01:02:03:04:05:06"),
            "mtu": 2000,
            "mgmt_only": True,
            "description": "An Interface",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "untagged_vlan": vlans[0].pk,
            "tagged_vlans": [v.pk for v in vlans[1:4]],
            "tags": [t.pk for t in Tag.objects.get_for_model(Interface)],
            "status": status_active.pk,
            "role": role.pk,
            "vrf": vrfs[0].pk,
            "virtual_device_contexts": [v.pk for v in vdcs],
        }

        cls.bulk_add_data = {
            "device": device.pk,
            "name_pattern": "Interface [4-6]",
            "label_pattern": "Interface Number [4-6]",
            "status": status_active.pk,
            "role": role.pk,
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "enabled": True,
            "mtu": 1500,
            "mgmt_only": False,
            "description": "An Interface",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "tags": [],
            "vrf": vrfs[1].pk,
        }

        cls.bulk_edit_data = {
            "type": InterfaceTypeChoices.TYPE_1GE_FIXED,
            "enabled": True,
            "lag": interfaces[3].pk,
            "mac_address": EUI("01:02:03:04:05:06"),
            "mtu": 2000,
            "mgmt_only": True,
            "description": "New description",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "untagged_vlan": vlans[0].pk,
            "tagged_vlans": [v.pk for v in vlans[1:4]],
            "status": status_active.pk,
            "role": role.pk,
            "vrf": vrfs[2].pk,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device": getattr(getattr(test_instance, "device", None), "pk", None),
            "module": getattr(getattr(test_instance, "module", None), "pk", None),
            "status": test_instance.status.pk,
            "type": test_instance.type,
            "label": "new test label",
            "description": "new test description",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_virtual_interface_with_parent_lag(self):
        """https://github.com/nautobot/nautobot/issues/4436."""
        self.add_permissions("dcim.add_interface")
        form_data = self.form_data.copy()
        del form_data["name"]
        form_data["name_pattern"] = "LAG.0"
        form_data["type"] = InterfaceTypeChoices.TYPE_VIRTUAL
        form_data["parent_interface"] = self.lag_interface
        del form_data["lag"]
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        instance = self._get_queryset().order_by("last_updated").last()
        self.assertEqual(instance.type, InterfaceTypeChoices.TYPE_VIRTUAL)
        self.assertEqual(instance.parent_interface, self.lag_interface)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_valid_ipaddress_link_of_ipaddress_table_in_interface_detail(self):
        """Assert bug https://github.com/nautobot/nautobot/issues/4685 Invalid link in IPAddress Table in an
        Interface Detail View"""
        interface = Interface.objects.first()
        ipaddress = IPAddress.objects.first()
        interface.ip_addresses.add(ipaddress)

        self.add_permissions("dcim.view_interface", "ipam.view_ipaddress")
        invalid_ipaddress_link = reverse("ipam:ipaddress_edit", args=(ipaddress.pk,))
        valid_ipaddress_link = ipaddress.get_absolute_url()
        response = self.client.get(interface.get_absolute_url() + "?tab=main")
        self.assertBodyContains(response, valid_ipaddress_link)
        response_content = extract_page_body(response.content.decode(response.charset))
        self.assertNotIn(invalid_ipaddress_link, response_content)


class FrontPortTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = FrontPort

    @classmethod
    def setUpTestData(cls):
        device = create_test_device("Device 1")
        cls.device = device

        rearports = (
            RearPort.objects.create(
                device=device,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port 1",
            ),
            RearPort.objects.create(
                device=device,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port 2",
            ),
            RearPort.objects.create(
                device=device,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port 3",
            ),
            RearPort.objects.create(
                device=device,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port 4",
            ),
            RearPort.objects.create(
                device=device,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port 5",
            ),
            RearPort.objects.create(
                device=device,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port 6",
            ),
        )

        frontports = (
            FrontPort.objects.create(
                device=device,
                name="Front Port 1",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port=rearports[0],
                rear_port_position=12,
            ),
            FrontPort.objects.create(
                device=device,
                name="Front Port 2",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port=rearports[1],
                rear_port_position=12,
            ),
            FrontPort.objects.create(
                device=device,
                name="Front Port 3",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port=rearports[2],
                rear_port_position=12,
            ),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = frontports
        cls.selected_objects_parent_name = device.name

        cls.form_data = {
            "device": device.pk,
            "name": "Front Port X",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port": rearports[3].pk,
            "rear_port_position": 1,
            "description": "New description",
            "tags": [t.pk for t in Tag.objects.get_for_model(FrontPort)],
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Front Port [4-6]",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port_set": [f"{rp.pk}:1" for rp in rearports[3:6]],
            "description": "New description",
            "tags": [t.pk for t in Tag.objects.get_for_model(FrontPort)],
        }

        cls.bulk_edit_data = {
            "type": PortTypeChoices.TYPE_8P8C,
            "description": "New description",
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device": getattr(getattr(test_instance, "device", None), "pk", None),
            "module": getattr(getattr(test_instance, "module", None), "pk", None),
            "rear_port": test_instance.rear_port.pk,  # rear_port must match the parent device/module
            "rear_port_position": test_instance.rear_port_position,
            "type": test_instance.type,
            "label": "new test label",
            "description": "new test description",
        }

    @unittest.skip("No DeviceBulkAddFrontPortView exists at present")
    def test_bulk_add_component(self):
        pass


class RearPortTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = RearPort

    @classmethod
    def setUpTestData(cls):
        device = create_test_device("Device 1")

        rearports = (
            RearPort.objects.create(
                device=device,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port 1",
            ),
            RearPort.objects.create(
                device=device,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port 2",
            ),
            RearPort.objects.create(
                device=device,
                type=PortTypeChoices.TYPE_8P8C,
                positions=24,
                name="Rear Port 3",
            ),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = rearports
        cls.selected_objects_parent_name = device.name

        cls.form_data = {
            "device": device.pk,
            "name": "Rear Port X",
            "type": PortTypeChoices.TYPE_8P8C,
            "positions": 3,
            "description": "A rear port",
            "tags": [t.pk for t in Tag.objects.get_for_model(RearPort)],
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Rear Port [4-6]",
            "type": PortTypeChoices.TYPE_8P8C,
            "positions": 3,
            "description": "A rear port",
            "tags": [t.pk for t in Tag.objects.get_for_model(RearPort)],
        }

        cls.bulk_edit_data = {
            "type": PortTypeChoices.TYPE_8P8C,
            "description": "New description",
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device": getattr(getattr(test_instance, "device", None), "pk", None),
            "module": getattr(getattr(test_instance, "module", None), "pk", None),
            "positions": test_instance.positions,
            "type": test_instance.type,
            "label": "new test label",
            "description": "new test description",
        }


class DeviceBayTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = DeviceBay

    @classmethod
    def setUpTestData(cls):
        device = create_test_device("Device 1")

        # Update the DeviceType subdevice role to allow adding DeviceBays
        DeviceType.objects.update(subdevice_role=SubdeviceRoleChoices.ROLE_PARENT)

        devicebays = (
            DeviceBay.objects.create(device=device, name="Device Bay 1"),
            DeviceBay.objects.create(device=device, name="Device Bay 2"),
            DeviceBay.objects.create(device=device, name="Device Bay 3"),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = devicebays
        cls.selected_objects_parent_name = device.name

        cls.form_data = {
            "device": device.pk,
            "name": "Device Bay X",
            "description": "A device bay",
            "tags": [t.pk for t in Tag.objects.get_for_model(DeviceBay)],
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Device Bay [4-6]",
            "description": "A device bay",
            "tags": [t.pk for t in Tag.objects.get_for_model(DeviceBay)],
        }

        cls.bulk_edit_data = {
            "description": "New description",
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device": test_instance.device.pk,
            "label": "new test label",
            "description": "new test description",
        }


class ModuleBayTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = ModuleBay

    @classmethod
    def setUpTestData(cls):
        device = Device.objects.first()
        module = Module.objects.first()

        module_bays = (
            ModuleBay.objects.create(parent_device=device, name="Test View Module Bay 1"),
            ModuleBay.objects.create(parent_device=device, name="Test View Module Bay 2"),
            ModuleBay.objects.create(parent_device=device, name="Test View Module Bay 3"),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = module_bays
        cls.selected_objects_parent_name = device.name

        cls.form_data = {
            "parent_device": device.pk,
            "name": "Test ModuleBay 1",
            "position": 1,
            "description": "Test modulebay description",
            "label": "Test modulebay label",
            "tags": sorted([t.pk for t in Tag.objects.get_for_model(ModuleBay)]),
        }

        cls.bulk_create_data = {
            "parent_module": module.pk,
            "name_pattern": "Test ModuleBay [0-2]",
            "position_pattern": "[1-3]",
            # Test that a label can be applied to each generated module bay
            "label_pattern": "Slot[1-3]",
            "description": "Test modulebay description",
            "tags": sorted([t.pk for t in Tag.objects.get_for_model(ModuleBay)]),
        }

        cls.bulk_edit_data = {
            "position": "new position",
            "description": "New description",
            "label": "New label",
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "parent_device": getattr(getattr(test_instance, "parent_device", None), "pk", None),
            "parent_module": getattr(getattr(test_instance, "parent_module", None), "pk", None),
            "position": "new test position",
            "label": "new test label",
            "description": "new test description",
        }

    def get_deletable_object_pks(self):
        # Since Modules and ModuleBays are nestable, we need to delete ModuleBays that don't have any child ModuleBays
        return ModuleBay.objects.filter(installed_module__isnull=True).values_list("pk", flat=True)[:3]

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_bulk_add_component(self):
        """Test bulk-adding this component to modules."""
        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        initial_count = self._get_queryset().count()

        data = self.bulk_create_data.copy()

        # Load the module-bulk-add form
        module_perm = ObjectPermission(name="Module permission", actions=["change"])
        module_perm.save()
        module_perm.users.add(self.user)
        module_perm.object_types.add(ContentType.objects.get_for_model(Module))
        url = reverse(f"dcim:module_bulk_add_{self.model._meta.model_name}")
        request = {
            "path": url,
            "data": post_data({"pk": data["parent_module"]}),
        }
        self.assertHttpStatus(self.client.post(**request), 200)

        # Post to the module-bulk-add form to create records
        data["pk"] = data.pop("parent_module")
        data["_create"] = ""
        request["data"] = post_data(data)
        self.assertHttpStatus(self.client.post(**request), 302)

        updated_count = self._get_queryset().count()
        self.assertEqual(updated_count, initial_count + self.bulk_create_count)

        matching_count = 0
        for instance in self._get_queryset().all():
            try:
                self.assertInstanceEqual(instance, self.bulk_create_data)
                matching_count += 1
            except AssertionError:
                pass
        self.assertEqual(matching_count, self.bulk_create_count)


class InventoryItemTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = InventoryItem

    @classmethod
    def setUpTestData(cls):
        software_versions = SoftwareVersion.objects.all()[:3]
        device = create_test_device("Device 1")
        manufacturer, _ = Manufacturer.objects.get_or_create(name="Manufacturer 1")

        inventory_items = (
            InventoryItem.objects.create(device=device, name="Inventory Item 1"),
            InventoryItem.objects.create(device=device, name="Inventory Item 2"),
            InventoryItem.objects.create(device=device, name="Inventory Item 3"),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = inventory_items
        cls.selected_objects_parent_name = device.name

        cls.form_data = {
            "device": device.pk,
            "manufacturer": manufacturer.pk,
            "name": "Inventory Item X",
            "parent": None,
            "discovered": False,
            "part_id": "123456",
            "serial": "VMWARE-XX XX XX XX XX XX XX XX-XX XX XX XX XX XX XX XX ABC",
            "asset_tag": "ABC123",
            "description": "An inventory item",
            "tags": [t.pk for t in Tag.objects.get_for_model(InventoryItem)],
            "software_version": software_versions[0].pk,
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Inventory Item [4-6]",
            "manufacturer": manufacturer.pk,
            "parent": None,
            "discovered": False,
            "part_id": "123456",
            "serial": "VMWARE-XX XX XX XX XX XX XX XX-XX XX XX XX XX XX XX XX ABC",
            "description": "An inventory item",
            "tags": [t.pk for t in Tag.objects.get_for_model(InventoryItem)],
            "software_version": software_versions[1].pk,
        }

        cls.bulk_edit_data = {
            "part_id": "123456",
            "description": "New description",
            "software_version": software_versions[2].pk,
        }

        test_instance = cls.model.objects.first()
        cls.update_data = {
            "name": test_instance.name,
            "device": test_instance.device.pk,
            "label": "new test label",
            "description": "new test description",
        }

    def test_table_with_indentation_is_removed_on_filter_or_sort(self):
        self.skipTest("InventoryItem table has no implementation of indentation.")


# TODO: Change base class to PrimaryObjectViewTestCase
# Blocked by lack of common creation view for cables (termination A must be initialized)
class CableTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = Cable

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(model="Device Type 1", manufacturer=manufacturer)
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()

        devices = (
            Device.objects.create(
                name="Device 1",
                location=location,
                device_type=devicetype,
                role=devicerole,
                status=devicestatus,
            ),
            Device.objects.create(
                name="Device 2",
                location=location,
                device_type=devicetype,
                role=devicerole,
                status=devicestatus,
            ),
            Device.objects.create(
                name="Device 3",
                location=location,
                device_type=devicetype,
                role=devicerole,
                status=devicestatus,
            ),
            Device.objects.create(
                name="Device 4",
                location=location,
                device_type=devicetype,
                role=devicerole,
                status=devicestatus,
            ),
        )

        interface_status = Status.objects.get_for_model(Interface).first()
        interfaces = (
            Interface.objects.create(
                device=devices[0],
                name="Interface A1",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[0],
                name="Interface A2",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[0],
                name="Interface A3",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Interface A1",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Interface A2",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Interface A3",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Interface A1",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Interface A2",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Interface A3",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[3],
                name="Interface A1",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[3],
                name="Interface A2",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[3],
                name="Interface A3",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
        )

        statuses = Status.objects.get_for_model(Cable)

        Cable.objects.create(
            termination_a=interfaces[0],
            termination_b=interfaces[3],
            type=CableTypeChoices.TYPE_CAT6,
            status=statuses[0],
        )
        Cable.objects.create(
            termination_a=interfaces[1],
            termination_b=interfaces[4],
            type=CableTypeChoices.TYPE_CAT6,
            status=statuses[0],
        )
        Cable.objects.create(
            termination_a=interfaces[2],
            termination_b=interfaces[5],
            type=CableTypeChoices.TYPE_CAT6,
            status=statuses[0],
        )

        # interface_ct = ContentType.objects.get_for_model(Interface)
        cls.form_data = {
            # Changing terminations not supported when editing an existing Cable
            # FIXME(John): Revisit this as it is likely an actual bug allowing the terminations to be changed after creation.
            # 'termination_a_type': interface_ct.pk,
            # 'termination_a_id': interfaces[0].pk,
            # 'termination_b_type': interface_ct.pk,
            # 'termination_b_id': interfaces[3].pk,
            "type": CableTypeChoices.TYPE_CAT6,
            "status": statuses[1].pk,
            "label": "Label",
            "color": "c0c0c0",
            "length": 100,
            "length_unit": CableLengthUnitChoices.UNIT_FOOT,
            "tags": [t.pk for t in Tag.objects.get_for_model(Cable)],
        }

        cls.bulk_edit_data = {
            "type": CableTypeChoices.TYPE_CAT5E,
            "status": statuses[0].pk,
            "label": "New label",
            "color": "00ff00",
            "length": 50,
            "length_unit": CableLengthUnitChoices.UNIT_METER,
        }

    def test_delete_a_cable_which_has_a_peer_connection(self):
        """Test for https://github.com/nautobot/nautobot/issues/1694."""
        self.add_permissions("dcim.delete_cable")

        location = Location.objects.first()
        device = Device.objects.first()

        interface_status = Status.objects.get_for_model(Interface).first()
        interfaces = [
            Interface.objects.create(device=device, name="eth0", status=interface_status),
            Interface.objects.create(device=device, name="eth1", status=interface_status),
        ]

        provider = Provider.objects.first()
        circuittype = CircuitType.objects.first()
        circuit_status = Status.objects.get_for_model(Circuit).first()
        circuit = Circuit.objects.create(
            cid="Circuit 1",
            provider=provider,
            circuit_type=circuittype,
            status=circuit_status,
        )

        circuit_terminations = [
            CircuitTermination.objects.create(
                circuit=circuit,
                term_side=CircuitTerminationSideChoices.SIDE_A,
                location=location,
            ),
            CircuitTermination.objects.create(
                circuit=circuit,
                term_side=CircuitTerminationSideChoices.SIDE_Z,
                location=location,
            ),
        ]

        status = Status.objects.get_for_model(Cable).get(name="Connected")
        cables = [
            Cable.objects.create(
                termination_a=circuit_terminations[0],
                termination_b=interfaces[0],
                status=status,
            ),
            Cable.objects.create(
                termination_a=circuit_terminations[1],
                termination_b=interfaces[1],
                status=status,
            ),
        ]

        request = {
            "path": self._get_url("delete", cables[0]),
            "data": post_data({"confirm": True}),
        }

        termination_ct = ContentType.objects.get_for_model(CircuitTermination)
        interface_ct = ContentType.objects.get_for_model(Interface)

        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertFalse(Cable.objects.filter(pk=cables[0].pk).exists())

        # Assert the wrong CablePath did not get deleted
        # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
        # pylint: disable=unsupported-binary-operation
        cable_path_1 = CablePath.objects.filter(
            Q(origin_type=termination_ct, origin_id=circuit_terminations[0].pk)
            | Q(origin_type=interface_ct, origin_id=interfaces[0].pk)
            | Q(
                destination_type=termination_ct,
                destination_id=circuit_terminations[0].pk,
            )
            | Q(destination_type=interface_ct, destination_id=interfaces[0].pk)
        )
        # pylint: enable=unsupported-binary-operation
        self.assertFalse(cable_path_1.exists())

        # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
        # pylint: disable=unsupported-binary-operation
        cable_path_2 = CablePath.objects.filter(
            Q(origin_type=termination_ct, origin_id=circuit_terminations[1].pk)
            | Q(origin_type=interface_ct, origin_id=interfaces[1].pk)
            | Q(
                destination_type=termination_ct,
                destination_id=circuit_terminations[1].pk,
            )
            | Q(destination_type=interface_ct, destination_id=interfaces[1].pk)
        )
        # pylint: enable=unsupported-binary-operation
        self.assertTrue(cable_path_2.exists())


class ConsoleConnectionsTestCase(ViewTestCases.ListObjectsViewTestCase):
    """
    Test the ConsoleConnectionsListView.
    """

    def _get_base_url(self):
        return "dcim:console_connections_{}"

    def _get_queryset(self):
        return ConsolePort.objects.filter(cable__isnull=False)

    def get_list_url(self):
        return "/dcim/console-connections/"

    def get_title(self):
        return "Console Connections"

    def get_list_view(self):
        return ConsoleConnectionsListView

    model = ConsolePort
    filterset = ConsoleConnectionFilterSet

    @classmethod
    def setUpTestData(cls):
        device_1 = create_test_device("Device 1")
        device_2 = create_test_device("Device 2")

        serverports = (
            ConsoleServerPort.objects.create(device=device_2, name="Console Server Port 1"),
            ConsoleServerPort.objects.create(device=device_2, name="Console Server Port 2"),
        )
        rearport = RearPort.objects.create(device=device_2, type=PortTypeChoices.TYPE_8P8C)

        consoleports = (
            ConsolePort.objects.create(device=device_1, name="Console Port 1"),
            ConsolePort.objects.create(device=device_1, name="Console Port 2"),
            ConsolePort.objects.create(device=device_1, name="Console Port 3"),
        )
        status_connected = Status.objects.get(name="Connected")

        Cable.objects.create(
            termination_a=consoleports[0],
            termination_b=serverports[0],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=consoleports[1],
            termination_b=serverports[1],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=consoleports[2],
            termination_b=rearport,
            status=status_connected,
        )


class PowerConnectionsTestCase(ViewTestCases.ListObjectsViewTestCase):
    """
    Test the PowerConnectionsListView.
    """

    def _get_base_url(self):
        return "dcim:power_connections_{}"

    def _get_queryset(self):
        return PowerPort.objects.filter(cable__isnull=False)

    def get_list_url(self):
        return "/dcim/power-connections/"

    def get_title(self):
        return "Power Connections"

    def get_list_view(self):
        return PowerConnectionsListView

    model = PowerPort
    filterset = PowerConnectionFilterSet

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        device_1 = create_test_device("Device 1")
        device_2 = create_test_device("Device 2")

        powerports = (
            PowerPort.objects.create(device=device_1, name="Power Port 1"),
            PowerPort.objects.create(device=device_1, name="Power Port 2"),
            PowerPort.objects.create(device=device_1, name="Power Port 3"),
        )

        poweroutlets = (
            PowerOutlet.objects.create(device=device_2, name="Power Outlet 1", power_port=powerports[0]),
            PowerOutlet.objects.create(device=device_2, name="Power Outlet 2", power_port=powerports[1]),
        )

        powerpanel = PowerPanel.objects.create(location=location, name="Power Panel 1")
        pf_status = Status.objects.get_for_model(PowerFeed).first()
        powerfeed = PowerFeed.objects.create(power_panel=powerpanel, name="Power Feed 1", status=pf_status)

        status_connected = Status.objects.get(name="Connected")

        Cable.objects.create(
            termination_a=powerports[2],
            termination_b=powerfeed,
            status=status_connected,
        )
        # Creating a PowerOutlet with a PowerPort via the ORM does *not* automatically cable the two together. Bug?
        Cable.objects.create(
            termination_a=powerports[0],
            termination_b=poweroutlets[0],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=powerports[1],
            termination_b=poweroutlets[1],
            status=status_connected,
        )


class InterfaceConnectionsTestCase(ViewTestCases.ListObjectsViewTestCase):
    """
    Test the InterfaceConnectionsListView.
    """

    def _get_base_url(self):
        return "dcim:interface_connections_{}"

    def _get_queryset(self):
        return Interface.objects.filter(cable__isnull=False)

    def get_list_url(self):
        return "/dcim/interface-connections/"

    def get_title(self):
        return "Interface Connections"

    def get_list_view(self):
        return InterfaceConnectionsListView

    model = Interface
    filterset = InterfaceConnectionFilterSet

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.first()

        device_1 = create_test_device("Device 1")
        device_2 = create_test_device("Device 2")

        interface_status = Status.objects.get_for_model(Interface).first()
        interface_role = Role.objects.get_for_model(Interface).first()
        cls.interfaces = (
            Interface.objects.create(
                device=device_1,
                name="Interface A1",
                type=InterfaceTypeChoices.TYPE_1GE_SFP,
                status=interface_status,
                role=interface_role,
            ),
            Interface.objects.create(
                device=device_1,
                name="Interface A2",
                type=InterfaceTypeChoices.TYPE_1GE_SFP,
                status=interface_status,
                role=interface_role,
            ),
            Interface.objects.create(
                device=device_1,
                name="Interface A3",
                type=InterfaceTypeChoices.TYPE_1GE_SFP,
                status=interface_status,
            ),
        )

        cls.device_2_interface = Interface.objects.create(
            device=device_2,
            name="Interface A1",
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=interface_status,
            role=interface_role,
        )
        rearport = RearPort.objects.create(device=device_2, type=PortTypeChoices.TYPE_8P8C)

        provider = Provider.objects.first()
        circuittype = CircuitType.objects.first()
        circuit_status = Status.objects.get_for_model(Circuit).first()
        circuit = Circuit.objects.create(
            cid="Circuit 1",
            provider=provider,
            circuit_type=circuittype,
            status=circuit_status,
        )
        circuittermination = CircuitTermination.objects.create(
            circuit=circuit,
            term_side=CircuitTerminationSideChoices.SIDE_A,
            location=location,
        )

        connected = Status.objects.get(name="Connected")

        Cable.objects.create(
            termination_a=cls.interfaces[0],
            termination_b=cls.device_2_interface,
            status=connected,
        )
        Cable.objects.create(
            termination_a=cls.interfaces[1],
            termination_b=circuittermination,
            status=connected,
        )
        Cable.objects.create(termination_a=cls.interfaces[2], termination_b=rearport, status=connected)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_list_objects_filtered(self):
        """Extend base ListObjectsViewTestCase to filter based on *both ends* of a connection."""
        # self.interfaces[0] is cabled to self.device_2_interface, and unfortunately with the way the queryset filtering
        # works at present, we can't guarantee whether filtering on id=interfaces[0] will show it or not.
        instance1, instance2 = self.interfaces[1], self.interfaces[2]
        response = self.client.get(f"{self._get_url('list')}?id={instance1.pk}")
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))
        if hasattr(self.model, "name"):
            self.assertIn(instance1.name, content, msg=content)
            self.assertNotIn(instance2.name, content, msg=content)
        if hasattr(self.model, "get_absolute_url"):
            self.assertIn(instance1.get_absolute_url(), content, msg=content)
            self.assertNotIn(instance2.get_absolute_url(), content, msg=content)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_list_objects_with_constrained_permission(self):
        """
        Extend base GetObjectViewTestCase to have correct permissions for *both ends* of a connection.
        """
        instance1 = self._get_queryset().all()[0]

        # Add object-level permission for the remote end of this connection as well.
        endpoint = instance1.connected_endpoint
        obj_perm = ObjectPermission(
            name="Endpoint test permission",
            constraints={"pk": endpoint.pk},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(endpoint))

        # super().test_list_objects_with_constrained_permission will add permissions for instance1 itself.
        super().test_list_objects_with_constrained_permission()


class VirtualChassisTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VirtualChassis

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()

        cls.devices = [
            Device.objects.create(
                device_type=device_type,
                role=device_role,
                status=device_status,
                name=f"Device {num}",
                location=location,
            )
            for num in range(1, 13)
        ]

        # Create three VirtualChassis with three members each
        vc1 = VirtualChassis.objects.create(name="VC1", master=cls.devices[0], domain="domain-1")
        Device.objects.filter(pk=cls.devices[0].pk).update(virtual_chassis=vc1, vc_position=1)
        Device.objects.filter(pk=cls.devices[1].pk).update(virtual_chassis=vc1, vc_position=2)
        Device.objects.filter(pk=cls.devices[2].pk).update(virtual_chassis=vc1, vc_position=3)
        vc2 = VirtualChassis.objects.create(name="VC2", master=cls.devices[3], domain="domain-2")
        Device.objects.filter(pk=cls.devices[3].pk).update(virtual_chassis=vc2, vc_position=1)
        Device.objects.filter(pk=cls.devices[4].pk).update(virtual_chassis=vc2, vc_position=2)
        Device.objects.filter(pk=cls.devices[5].pk).update(virtual_chassis=vc2, vc_position=3)
        vc3 = VirtualChassis.objects.create(name="VC3", master=cls.devices[6], domain="domain-3")
        Device.objects.filter(pk=cls.devices[6].pk).update(virtual_chassis=vc3, vc_position=1)
        Device.objects.filter(pk=cls.devices[7].pk).update(virtual_chassis=vc3, vc_position=2)
        Device.objects.filter(pk=cls.devices[8].pk).update(virtual_chassis=vc3, vc_position=3)

        cls.form_data = {
            "name": "VC4",
            "domain": "domain-4",
            # Management form data for VC members
            "form-TOTAL_FORMS": 0,
            "form-INITIAL_FORMS": 3,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
        }

        cls.bulk_edit_data = {
            "domain": "domain-x",
        }

    def test_device_interfaces_count_correct(self):
        """
        This checks whether the other memebers' interfaces are included in the
        interfaces tab of the master device and whether the interface count on the tab header is
        rendered correctly.
        """
        self.user.is_superuser = True
        self.user.save()
        interface_status = Status.objects.get_for_model(Interface).first()
        Interface.objects.create(device=self.devices[0], name="eth0", status=interface_status)
        Interface.objects.create(device=self.devices[0], name="eth1", status=interface_status)
        Interface.objects.create(device=self.devices[1], name="device 1 interface 1", status=interface_status)
        Interface.objects.create(device=self.devices[1], name="device 1 interface 2", status=interface_status)
        Interface.objects.create(device=self.devices[2], name="device 2 interface 1", status=interface_status)
        Interface.objects.create(device=self.devices[2], name="device 2 interface 2", status=interface_status)
        response = self.client.get(reverse("dcim:device_interfaces", kwargs={"pk": self.devices[0].pk}))
        self.assertBodyContains(response, 'Interfaces <span class="badge">6</span>')
        self.assertBodyContains(response, "device 1 interface 1")
        self.assertBodyContains(response, "device 1 interface 2")
        self.assertBodyContains(response, "device 2 interface 1")
        self.assertBodyContains(response, "device 2 interface 2")

    def test_device_column_visible(self):
        """
        This checks whether the device column on a device's interfaces
        list is visible if the device is the master in a virtual chassis
        """
        self.user.is_superuser = True
        self.user.save()
        interface_status = Status.objects.get_for_model(Interface).first()
        Interface.objects.create(device=self.devices[0], name="eth0", status=interface_status)
        Interface.objects.create(device=self.devices[0], name="eth1", status=interface_status)
        response = self.client.get(reverse("dcim:device_interfaces", kwargs={"pk": self.devices[0].pk}))
        self.assertBodyContains(response, "<th>Device</th>", html=True)

    def test_device_column_not_visible(self):
        """
        This checks whether the device column on a device's interfaces
        list isn't visible if the device is not the master in a virtual chassis
        """
        self.user.is_superuser = True
        self.user.save()
        interface_status = Status.objects.get_for_model(Interface).first()
        Interface.objects.create(device=self.devices[1], name="eth2", status=interface_status)
        Interface.objects.create(device=self.devices[1], name="eth3", status=interface_status)
        response = self.client.get(reverse("dcim:device_interfaces", kwargs={"pk": self.devices[1].pk}))
        self.assertNotIn("<th >Device</th>", extract_page_body(response.content.decode(response.charset)))
        # Sanity check:
        self.assertBodyContains(response, "<th>Name</th>", html=True)


class PowerPanelTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = PowerPanel

    @classmethod
    def setUpTestData(cls):
        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]
        rackgroups = (
            RackGroup.objects.create(name="Rack Group 1", location=locations[0]),
            RackGroup.objects.create(name="Rack Group 2", location=locations[1]),
        )

        PowerPanel.objects.create(location=locations[0], rack_group=rackgroups[0], name="Power Panel 1")
        PowerPanel.objects.create(location=locations[0], rack_group=rackgroups[0], name="Power Panel 2")
        PowerPanel.objects.create(location=locations[0], rack_group=rackgroups[0], name="Power Panel 3")

        cls.form_data = {
            "location": locations[1].pk,
            "rack_group": rackgroups[1].pk,
            "name": "Power Panel X",
            "tags": [t.pk for t in Tag.objects.get_for_model(PowerPanel)],
        }

        cls.bulk_edit_data = {
            "location": locations[1].pk,
            "rack_group": rackgroups[1].pk,
        }


class PowerFeedTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = PowerFeed

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        # Assign location generated to the class object for use later.
        cls.location = location

        powerpanels = (
            PowerPanel.objects.create(location=location, name="Power Panel 1"),
            PowerPanel.objects.create(location=location, name="Power Panel 2"),
        )

        # Assign power panels generated to the class object for use later.
        cls.powerpanels = powerpanels

        rack_status = Status.objects.get_for_model(Rack).first()
        racks = (
            Rack.objects.create(location=location, name="Rack 1", status=rack_status),
            Rack.objects.create(location=location, name="Rack 2", status=rack_status),
        )

        statuses = Status.objects.get_for_model(PowerFeed)
        cls.status = statuses
        status_planned = statuses[0]

        powerfeed_1 = PowerFeed.objects.create(
            name="Power Feed 1",
            power_panel=powerpanels[0],
            rack=racks[0],
            status=status_planned,
        )
        powerfeed_2 = PowerFeed.objects.create(
            name="Power Feed 2",
            power_panel=powerpanels[0],
            rack=racks[0],
            status=status_planned,
        )
        PowerFeed.objects.create(
            name="Power Feed 3",
            power_panel=powerpanels[0],
            rack=racks[0],
            status=status_planned,
        )

        # Assign power feeds for the tests later
        cls.powerfeeds = (powerfeed_1, powerfeed_2)

        cls.form_data = {
            "name": "Power Feed X",
            "power_panel": powerpanels[1].pk,
            "rack": racks[1].pk,
            "status": status_planned.pk,
            "type": PowerFeedTypeChoices.TYPE_REDUNDANT,
            "supply": PowerFeedSupplyChoices.SUPPLY_DC,
            "phase": PowerFeedPhaseChoices.PHASE_3PHASE,
            "voltage": 100,
            "amperage": 100,
            "max_utilization": 50,
            "comments": "New comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(PowerFeed)],
        }

        cls.bulk_edit_data = {
            "power_panel": powerpanels[1].pk,
            "rack": racks[1].pk,
            "status": status_planned.pk,
            "type": PowerFeedTypeChoices.TYPE_REDUNDANT,
            "supply": PowerFeedSupplyChoices.SUPPLY_DC,
            "phase": PowerFeedPhaseChoices.PHASE_3PHASE,
            "voltage": 100,
            "amperage": 100,
            "max_utilization": 50,
            "comments": "New comments",
        }

    def test_power_feed_detail(self):
        self.add_permissions("dcim.view_powerfeed")
        # Setup base device info
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        device = Device.objects.create(
            device_type=device_type,
            role=device_role,
            status=device_status,
            name="Device1",
            location=self.location,
        )

        powerport = PowerPort.objects.create(device=device, name="Power Port 1")

        powerfeed = self.powerfeeds[0]

        Cable.objects.create(
            termination_a=powerport,
            termination_b=powerfeed,
            status=Status.objects.get(name="Connected"),
        )

        url = reverse("dcim:powerfeed", kwargs={"pk": powerfeed.pk})
        self.assertHttpStatus(self.client.get(url), 200)


class PathTraceViewTestCase(ModelViewTestCase):
    def test_get_cable_path_trace_do_not_throw_error(self):
        """
        Assert selecting a related path in cable trace view loads successfully.

        (https://github.com/nautobot/nautobot/issues/1741)
        """
        self.add_permissions("dcim.view_cable", "dcim.view_rearport")
        active = Status.objects.get(name="Active")
        connected = Status.objects.get(name="Connected")
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        location_type = LocationType.objects.get(name="Campus")
        location = Location.objects.create(location_type=location_type, name="Location 1", status=active)
        device = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="Device 1",
            location=location,
            status=active,
        )
        obj = RearPort.objects.create(device=device, name="Rear Port 1", type=PortTypeChoices.TYPE_8P8C)
        peer_obj = Interface.objects.create(device=device, name="eth0", status=active)
        Cable.objects.create(termination_a=obj, termination_b=peer_obj, label="Cable 1", status=connected)

        url = reverse("dcim:rearport_trace", args=[obj.pk])
        cablepath_id = CablePath.objects.first().id
        response = self.client.get(url + f"?cablepath_id={cablepath_id}")
        self.assertBodyContains(response, "<h1>Cable Trace for Rear Port Rear Port 1</h1>", html=True)


class DeviceRedundancyGroupTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = DeviceRedundancyGroup

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(DeviceRedundancyGroup)

        cls.form_data = {
            "name": "DRG χ",
            "failover_strategy": DeviceRedundancyGroupFailoverStrategyChoices.FAILOVER_ACTIVE_PASSIVE,
            "status": statuses[3].pk,
            "local_config_context_data": None,
        }

        cls.bulk_edit_data = {
            "failover_strategy": DeviceRedundancyGroupFailoverStrategyChoices.FAILOVER_ACTIVE_PASSIVE,
            "status": statuses[0].pk,
        }


class InterfaceRedundancyGroupTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = InterfaceRedundancyGroup

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(InterfaceRedundancyGroup)
        cls.ips = IPAddress.objects.all()
        cls.secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
            SecretsGroup.objects.create(name="Secrets Group 3"),
        )

        cls.interface_redundancy_groups = (
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 1",
                protocol="hsrp",
                status=statuses[0],
                virtual_ip=None,
                secrets_group=cls.secrets_groups[0],
                protocol_group_id="1",
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 2",
                protocol="carp",
                status=statuses[1],
                virtual_ip=cls.ips[1],
                secrets_group=cls.secrets_groups[1],
                protocol_group_id="2",
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 3",
                protocol="vrrp",
                status=statuses[2],
                virtual_ip=cls.ips[2],
                secrets_group=None,
                protocol_group_id="3",
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 4",
                protocol="glbp",
                status=statuses[3],
                virtual_ip=cls.ips[3],
                secrets_group=cls.secrets_groups[2],
            ),
        )

        for group in cls.interface_redundancy_groups:
            group.validated_save()

        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]

        devicetypes = DeviceType.objects.all()[:2]

        deviceroles = Role.objects.get_for_model(Device)[:2]

        device_statuses = Status.objects.get_for_model(Device)
        status_active = device_statuses[0]
        device = Device.objects.create(
            name="Device 1",
            location=locations[0],
            device_type=devicetypes[0],
            role=deviceroles[0],
            status=status_active,
        )
        intf_status = Status.objects.get_for_model(Interface).first()
        intf_role = Role.objects.get_for_model(Interface).first()
        cls.interfaces = (
            Interface.objects.create(device=device, name="Interface A1", status=intf_status, role=intf_role),
            Interface.objects.create(device=device, name="Interface A2", status=intf_status),
            Interface.objects.create(device=device, name="Interface A3", status=intf_status, role=intf_role),
        )

        cls.form_data = {
            "name": "IRG χ",
            "protocol": InterfaceRedundancyGroupProtocolChoices.GLBP,
            "status": statuses[3].pk,
        }
        cls.interface_add_form_data = {
            "interface_redundancy_group": cls.interface_redundancy_groups[0].pk,
            "interface": cls.interfaces[0].pk,
            "priority": 100,
        }

        cls.bulk_edit_data = {
            "protocol": InterfaceRedundancyGroupProtocolChoices.HSRP,
            "status": statuses[0].pk,
            "virtual_ip": cls.ips[0].pk,
            "secrets_group": cls.secrets_groups[1].pk,
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_adding_interfaces_to_group(self):
        initial_count = InterfaceRedundancyGroupAssociation.objects.all().count()

        # Assign unconstrained permission
        self.add_permissions("dcim.add_interfaceredundancygroupassociation")
        return_url = reverse(
            "dcim:interfaceredundancygroup",
            kwargs={"pk": self.interface_redundancy_groups[0].pk},
        )
        url = reverse("dcim:interfaceredundancygroupassociation_add")
        url = url + f"?interface_redundancy_group={self.interface_redundancy_groups[0].pk}&return_url={return_url}"
        self.assertHttpStatus(self.client.get(url), 200)

        # Try POST with model-level permission
        request = {
            "path": url,
            "data": post_data(self.interface_add_form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(initial_count + 1, InterfaceRedundancyGroupAssociation.objects.all().count())
        self.interface_add_form_data["interface"] = self.interfaces[1]
        request = {
            "path": url,
            "data": post_data(self.interface_add_form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(initial_count + 2, InterfaceRedundancyGroupAssociation.objects.all().count())


class SoftwareImageFileTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SoftwareImageFile
    filterset = SoftwareImageFileFilterSet
    custom_action_required_permissions = {
        "dcim:softwareimagefile_devices": ["dcim.view_softwareimagefile", "dcim.view_device"],
        "dcim:softwareimagefile_device_types": ["dcim.view_softwareimagefile", "dcim.view_devicetype"],
        "dcim:softwareimagefile_virtual_machines": [
            "dcim.view_softwareimagefile",
            "virtualization.view_virtualmachine",
        ],
        "dcim:softwareimagefile_inventory_items": ["dcim.view_softwareimagefile", "dcim.view_inventoryitem"],
    }

    @classmethod
    def setUpTestData(cls):
        device_types = DeviceType.objects.all()[:2]
        statuses = Status.objects.get_for_model(SoftwareImageFile)
        software_versions = SoftwareVersion.objects.all()
        external_integration = ExternalIntegration.objects.first()

        cls.form_data = {
            "software_version": software_versions[0].pk,
            "image_file_name": "software_image_file_test_case.bin",
            "status": statuses[0].pk,
            "image_file_checksum": "abcdef1234567890",
            "image_file_size": 1234567890,
            "hashing_algorithm": SoftwareImageFileHashingAlgorithmChoices.SHA512,
            "download_url": "https://example.com/software_image_file_test_case.bin",
            "external_integration": external_integration.pk,
            "device_types": [device_types[0].pk, device_types[1].pk],
        }

        cls.bulk_edit_data = {
            "software_version": software_versions[0].pk,
            "status": statuses[0].pk,
            "image_file_checksum": "abcdef1234567890",
            "hashing_algorithm": SoftwareImageFileHashingAlgorithmChoices.SHA512,
            "image_file_size": 1234567890,
            "download_url": "https://example.com/software_image_file_test_case.bin",
            "external_integration": external_integration.pk,
        }


class SoftwareVersionTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SoftwareVersion
    filterset = SoftwareVersionFilterSet

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(SoftwareVersion)
        platforms = Platform.objects.all()

        # Protected FK to SoftwareImageFile prevents deletion
        DeviceTypeToSoftwareImageFile.objects.all().delete()
        # Protected FK to SoftwareVersion prevents deletion
        Device.objects.all().update(software_version=None)

        cls.form_data = {
            "platform": platforms[0].pk,
            "version": "1.0.0",
            "status": statuses[0].pk,
            "alias": "Version 1.0.0",
            "release_date": datetime.date(2001, 1, 1),
            "end_of_support_date": datetime.date(2005, 1, 1),
            "documentation_url": "https://example.com/software_version_test_case",
            "long_term_support": True,
            "pre_release": False,
        }

        cls.bulk_edit_data = {
            "platform": platforms[0].pk,
            "status": statuses[0].pk,
            "alias": "Version x.y.z",
            "release_date": datetime.date(2001, 12, 31),
            "end_of_support_date": datetime.date(2005, 12, 31),
            "documentation_url": "https://example.com/software_version_test_case/docs2",
            "long_term_support": False,
            "pre_release": True,
        }


class ControllerTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Controller
    filterset = ControllerFilterSet
    custom_action_required_permissions = {
        "dcim:controller_wirelessnetworks": [
            "dcim.view_controller",
            "wireless.view_controllermanageddevicegroupwirelessnetworkassignment",
        ],
    }

    @classmethod
    def setUpTestData(cls):
        device = Device.objects.first()
        external_integration = ExternalIntegration.objects.first()
        location = Location.objects.get_for_model(Controller).first()
        platform = Platform.objects.first()
        role = Role.objects.get_for_model(Controller).first()
        status = Status.objects.get_for_model(Controller).first()
        tenant = Tenant.objects.first()

        cls.form_data = {
            "controller_device": device.pk,
            "description": "Controller 1 description",
            "external_integration": external_integration.pk,
            "location": location.pk,
            "name": "Controller 1",
            "platform": platform.pk,
            "role": role.pk,
            "status": status.pk,
            "tenant": tenant.pk,
        }

        cls.bulk_edit_data = {
            "external_integration": external_integration.pk,
            "location": location.pk,
            "platform": platform.pk,
            "role": role.pk,
            "status": status.pk,
            "tenant": tenant.pk,
        }


class ControllerManagedDeviceGroupTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = ControllerManagedDeviceGroup
    filterset = ControllerManagedDeviceGroupFilterSet
    custom_action_required_permissions = {
        "dcim:controllermanageddevicegroup_wireless_networks": [
            "dcim.view_controllermanageddevicegroup",
            "wireless.view_controllermanageddevicegroupwirelessnetworkassignment",
        ],
        "dcim:controllermanageddevicegroup_radio_profiles": [
            "dcim.view_controllermanageddevicegroup",
            "wireless.view_radioprofile",
        ],
    }

    @classmethod
    def setUpTestData(cls):
        controllers = Controller.objects.all()

        cls.form_data = {
            "name": "Managed Device Group 10",
            "controller": controllers[0].pk,
            "weight": 100,
            "devices": [item.pk for item in Device.objects.all()[:2]],
            # Management form fields required for the dynamic Wireless Network formset
            "wireless_network_assignments-TOTAL_FORMS": "0",
            "wireless_network_assignments-INITIAL_FORMS": "1",
            "wireless_network_assignments-MIN_NUM_FORMS": "0",
            "wireless_network_assignments-MAX_NUM_FORMS": "1000",
        }

        cls.bulk_edit_data = {
            "weight": 300,
        }


class VirtualDeviceContextTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VirtualDeviceContext
    filterset = VirtualDeviceContextFilterSet

    @classmethod
    def setUpTestData(cls):
        devices = Device.objects.filter(interfaces__isnull=False)
        vdc_status = Status.objects.get_for_model(VirtualDeviceContext)[0]
        tenants = Tenant.objects.all()

        cls.form_data = {
            "name": "Virtual Device Context 1",
            "device": devices[0].pk,
            "identifier": 100,
            "status": vdc_status.pk,
            "tenant": tenants[0].pk,
            "interfaces": [interface.pk for interface in devices[0].all_interfaces[:3]],
            "description": "Sample Description",
        }

        cls.update_data = {
            "name": "Virtual Device Context 3",
            "tenant": tenants[3].pk,
            "status": vdc_status.pk,
        }

        cls.bulk_edit_data = {
            "tenant": tenants[1].pk,
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_update_vdc_primary_ips(self):
        """Test assigning a primary IP to a virtual device context."""
        self.add_permissions("dcim.change_virtualdevicecontext")
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

        form_data = self.form_data.copy()
        form_data["device"] = vdc.device
        form_data["interfaces"] = [interface.pk]
        form_data["primary_ip4"] = ip_v4.pk
        form_data["primary_ip6"] = ip_v6.pk
        # Assert that update succeeds.
        request = {
            "path": self._get_url("edit", vdc),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        vdc.refresh_from_db()
        self.assertEqual(vdc.primary_ip6, ip_v6)
        self.assertEqual(vdc.primary_ip4, ip_v4)


class ModuleFamilyTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    """Test cases for ModuleFamily views."""

    model = ModuleFamily

    @classmethod
    def setUpTestData(cls):
        """Create test data for ModuleFamily views."""
        ModuleFamily.objects.create(name="Module Family 1", description="First Module Family")
        ModuleFamily.objects.create(name="Module Family 2", description="Second Module Family")
        ModuleFamily.objects.create(name="Module Family 3", description="Third Module Family")

        cls.form_data = {
            "name": "Module Family X",
            "description": "A new module family",
        }

        cls.csv_data = (
            "name,description",
            "Module Family 4,Fourth Module Family",
            "Module Family 5,Fifth Module Family",
            "Module Family 6,Sixth Module Family",
        )

        cls.bulk_edit_data = {
            "description": "Modified description",
        }
