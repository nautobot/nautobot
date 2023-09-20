from decimal import Decimal
import unittest

import pytz
import yaml

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.test import override_settings
from django.urls import reverse
from netaddr import EUI

from nautobot.circuits.choices import CircuitTerminationSideChoices
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.core.testing import ViewTestCases, extract_page_body, ModelViewTestCase, post_data
from nautobot.core.testing.utils import generate_random_device_asset_tag_of_specified_size
from nautobot.dcim.choices import (
    CableLengthUnitChoices,
    CableTypeChoices,
    ConsolePortTypeChoices,
    DeviceFaceChoices,
    DeviceRedundancyGroupFailoverStrategyChoices,
    InterfaceModeChoices,
    InterfaceRedundancyGroupProtocolChoices,
    InterfaceTypeChoices,
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
    SubdeviceRoleChoices,
)
from nautobot.dcim.filters import ConsoleConnectionFilterSet, InterfaceConnectionFilterSet, PowerConnectionFilterSet
from nautobot.dcim.models import (
    Cable,
    CablePath,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceRedundancyGroup,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    InterfaceRedundancyGroup,
    Manufacturer,
    InventoryItem,
    Location,
    LocationType,
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
    RearPort,
    RearPortTemplate,
    VirtualChassis,
)
from nautobot.extras.choices import CustomFieldTypeChoices, RelationshipTypeChoices
from nautobot.extras.models import (
    ConfigContextSchema,
    CustomField,
    CustomFieldChoice,
    Relationship,
    RelationshipAssociation,
    Role,
    SecretsGroup,
    Status,
    Tag,
)
from nautobot.ipam.choices import IPAddressTypeChoices
from nautobot.ipam.models import IPAddress, Namespace, Prefix, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.users.models import ObjectPermission

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
        name=name, location=location, device_type=devicetype, role=devicerole, status=devicestatus
    )

    return device


class LocationTypeTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = LocationType

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
            lt.validated_save()
            lt.content_types.add(ContentType.objects.get_for_model(RackGroup))
        # Deletable Location Types
        LocationType.objects.create(name="Delete Me 1")
        LocationType.objects.create(name="Delete Me 2")
        LocationType.objects.create(name="Delete Me 3")

        # Similarly, EditObjectViewTestCase expects to be able to change lt1 with the below form_data,
        # so we need to make sure we're not trying to introduce a reference loop to the LocationType tree...
        cls.form_data = {
            "name": "Intermediate 2",
            # "parent": lt1.pk, # TODO: Either overload how EditObjectViewTestCase finds an editable object or write a specific test case for this.
            "description": "Another intermediate type",
            "content_types": [ContentType.objects.get_for_model(Rack).pk, ContentType.objects.get_for_model(Device).pk],
            "nestable": True,
        }

        cls.csv_data = (
            "name,parent,description,content_types,nestable",
            # Import understands foreign-keys provided as either a composite-key (for LocationType, this is .name)...
            f"Intermediate 3,{lt1.name},Another intermediate type,ipam.prefix,false",
            # ... or as a PK value
            f'Intermediate 4,{lt1.pk},Another intermediate type,"ipam.prefix,dcim.device",false',
            "Root 3,,Another root type,,true",
        )

    def _get_queryset(self):
        return super()._get_queryset().order_by("last_updated")


class LocationTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Location

    @classmethod
    def setUpTestData(cls):
        lt1 = LocationType.objects.get(name="Campus")
        lt2 = LocationType.objects.get(name="Building")
        lt3 = LocationType.objects.get(name="Floor")
        for lt in [lt1, lt2, lt3]:
            lt.validated_save()

        status = Status.objects.get_for_model(Location).first()
        tenant = Tenant.objects.first()

        loc1 = Location.objects.create(name="Root 1", location_type=lt1, status=status)
        loc2 = Location.objects.create(name="Root 2", location_type=lt1, status=status, tenant=tenant)
        loc3 = Location.objects.create(name="Intermediate 1", location_type=lt2, parent=loc2, status=status)
        loc4 = Location.objects.create(name="Leaf 1", location_type=lt3, parent=loc3, status=status, description="Hi!")
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
            "time_zone": pytz.UTC,
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

        cls.csv_data = (
            "name,location_type,parent,status,tenant,description",
            # Mix and match composite keys and PKs to confirm that the serializer handles both correctly
            f'Root 3,"{lt1.name}",,{status.name},,',
            f'Intermediate 2,"{lt2.pk}",{loc2.composite_key},{status.pk},"{tenant.name}",Hello world!',
            f'Leaf 2,"{lt3.name}",{loc3.pk},{status.name},"{tenant.name}",',
        )

        cls.bulk_edit_data = {
            "description": "A generic description",
            # Because we have a mix of root and non-root LocationTypes,
            # we can't bulk-edit the parent in this generic test
            "tenant": tenant.pk,
            "status": Status.objects.get_for_model(Location).last().pk,
            "asn": 65009,
            "time_zone": pytz.timezone("US/Eastern"),
        }


class RackGroupTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = RackGroup

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        RackGroup.objects.create(name="Rack Group 1", location=location)
        RackGroup.objects.create(name="Rack Group 2", location=location)
        RackGroup.objects.create(name="Rack Group 3", location=location)
        RackGroup.objects.create(name="Rack Group 8", location=location)

        cls.form_data = {
            "name": "Rack Group X",
            "location": location.pk,
            "description": "A new rack group",
        }

        cls.csv_data = (
            "location,name,description",
            f"{location.composite_key},Rack Group 4,Fourth rack group",
            f"{location.pk},Rack Group 5,Fifth rack group",
            f"{location.composite_key},Rack Group 6,Sixth rack group",
            f"{location.pk},Rack Group 7,Seventh rack group",
        )


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

        cls.csv_data = (
            "rack,units,description",
            f'{rack.composite_key},"10,11,12",Reservation 1',
            f"{rack.pk},13,Reservation 2",
            f'{rack.composite_key},"16,17,18",Reservation 3',
        )

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
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_MULTISELECT, label="Rack Colors", default=[]),
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
                relationship=cls.relationships[0], source=rack, destination=cls.locations[1]
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

        cls.csv_data = (
            "location,rack_group,name,width,u_height,status",
            f"{cls.locations[0].composite_key},,Rack 4,19,42,{statuses[0].name}",
            f"{cls.locations[0].pk},{rackgroups[0].composite_key},Rack 5,19,42,{statuses[1].name}",
            f"{cls.locations[1].composite_key},{rackgroups[1].pk},Rack 6,19,42,{statuses[2].pk}",
        )

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
        cable1 = Cable(termination_a=powerfeed1, termination_b=powerport1, status=self.cable_connected)
        cable1.save()

        # Create power port for 2nd device
        powerport2 = PowerPort.objects.create(device=devices[1], name="Power Port 12", allocated_draw=1200)

        # Connect power port to power outlet (dev1)
        cable2 = Cable(termination_a=powerport2, termination_b=poweroutlet1, status=self.cable_connected)
        cable2.save()

        # Create another power port for 2nd device and directly connect to the second PowerFeed.
        powerport3 = PowerPort.objects.create(device=devices[1], name="Power Port 13", allocated_draw=2400)
        cable3 = Cable(termination_a=powerfeed2, termination_b=powerport3, status=self.cable_connected)
        cable3.save()

        # Test the view
        response = self.client.get(reverse("dcim:rack", args=[self.racks[0].pk]))
        self.assertHttpStatus(response, 200)
        # Validate Power Utilization for PowerFeed 11 is displaying correctly on Rack View.
        power_feed_11_html = """
        <td><div title="Used: 1200&#13;Count: 3840" class="progress text-center">
            <div class="progress-bar progress-bar-success"
                role="progressbar" aria-valuenow="31" aria-valuemin="0" aria-valuemax="100" style="width: 31%">
                31%
            </div>
        </div></td>
        """
        self.assertContains(response, power_feed_11_html, html=True)
        # Validate Power Utilization for PowerFeed12 is displaying correctly on Rack View.
        power_feed_12_html = """
        <td><div title="Used: 2400&#13;Count: 3840" class="progress text-center">
            <div class="progress-bar progress-bar-success"
                role="progressbar" aria-valuenow="62" aria-valuemin="0" aria-valuemax="100" style="width: 62%">
                62%
            </div>
        </div></td>
        """
        self.assertContains(response, power_feed_12_html, html=True)
        # Validate Rack Power Utilization for Combined powerfeeds is displaying correctly on the Rack View
        total_utilization_html = """
        <td><div title="Used: 3600&#13;Count: 7680" class="progress text-center">
            <div class="progress-bar progress-bar-success"
                role="progressbar" aria-valuenow="46" aria-valuemin="0" aria-valuemax="100" style="width: 46%">
                46%
            </div>
        </div></td>
        """
        self.assertContains(response, total_utilization_html, html=True)


class ManufacturerTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = Manufacturer

    @classmethod
    def setUpTestData(cls):
        # FIXME(jathan): This has to be replaced with# `get_deletable_object` and
        # `get_deletable_object_pks` but this is a workaround just so all of these objects are
        # deletable for now.
        DeviceType.objects.all().delete()
        Platform.objects.all().delete()

        cls.form_data = {
            "name": "Manufacturer X",
            "description": "A new manufacturer",
        }
        cls.csv_data = (
            "name,description",
            "Manufacturer 4,Fourth manufacturer",
            "Manufacturer 5,Fifth manufacturer",
            "Manufacturer 6,Sixth manufacturer",
            "Manufacturer 7,Seventh manufacturer",
        )


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
        manufacturers = Manufacturer.objects.all()[:2]

        DeviceType.objects.create(model="Test Device Type 1", manufacturer=manufacturers[0])
        DeviceType.objects.create(model="Test Device Type 2", manufacturer=manufacturers[0])
        DeviceType.objects.create(model="Test Device Type 3", manufacturer=manufacturers[0])
        DeviceType.objects.create(model="Test Device Type 4", manufacturer=manufacturers[1])

        cls.form_data = {
            "manufacturer": manufacturers[1].pk,
            "model": "Device Type X",
            "part_number": "123ABC",
            "u_height": 2,
            "is_full_depth": True,
            "subdevice_role": "",  # CharField
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(DeviceType)],
        }

        cls.bulk_edit_data = {
            "manufacturer": manufacturers[1].pk,
            "u_height": 3,
            "is_full_depth": False,
        }

    # Temporary FIXME(jathan): Literally just trying to get the tests running so
    # we can keep moving on the fixture factories. This should be removed once
    # we've cleaned up all the hard-coded object comparisons and are all in on
    # factories.
    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_bulk_edit_objects_with_constrained_permission(self):
        DeviceType.objects.exclude(model__startswith="Test Device Type").delete()
        super().test_bulk_edit_objects_with_constrained_permission()

    # Temporary FIXME(jathan): Literally just trying to get the tests running so
    # we can keep moving on the fixture factories. This should be removed once
    # we've cleaned up all the hard-coded object comparisons and are all in on
    # factories.
    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_bulk_edit_objects_with_permission(self):
        DeviceType.objects.exclude(model__startswith="Test Device Type").delete()
        super().test_bulk_edit_objects_with_permission()

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
"""

        # Create the manufacturer
        Manufacturer.objects.first()

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
        )

        form_data = {"data": IMPORT_DATA, "format": "yaml"}
        response = self.client.post(reverse("dcim:devicetype_import"), data=form_data, follow=True)
        self.assertHttpStatus(response, 200)

        dt = DeviceType.objects.get(model="TEST-1000")
        self.assertEqual(dt.comments, "test comment")

        # Verify all of the components were created
        self.assertEqual(dt.console_port_templates.count(), 3)
        cp1 = ConsolePortTemplate.objects.first()
        self.assertEqual(cp1.name, "Console Port 1")
        self.assertEqual(cp1.type, ConsolePortTypeChoices.TYPE_DE9)

        self.assertEqual(dt.console_server_port_templates.count(), 3)
        csp1 = ConsoleServerPortTemplate.objects.first()
        self.assertEqual(csp1.name, "Console Server Port 1")
        self.assertEqual(csp1.type, ConsolePortTypeChoices.TYPE_RJ45)

        self.assertEqual(dt.power_port_templates.count(), 3)
        pp1 = PowerPortTemplate.objects.first()
        self.assertEqual(pp1.name, "Power Port 1")
        self.assertEqual(pp1.type, PowerPortTypeChoices.TYPE_IEC_C14)

        self.assertEqual(dt.power_outlet_templates.count(), 3)
        po1 = PowerOutletTemplate.objects.first()
        self.assertEqual(po1.name, "Power Outlet 1")
        self.assertEqual(po1.type, PowerOutletTypeChoices.TYPE_IEC_C13)
        self.assertEqual(po1.power_port_template, pp1)
        self.assertEqual(po1.feed_leg, PowerOutletFeedLegChoices.FEED_LEG_A)

        self.assertEqual(dt.interface_templates.count(), 3)
        iface1 = InterfaceTemplate.objects.first()
        self.assertEqual(iface1.name, "Interface 1")
        self.assertEqual(iface1.type, InterfaceTypeChoices.TYPE_1GE_FIXED)
        self.assertTrue(iface1.mgmt_only)

        self.assertEqual(dt.rear_port_templates.count(), 3)
        rp1 = RearPortTemplate.objects.first()
        self.assertEqual(rp1.name, "Rear Port 1")

        self.assertEqual(dt.front_port_templates.count(), 3)
        fp1 = FrontPortTemplate.objects.first()
        self.assertEqual(fp1.name, "Front Port 1")
        self.assertEqual(fp1.rear_port_template, rp1)
        self.assertEqual(fp1.rear_port_position, 1)

        self.assertEqual(dt.device_bay_templates.count(), 3)
        db1 = DeviceBayTemplate.objects.first()
        self.assertEqual(db1.name, "Device Bay 1")

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
        self.assertHttpStatus(response, 302)
        for instance in self._get_queryset().filter(pk__in=pk_list):
            self.assertEqual(instance.u_height, data["u_height"])

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
        self.assertHttpStatus(response, 200)
        self.assertIn("failed validation", response.content.decode(response.charset))


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
            "type": ConsolePortTypeChoices.TYPE_RJ45,
        }

        cls.bulk_edit_data = {
            "type": ConsolePortTypeChoices.TYPE_RJ45,
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
            "type": ConsolePortTypeChoices.TYPE_RJ45,
        }

        cls.bulk_edit_data = {
            "type": ConsolePortTypeChoices.TYPE_RJ45,
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
        }

        cls.bulk_create_data = {
            "device_type": devicetypes[1].pk,
            "name_pattern": "Power Port Template [4-6]",
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
        }

        cls.bulk_edit_data = {
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
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
            "type": PowerOutletTypeChoices.TYPE_IEC_C13,
            "power_port_template": powerports[0].pk,
            "feed_leg": PowerOutletFeedLegChoices.FEED_LEG_B,
        }

        cls.bulk_edit_data = {
            "type": PowerOutletTypeChoices.TYPE_IEC_C13,
            "feed_leg": PowerOutletFeedLegChoices.FEED_LEG_B,
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

        InterfaceTemplate.objects.create(device_type=devicetypes[0], name="Interface Template 1")
        InterfaceTemplate.objects.create(device_type=devicetypes[0], name="Interface Template 2")
        InterfaceTemplate.objects.create(device_type=devicetypes[0], name="Interface Template 3")

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
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "mgmt_only": True,
        }

        cls.bulk_edit_data = {
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "mgmt_only": True,
        }


class FrontPortTemplateTestCase(ViewTestCases.DeviceComponentTemplateViewTestCase):
    model = FrontPortTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")

        rearports = (
            RearPortTemplate.objects.create(device_type=devicetype, name="Rear Port Template 1"),
            RearPortTemplate.objects.create(device_type=devicetype, name="Rear Port Template 2"),
            RearPortTemplate.objects.create(device_type=devicetype, name="Rear Port Template 3"),
            RearPortTemplate.objects.create(device_type=devicetype, name="Rear Port Template 4"),
            RearPortTemplate.objects.create(device_type=devicetype, name="Rear Port Template 5"),
            RearPortTemplate.objects.create(device_type=devicetype, name="Rear Port Template 6"),
        )

        FrontPortTemplate.objects.create(
            device_type=devicetype,
            name="Front Port Template 1",
            rear_port_template=rearports[0],
            rear_port_position=1,
        )
        FrontPortTemplate.objects.create(
            device_type=devicetype,
            name="Front Port Template 2",
            rear_port_template=rearports[1],
            rear_port_position=1,
        )
        FrontPortTemplate.objects.create(
            device_type=devicetype,
            name="Front Port Template 3",
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
            "name_pattern": "Front Port [4-6]",
            "type": PortTypeChoices.TYPE_8P8C,
            "rear_port_template_set": [f"{rp.pk}:1" for rp in rearports[3:6]],
        }

        cls.bulk_edit_data = {
            "type": PortTypeChoices.TYPE_8P8C,
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

        RearPortTemplate.objects.create(device_type=devicetypes[0], name="Rear Port Template 1")
        RearPortTemplate.objects.create(device_type=devicetypes[0], name="Rear Port Template 2")
        RearPortTemplate.objects.create(device_type=devicetypes[0], name="Rear Port Template 3")

        cls.form_data = {
            "device_type": devicetypes[1].pk,
            "name": "Rear Port Template X",
            "type": PortTypeChoices.TYPE_8P8C,
            "positions": 2,
        }

        cls.bulk_create_data = {
            "device_type": devicetypes[1].pk,
            "name_pattern": "Rear Port Template [4-6]",
            "type": PortTypeChoices.TYPE_8P8C,
            "positions": 2,
        }

        cls.bulk_edit_data = {
            "type": PortTypeChoices.TYPE_8P8C,
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
        }

        cls.bulk_edit_data = {
            "description": "Foo bar",
        }


class PlatformTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = Platform

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()

        cls.form_data = {
            "name": "Platform X",
            "manufacturer": manufacturer.pk,
            "napalm_driver": "junos",
            "napalm_args": None,
            "network_driver": "juniper_junos",
            "description": "A new platform",
        }

        cls.csv_data = (
            "name,description",
            "Platform 4,Fourth platform",
            "Platform 5,Fifth platform",
            "Platform 6,Sixth platform",
            "Platform 7,Seventh platform",
        )


class DeviceTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Device

    @classmethod
    def setUpTestData(cls):
        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]

        rack_group = RackGroup.objects.create(location=locations[0], name="Rack Group 1")

        rack_status = Status.objects.get_for_model(Rack).first()
        racks = (
            Rack.objects.create(name="Rack 1", location=locations[0], rack_group=rack_group, status=rack_status),
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

        cls.custom_fields = (
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_INTEGER, label="Crash Counter", default=0),
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

        device_bay = DeviceBay.objects.create(device=devices[0], name="Device Bay 1")

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

        cls.interfaces = (
            Interface.objects.create(device=devices[0], name="Interface 1", status=intf_status),
            Interface.objects.create(device=devices[0], name="Interface 2", status=intf_status),
            Interface.objects.create(device=devices[0], name="Interface 3", status=intf_status),
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
        }

        cls.csv_data = (
            "role,device_type,status,name,location,rack,position,face,secrets_group,parent_bay",
            f"{deviceroles[0].name},{devicetypes[0].composite_key},{statuses[0].name},Device 4,{locations[0].name},{racks[0].composite_key},10,front,",
            f"{deviceroles[0].pk},{devicetypes[0].pk},{statuses[0].pk},Device 5,{locations[0].pk},{racks[0].pk},20,front,",
            f"{deviceroles[0].name},{devicetypes[0].composite_key},{statuses[0].name},Device 6,{locations[0].name},{racks[0].composite_key},30,front,Secrets Group 2",
            f"{deviceroles[1].name},{devicetypes[1].composite_key},{statuses[0].name},Child Device,{locations[0].name},,,,,{device_bay.composite_key}",
        )

        cls.bulk_edit_data = {
            "device_type": devicetypes[1].pk,
            "role": deviceroles[1].pk,
            "tenant": None,
            "platform": platforms[1].pk,
            "serial": "VMWARE-XX XX XX XX XX XX XX XX-XX XX XX XX XX XX XX XX",
            "status": statuses[2].pk,
            "location": locations[1].pk,
            "rack": racks[1].pk,
            "position": None,
            "face": DeviceFaceChoices.FACE_FRONT,
            "secrets_group": secrets_groups[1].pk,
        }

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
        device = Device.objects.first()
        self.add_permissions("ipam.add_ipaddress", "dcim.change_interface")

        url = reverse("dcim:device_interfaces", kwargs={"pk": device.pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        response_body = response.content.decode(response.charset)
        # Count the number of occurrences of "Add IP address" in the response_body
        count = response_body.count("Add IP address")
        # Assert that "Add IP address" appears for each of the three interfaces
        self.assertEqual(count, 3)

    def test_device_interface_assign_ipaddress(self):
        device = Device.objects.first()
        self.add_permissions(
            "ipam.add_ipaddress", "extras.view_status", "ipam.view_namespace", "dcim.view_device", "dcim.view_interface"
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

        with self.subTest("Assert Cannnot assign IPAddress('Add New') without permission"):
            # Assert Add new IPAddress
            response = self.client.post(**add_new_ip_request, follow=True)
            response_body = response.content.decode(response.charset)
            self.assertHttpStatus(response, 200)
            self.interfaces[0].refresh_from_db()
            self.assertEqual(self.interfaces[0].ip_addresses.all().count(), 0)
            self.assertIn(f"Interface with id &quot;{self.interfaces[0].pk}&quot; not found", response_body)

        with self.subTest("Assert Cannnot assign IPAddress(Exsisting IP) without permission"):
            # Assert Assign Exsisting IPAddress
            response = self.client.post(**assign_ip_request, follow=True)
            response_body = response.content.decode(response.charset)
            self.assertHttpStatus(response, 200)
            self.interfaces[1].refresh_from_db()
            self.assertEqual(self.interfaces[1].ip_addresses.all().count(), 0)
            self.assertIn(f"Interface with id &quot;{self.interfaces[1].pk}&quot; not found", response_body)

        self.add_permissions("dcim.change_interface", "ipam.view_ipaddress")

        with self.subTest("Assert Create and Assign IPAddress"):
            self.assertHttpStatus(self.client.post(**add_new_ip_request), 302)
            self.interfaces[0].refresh_from_db()
            self.assertEqual(
                str(self.interfaces[0].ip_addresses.all().first().address), add_new_ip_form_data["address"]
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
        device = Device.objects.first()
        interface = Interface.objects.first()
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
            name="Schema 1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
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
        self.assertEqual(self._get_queryset().get(name="Device X").local_config_context_schema.pk, schema.pk)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_local_config_context_schema_validation_fails(self):
        """
        Given a config context schema
        And a device with local context that *does not* conform to that schema
        Assert that the local context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", data_schema={"type": "object", "properties": {"foo": {"type": "integer"}}}
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

        cls.csv_data = (
            "device,name",
            f"{device.composite_key},Console Port 4",
            f"{device.pk},Console Port 5",
            f"{device.composite_key},Console Port 6",
        )


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

        cls.csv_data = (
            "device,name",
            f"{device.composite_key},Console Server Port 4",
            f"{device.pk},Console Server Port 5",
            f"{device.composite_key},Console Server Port 6",
        )


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
            "description": "A power port",
            "tags": [t.pk for t in Tag.objects.get_for_model(PowerPort)],
        }

        cls.bulk_create_data = {
            "device": device.pk,
            "name_pattern": "Power Port [4-6]]",
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
            "description": "A power port",
            "tags": [t.pk for t in Tag.objects.get_for_model(PowerPort)],
        }

        cls.bulk_edit_data = {
            "type": PowerPortTypeChoices.TYPE_IEC_C14,
            "maximum_draw": 100,
            "allocated_draw": 50,
            "description": "New description",
        }

        cls.csv_data = (
            "device,name",
            f"{device.composite_key},Power Port 4",
            f"{device.pk},Power Port 5",
            f"{device.composite_key},Power Port 6",
        )


class PowerOutletTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = PowerOutlet

    @classmethod
    def setUpTestData(cls):
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

        cls.csv_data = (
            "device,name",
            f"{device.composite_key},Power Outlet 4",
            f"{device.pk},Power Outlet 5",
            f"{device.composite_key},Power Outlet 6",
        )


class InterfaceTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = Interface

    @classmethod
    def setUpTestData(cls):
        device = create_test_device("Device 1")

        statuses = Status.objects.get_for_model(Interface)
        status_active = statuses[0]

        interfaces = (
            Interface.objects.create(device=device, name="Interface 1", status=status_active),
            Interface.objects.create(device=device, name="Interface 2", status=status_active),
            Interface.objects.create(device=device, name="Interface 3", status=status_active),
            Interface.objects.create(
                device=device, name="LAG", status=status_active, type=InterfaceTypeChoices.TYPE_LAG
            ),
            Interface.objects.create(
                device=device, name="BRIDGE", status=status_active, type=InterfaceTypeChoices.TYPE_BRIDGE
            ),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = interfaces
        cls.selected_objects_parent_name = device.name

        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlan_group = VLANGroup.objects.first()
        vlans = (
            VLAN.objects.create(
                vid=1, name="VLAN1", location=device.location, status=vlan_status, vlan_group=vlan_group
            ),
            VLAN.objects.create(
                vid=101, name="VLAN101", location=device.location, status=vlan_status, vlan_group=vlan_group
            ),
            VLAN.objects.create(
                vid=102, name="VLAN102", location=device.location, status=vlan_status, vlan_group=vlan_group
            ),
            VLAN.objects.create(
                vid=103, name="VLAN103", location=device.location, status=vlan_status, vlan_group=vlan_group
            ),
        )

        cls.form_data = {
            "device": device.pk,
            "name": "Interface X",
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "enabled": False,
            "status": status_active.pk,
            "lag": interfaces[3].pk,
            "mac_address": EUI("01:02:03:04:05:06"),
            "mtu": 2000,
            "mgmt_only": True,
            "description": "A front port",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "untagged_vlan": vlans[0].pk,
            "tagged_vlans": [v.pk for v in vlans[1:4]],
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
        }

        cls.bulk_add_data = {
            "device": device.pk,
            "name_pattern": "Interface [4-6]",
            "label_pattern": "Interface Number [4-6]",
            "status": status_active.pk,
            "type": InterfaceTypeChoices.TYPE_1GE_GBIC,
            "enabled": True,
            "mtu": 1500,
            "mgmt_only": False,
            "description": "An Interface",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "tags": [],
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
        }

        cls.csv_data = (
            "type,name,device__name,device__location__name,status",
            f"virtual,Interface 4,{device.name},{device.location.name},{statuses[0].name}",
            f"1000base-t,Interface 5,{device.name},{device.location.name},{statuses[0].name}",
            f"1000base-t,Interface 6,{device.name},{device.location.name},{statuses[1].name}",
        )


class FrontPortTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = FrontPort

    @classmethod
    def setUpTestData(cls):
        device = create_test_device("Device 1")
        cls.device = device

        rearports = (
            RearPort.objects.create(device=device, name="Rear Port 1"),
            RearPort.objects.create(device=device, name="Rear Port 2"),
            RearPort.objects.create(device=device, name="Rear Port 3"),
            RearPort.objects.create(device=device, name="Rear Port 4"),
            RearPort.objects.create(device=device, name="Rear Port 5"),
            RearPort.objects.create(device=device, name="Rear Port 6"),
        )

        frontports = (
            FrontPort.objects.create(device=device, name="Front Port 1", rear_port=rearports[0]),
            FrontPort.objects.create(device=device, name="Front Port 2", rear_port=rearports[1]),
            FrontPort.objects.create(device=device, name="Front Port 3", rear_port=rearports[2]),
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

        cls.csv_data = (
            "device,name,type,rear_port,rear_port_position",
            f"{device.composite_key},Front Port 4,8p8c,{rearports[3].composite_key},1",
            f"{device.pk},Front Port 5,8p8c,{rearports[4].composite_key},1",
            f"{device.composite_key},Front Port 6,8p8c,{rearports[5].pk},1",
        )

    @unittest.skip("No DeviceBulkAddFrontPortView exists at present")
    def test_bulk_add_component(self):
        pass


class RearPortTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = RearPort

    @classmethod
    def setUpTestData(cls):
        device = create_test_device("Device 1")

        rearports = (
            RearPort.objects.create(device=device, name="Rear Port 1"),
            RearPort.objects.create(device=device, name="Rear Port 2"),
            RearPort.objects.create(device=device, name="Rear Port 3"),
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

        cls.csv_data = (
            "device,name,type,positions",
            f"{device.composite_key},Rear Port 4,8p8c,1",
            f"{device.pk},Rear Port 5,8p8c,1",
            f"{device.composite_key},Rear Port 6,8p8c,1",
        )


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

        cls.csv_data = (
            "device,name",
            f"{device.composite_key},Device Bay 4",
            f"{device.pk},Device Bay 5",
            f"{device.composite_key},Device Bay 6",
        )


class InventoryItemTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = InventoryItem

    @classmethod
    def setUpTestData(cls):
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
        }

        cls.bulk_edit_data = {
            "part_id": "123456",
            "description": "New description",
        }

        cls.csv_data = (
            "device,name",
            f"{device.composite_key},Inventory Item 4",
            f"{device.pk},Inventory Item 5",
            f"{device.composite_key},Inventory Item 6",
        )


# TODO: Change base class to PrimaryObjectViewTestCase
# Blocked by lack of common creation view for cables (termination A must be initialized)
class CableTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
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
                name="Interface 1",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[0],
                name="Interface 2",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[0],
                name="Interface 3",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Interface 1",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Interface 2",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Interface 3",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Interface 1",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Interface 2",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Interface 3",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[3],
                name="Interface 1",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[3],
                name="Interface 2",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[3],
                name="Interface 3",
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

        cls.csv_data = (
            "termination_a_id,termination_a_type,termination_b_id,termination_b_type,status",
            f"{interfaces[6].id},dcim.interface,{interfaces[9].id},dcim.interface,{statuses[0].name}",
            f"{interfaces[7].id},dcim.interface,{interfaces[10].id},dcim.interface,{statuses[0].name}",
            f"{interfaces[8].id},dcim.interface,{interfaces[11].id},dcim.interface,{statuses[0].name}",
        )

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
            cid="Circuit 1", provider=provider, circuit_type=circuittype, status=circuit_status
        )

        circuit_terminations = [
            CircuitTermination.objects.create(
                circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_A, location=location
            ),
            CircuitTermination.objects.create(
                circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_Z, location=location
            ),
        ]

        status = Status.objects.get_for_model(Cable).get(name="Connected")
        cables = [
            Cable.objects.create(termination_a=circuit_terminations[0], termination_b=interfaces[0], status=status),
            Cable.objects.create(termination_a=circuit_terminations[1], termination_b=interfaces[1], status=status),
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
            | Q(destination_type=termination_ct, destination_id=circuit_terminations[0].pk)
            | Q(destination_type=interface_ct, destination_id=interfaces[0].pk)
        )
        # pylint: enable=unsupported-binary-operation
        self.assertFalse(cable_path_1.exists())

        # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
        # pylint: disable=unsupported-binary-operation
        cable_path_2 = CablePath.objects.filter(
            Q(origin_type=termination_ct, origin_id=circuit_terminations[1].pk)
            | Q(origin_type=interface_ct, origin_id=interfaces[1].pk)
            | Q(destination_type=termination_ct, destination_id=circuit_terminations[1].pk)
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

    def get_list_url(self):
        return "/dcim/console-connections/"

    def get_title(self):
        return "Console Connections"

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

        Cable.objects.create(termination_a=consoleports[0], termination_b=serverports[0], status=status_connected)
        Cable.objects.create(termination_a=consoleports[1], termination_b=serverports[1], status=status_connected)
        Cable.objects.create(termination_a=consoleports[2], termination_b=rearport, status=status_connected)


class PowerConnectionsTestCase(ViewTestCases.ListObjectsViewTestCase):
    """
    Test the PowerConnectionsListView.
    """

    def get_list_url(self):
        return "/dcim/power-connections/"

    def get_title(self):
        return "Power Connections"

    def _get_base_url(self):
        return "dcim:power_connections_{}"

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

        Cable.objects.create(termination_a=powerports[2], termination_b=powerfeed, status=status_connected)
        # Creating a PowerOutlet with a PowerPort via the ORM does *not* automatically cable the two together. Bug?
        Cable.objects.create(termination_a=powerports[0], termination_b=poweroutlets[0], status=status_connected)
        Cable.objects.create(termination_a=powerports[1], termination_b=poweroutlets[1], status=status_connected)


class InterfaceConnectionsTestCase(ViewTestCases.ListObjectsViewTestCase):
    """
    Test the InterfaceConnectionsListView.
    """

    def _get_base_url(self):
        return "dcim:interface_connections_{}"

    def get_list_url(self):
        return "/dcim/interface-connections/"

    def get_title(self):
        return "Interface Connections"

    model = Interface
    filterset = InterfaceConnectionFilterSet

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.first()

        device_1 = create_test_device("Device 1")
        device_2 = create_test_device("Device 2")

        interface_status = Status.objects.get_for_model(Interface).first()
        cls.interfaces = (
            Interface.objects.create(
                device=device_1, name="Interface 1", type=InterfaceTypeChoices.TYPE_1GE_SFP, status=interface_status
            ),
            Interface.objects.create(
                device=device_1, name="Interface 2", type=InterfaceTypeChoices.TYPE_1GE_SFP, status=interface_status
            ),
            Interface.objects.create(
                device=device_1, name="Interface 3", type=InterfaceTypeChoices.TYPE_1GE_SFP, status=interface_status
            ),
        )

        cls.device_2_interface = Interface.objects.create(
            device=device_2, name="Interface 1", type=InterfaceTypeChoices.TYPE_1GE_SFP, status=interface_status
        )
        rearport = RearPort.objects.create(device=device_2, type=PortTypeChoices.TYPE_8P8C)

        provider = Provider.objects.first()
        circuittype = CircuitType.objects.first()
        circuit_status = Status.objects.get_for_model(Circuit).first()
        circuit = Circuit.objects.create(
            cid="Circuit 1", provider=provider, circuit_type=circuittype, status=circuit_status
        )
        circuittermination = CircuitTermination.objects.create(
            circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_A, location=location
        )

        connected = Status.objects.get(name="Connected")

        Cable.objects.create(termination_a=cls.interfaces[0], termination_b=cls.device_2_interface, status=connected)
        Cable.objects.create(termination_a=cls.interfaces[1], termination_b=circuittermination, status=connected)
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
        # TODO: it'd make test failures more readable if we strip the page headers/footers from the content
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

        cls.csv_data = (
            "name,domain,master",
            f"VC4,Domain 4,{cls.devices[9].composite_key}",
            f"VC5,Domain 5,{cls.devices[10].pk}",
            f"VC6,Domain 6,{cls.devices[11].composite_key}",
        )

        cls.bulk_edit_data = {
            "domain": "domain-x",
        }

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
        self.assertIn("<th >Device</th>", str(response.content))

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
        self.assertNotIn("<th >Device</th>", str(response.content))
        # Sanity check:
        self.assertIn("<th >Name</th>", str(response.content))


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

        cls.csv_data = (
            "location,rack_group,name",
            f"{locations[0].composite_key},{rackgroups[0].composite_key},Power Panel 4",
            f"{locations[0].pk},{rackgroups[0].composite_key},Power Panel 5",
            f"{locations[0].composite_key},{rackgroups[0].pk},Power Panel 6",
        )

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
            name="Power Feed 1", power_panel=powerpanels[0], rack=racks[0], status=status_planned
        )
        powerfeed_2 = PowerFeed.objects.create(
            name="Power Feed 2", power_panel=powerpanels[0], rack=racks[0], status=status_planned
        )
        PowerFeed.objects.create(name="Power Feed 3", power_panel=powerpanels[0], rack=racks[0], status=status_planned)

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

        cls.csv_data = (
            "power_panel,name,voltage,amperage,max_utilization,status",
            f"{powerpanels[0].composite_key},Power Feed 4,120,20,80,{statuses[0].name}",
            f"{powerpanels[0].pk},Power Feed 5,120,20,80,{statuses[0].pk}",
            f"{powerpanels[0].composite_key},Power Feed 6,120,20,80,{statuses[1].name}",
        )

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
            termination_a=powerport, termination_b=powerfeed, status=Status.objects.get(name="Connected")
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
            device_type=devicetype, role=devicerole, name="Device 1", location=location, status=active
        )
        obj = RearPort.objects.create(device=device, name="Rear Port 1", type=PortTypeChoices.TYPE_8P8C)
        peer_obj = Interface.objects.create(device=device, name="eth0", status=active)
        Cable.objects.create(termination_a=obj, termination_b=peer_obj, label="Cable 1", status=connected)

        url = reverse("dcim:rearport_trace", args=[obj.pk])
        cablepath_id = CablePath.objects.first().id
        response = self.client.get(url + f"?cablepath_id={cablepath_id}")
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertInHTML("<h1>Cable Trace for Rear Port Rear Port 1</h1>", content)


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

        cls.csv_data = (
            "name,failover_strategy,status",
            f"DRG δ,,{statuses[0].name}",
            f"DRG ε,,{statuses[0].name}",
            f"DRG ζ,active-active,{statuses[1].name}",
            f"DRG 7,active-passive,{statuses[1].name}",
        )

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

        interface_redundancy_groups = (
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

        for group in interface_redundancy_groups:
            group.validated_save()

        cls.form_data = {
            "name": "IRG χ",
            "protocol": InterfaceRedundancyGroupProtocolChoices.GLBP,
            "status": statuses[3].pk,
        }

        cls.csv_data = (
            "name,protocol,status",
            f"IRG δ,hsrp,{statuses[0].name}",
            f"IRG ε,glbp,{statuses[1].name}",
            f"IRG ζ,hsrp,{statuses[0].name}",
            f"IRG 7,carp,{statuses[2].name}",
        )

        cls.bulk_edit_data = {
            "protocol": InterfaceRedundancyGroupProtocolChoices.HSRP,
            "status": statuses[0].pk,
            "virtual_ip": cls.ips[0].pk,
            "secrets_group": cls.secrets_groups[1].pk,
        }
