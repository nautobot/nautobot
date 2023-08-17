from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.core.testing import FilterTestCases
from nautobot.dcim.choices import (
    CableLengthUnitChoices,
    CableTypeChoices,
    DeviceFaceChoices,
    InterfaceModeChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedPhaseChoices,
    PowerFeedSupplyChoices,
    PowerFeedTypeChoices,
    PowerOutletFeedLegChoices,
    RackDimensionUnitChoices,
    RackTypeChoices,
    RackWidthChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.filters import (
    CableFilterSet,
    ConsolePortFilterSet,
    ConsolePortTemplateFilterSet,
    ConsoleServerPortFilterSet,
    ConsoleServerPortTemplateFilterSet,
    DeviceBayFilterSet,
    DeviceBayTemplateFilterSet,
    DeviceFilterSet,
    DeviceRedundancyGroupFilterSet,
    DeviceTypeFilterSet,
    FrontPortFilterSet,
    FrontPortTemplateFilterSet,
    InterfaceFilterSet,
    InterfaceRedundancyGroupFilterSet,
    InterfaceRedundancyGroupAssociationFilterSet,
    InterfaceTemplateFilterSet,
    InventoryItemFilterSet,
    LocationFilterSet,
    LocationTypeFilterSet,
    ManufacturerFilterSet,
    PlatformFilterSet,
    PowerFeedFilterSet,
    PowerPanelFilterSet,
    PowerPortFilterSet,
    PowerPortTemplateFilterSet,
    PowerOutletFilterSet,
    PowerOutletTemplateFilterSet,
    RackFilterSet,
    RackGroupFilterSet,
    RackReservationFilterSet,
    RearPortFilterSet,
    RearPortTemplateFilterSet,
    VirtualChassisFilterSet,
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
    DeviceType,
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
    Platform,
    PowerFeed,
    PowerPanel,
    PowerPort,
    PowerPortTemplate,
    PowerOutlet,
    PowerOutletTemplate,
    Rack,
    RackGroup,
    RackReservation,
    RearPort,
    RearPortTemplate,
    VirtualChassis,
)
from nautobot.extras.models import Role, SecretsGroup, Status, Tag
from nautobot.ipam.models import IPAddress, Prefix, Service, VLAN, VLANGroup, Namespace
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine


# Use the proper swappable User model
User = get_user_model()


def common_test_data(cls):
    tenants = Tenant.objects.filter(tenant_group__isnull=False)
    cls.tenants = tenants

    lt1 = LocationType.objects.get(name="Campus")
    lt2 = LocationType.objects.get(name="Building")
    lt3 = LocationType.objects.get(name="Floor")
    lt4 = LocationType.objects.get(name="Room")
    lt4.content_types.add(ContentType.objects.get_for_model(Device))

    loc0 = Location.objects.filter(location_type=lt1).first()
    loc1 = Location.objects.filter(location_type=lt1).first()
    loc2 = Location.objects.filter(location_type=lt2).first()

    for instance in [loc0, loc1]:
        instance.tags.set(Tag.objects.get_for_model(Location))
    loc2.parent = loc1
    loc3 = Location.objects.filter(location_type=lt3).first()
    loc3.parent = loc2
    loc4 = Location.objects.filter(location_type=lt4).first()
    nested_loc = Location.objects.filter(location_type__nestable=True, parent__isnull=False).first()
    for loc in [loc1, loc2, loc3, loc4, nested_loc]:
        loc.validated_save()
    cls.loc0 = loc0
    cls.loc1 = loc1
    cls.nested_loc = nested_loc

    provider = Provider.objects.first()
    circuit_type = CircuitType.objects.first()
    circuit_status = Status.objects.get_for_model(Circuit).first()
    circuit = Circuit.objects.create(
        provider=provider, circuit_type=circuit_type, cid="Test Circuit 1", status=circuit_status
    )
    CircuitTermination.objects.create(circuit=circuit, location=loc0, term_side="A")
    CircuitTermination.objects.create(circuit=circuit, location=loc1, term_side="Z")

    manufacturers = list(Manufacturer.objects.all()[:3])
    cls.manufacturers = manufacturers

    platforms = Platform.objects.all()[:3]
    for num, platform in enumerate(platforms):
        platform.manufacturer = manufacturers[num]
        platform.napalm_driver = f"driver-{num}"
        platform.napalm_args = ["--test", f"--arg{num}"]
        platform.network_driver = f"driver_{num}"
        platform.save()
    cls.platforms = platforms

    device_types = (
        DeviceType.objects.create(
            manufacturer=manufacturers[0],
            comments="Device type 1",
            model="Model 1",
            part_number="Part Number 1",
            u_height=1,
            is_full_depth=True,
        ),
        DeviceType.objects.create(
            manufacturer=manufacturers[1],
            comments="Device type 2",
            model="Model 2",
            part_number="Part Number 2",
            u_height=2,
            is_full_depth=True,
            subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
        ),
        DeviceType.objects.create(
            manufacturer=manufacturers[2],
            comments="Device type 3",
            model="Model 3",
            part_number="Part Number 3",
            u_height=3,
            is_full_depth=False,
            subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
        ),
    )
    cls.device_types = device_types

    rack_groups = (
        RackGroup.objects.create(name="Rack Group 1", location=loc0),
        RackGroup.objects.create(name="Rack Group 2", location=loc1),
        RackGroup.objects.create(name="Rack Group 3", location=loc1),
    )

    power_panels = (
        PowerPanel.objects.create(name="Power Panel 1", location=loc0, rack_group=rack_groups[0]),
        PowerPanel.objects.create(name="Power Panel 2", location=loc1, rack_group=rack_groups[1]),
        PowerPanel.objects.create(name="Power Panel 3", location=loc1, rack_group=rack_groups[2]),
    )
    power_panels[0].tags.set(Tag.objects.get_for_model(PowerPanel))
    power_panels[1].tags.set(Tag.objects.get_for_model(PowerPanel)[:3])

    rackroles = Role.objects.get_for_model(Rack)

    cls.rack_statuses = Status.objects.get_for_model(Rack)

    racks = (
        Rack.objects.create(
            name="Rack 1",
            comments="comment1",
            facility_id="rack-1",
            location=loc0,
            rack_group=rack_groups[0],
            tenant=tenants[0],
            status=cls.rack_statuses[0],
            role=rackroles[0],
            serial="ABC",
            asset_tag="1001",
            type=RackTypeChoices.TYPE_2POST,
            width=RackWidthChoices.WIDTH_19IN,
            u_height=42,
            desc_units=False,
            outer_width=100,
            outer_depth=100,
            outer_unit=RackDimensionUnitChoices.UNIT_MILLIMETER,
        ),
        Rack.objects.create(
            name="Rack 2",
            comments="comment2",
            facility_id="rack-2",
            rack_group=rack_groups[1],
            location=loc0,
            tenant=tenants[1],
            status=cls.rack_statuses[1],
            role=rackroles[1],
            serial="DEF",
            asset_tag="1002",
            type=RackTypeChoices.TYPE_4POST,
            width=RackWidthChoices.WIDTH_21IN,
            u_height=43,
            desc_units=False,
            outer_width=200,
            outer_depth=200,
            outer_unit=RackDimensionUnitChoices.UNIT_MILLIMETER,
        ),
        Rack.objects.create(
            name="Rack 3",
            comments="comment3",
            facility_id="rack-3",
            rack_group=rack_groups[2],
            location=loc0,
            tenant=tenants[2],
            status=cls.rack_statuses[2],
            role=rackroles[2],
            serial="GHI",
            asset_tag="1003",
            type=RackTypeChoices.TYPE_CABINET,
            width=RackWidthChoices.WIDTH_23IN,
            u_height=44,
            desc_units=True,
            outer_width=300,
            outer_depth=300,
            outer_unit=RackDimensionUnitChoices.UNIT_INCH,
        ),
    )
    racks[0].tags.set(Tag.objects.get_for_model(Rack))
    racks[1].tags.set(Tag.objects.get_for_model(Rack)[:3])

    cls.device_roles = Role.objects.get_for_model(Device)

    cluster_type = ClusterType.objects.create(name="Circuit Type 2")
    clusters = (
        Cluster.objects.create(name="Cluster 1", cluster_type=cluster_type, location=loc0),
        Cluster.objects.create(name="Cluster 2", cluster_type=cluster_type, location=loc1),
        Cluster.objects.create(name="Cluster 3", cluster_type=cluster_type, location=loc1),
    )

    vm_status = Status.objects.get_for_model(VirtualMachine).first()
    VirtualMachine.objects.create(
        cluster=clusters[0], name="VM 1", role=cls.device_roles[0], platform=platforms[0], status=vm_status
    )
    VirtualMachine.objects.create(
        cluster=clusters[0], name="VM 2", role=cls.device_roles[1], platform=platforms[1], status=vm_status
    )
    VirtualMachine.objects.create(
        cluster=clusters[0], name="VM 3", role=cls.device_roles[2], platform=platforms[2], status=vm_status
    )

    vlan_groups = (
        VLANGroup.objects.create(name="VLAN Group 1", location=loc0),
        VLANGroup.objects.create(name="VLAN Group 2", location=loc0),
        VLANGroup.objects.create(name="VLAN Group 3", location=loc1),
    )

    vlan_status = Status.objects.get_for_model(VLAN).first()
    VLAN.objects.create(name="VLAN 101", vid=101, location=loc0, status=vlan_status, vlan_group=vlan_groups[0])
    VLAN.objects.create(name="VLAN 102", vid=102, location=loc0, status=vlan_status, vlan_group=vlan_groups[1])
    VLAN.objects.create(name="VLAN 103", vid=103, location=loc1, status=vlan_status, vlan_group=vlan_groups[2])

    pf_status = Status.objects.get_for_model(PowerFeed).first()
    power_feeds = (
        PowerFeed.objects.create(name="Power Feed 1", rack=racks[0], power_panel=power_panels[0], status=pf_status),
        PowerFeed.objects.create(name="Power Feed 2", rack=racks[1], power_panel=power_panels[1], status=pf_status),
        PowerFeed.objects.create(name="Power Feed 3", rack=racks[2], power_panel=power_panels[2], status=pf_status),
    )
    power_feeds[0].tags.set(Tag.objects.get_for_model(PowerFeed))
    power_feeds[1].tags.set(Tag.objects.get_for_model(PowerFeed)[:3])

    users = (
        User.objects.create_user(username="TestCaseUser 1"),
        User.objects.create_user(username="TestCaseUser 2"),
        User.objects.create_user(username="TestCaseUser 3"),
    )

    rack_reservations = (
        RackReservation.objects.create(
            rack=racks[0],
            units=(1, 2, 3),
            user=users[0],
            description="Rack Reservation 1",
            tenant=tenants[0],
        ),
        RackReservation.objects.create(
            rack=racks[1],
            units=(4, 5, 6),
            user=users[1],
            description="Rack Reservation 2",
            tenant=tenants[1],
        ),
        RackReservation.objects.create(
            rack=racks[2],
            units=(7, 8, 9),
            user=users[2],
            description="Rack Reservation 3",
            tenant=tenants[2],
        ),
    )
    rack_reservations[0].tags.set(Tag.objects.get_for_model(RackReservation))
    rack_reservations[1].tags.set(Tag.objects.get_for_model(RackReservation)[:3])

    ConsolePortTemplate.objects.create(
        device_type=device_types[0],
        name="Console Port 1",
        label="console1",
        description="Front Console Port 1",
    )
    ConsolePortTemplate.objects.create(
        device_type=device_types[1],
        name="Console Port 2",
        label="console2",
        description="Front Console Port 2",
    )
    ConsolePortTemplate.objects.create(
        device_type=device_types[2],
        name="Console Port 3",
        label="console3",
        description="Front Console Port 3",
    )

    ConsoleServerPortTemplate.objects.create(
        device_type=device_types[0],
        name="Console Server Port 1",
        label="consoleserverport1",
        description="Front Console Server Port 1",
    )
    ConsoleServerPortTemplate.objects.create(
        device_type=device_types[1],
        name="Console Server Port 2",
        label="consoleserverport2",
        description="Front Console Server Port 2",
    )
    ConsoleServerPortTemplate.objects.create(
        device_type=device_types[2],
        name="Console Server Port 3",
        label="consoleserverport3",
        description="Front Console Server Port 3",
    )

    power_port_templates = (
        PowerPortTemplate.objects.create(
            device_type=device_types[0],
            name="Power Port 1",
            maximum_draw=100,
            allocated_draw=50,
            label="powerport1",
            description="Power Port Description 1",
        ),
        PowerPortTemplate.objects.create(
            device_type=device_types[1],
            name="Power Port 2",
            maximum_draw=200,
            allocated_draw=100,
            label="powerport2",
            description="Power Port Description 2",
        ),
        PowerPortTemplate.objects.create(
            device_type=device_types[2],
            name="Power Port 3",
            maximum_draw=300,
            allocated_draw=150,
            label="powerport3",
            description="Power Port Description 3",
        ),
    )

    PowerOutletTemplate.objects.create(
        device_type=device_types[0],
        power_port_template=power_port_templates[0],
        name="Power Outlet 1",
        feed_leg=PowerOutletFeedLegChoices.FEED_LEG_A,
        label="poweroutlet1",
        description="Power Outlet Description 1",
    )
    PowerOutletTemplate.objects.create(
        device_type=device_types[1],
        power_port_template=power_port_templates[1],
        name="Power Outlet 2",
        feed_leg=PowerOutletFeedLegChoices.FEED_LEG_B,
        label="poweroutlet2",
        description="Power Outlet Description 2",
    )
    PowerOutletTemplate.objects.create(
        device_type=device_types[2],
        power_port_template=power_port_templates[2],
        name="Power Outlet 3",
        feed_leg=PowerOutletFeedLegChoices.FEED_LEG_C,
        label="poweroutlet3",
        description="Power Outlet Description 3",
    )

    InterfaceTemplate.objects.create(
        name="Interface 1",
        description="Interface Description 1",
        device_type=device_types[0],
        label="interface1",
        mgmt_only=True,
        type=InterfaceTypeChoices.TYPE_1GE_SFP,
    )
    InterfaceTemplate.objects.create(
        name="Interface 2",
        description="Interface Description 2",
        device_type=device_types[1],
        label="interface2",
        mgmt_only=False,
        type=InterfaceTypeChoices.TYPE_1GE_GBIC,
    )
    InterfaceTemplate.objects.create(
        name="Interface 3",
        description="Interface Description 3",
        device_type=device_types[2],
        label="interface3",
        mgmt_only=False,
        type=InterfaceTypeChoices.TYPE_1GE_FIXED,
    )

    rear_ports = (
        RearPortTemplate.objects.create(
            device_type=device_types[0],
            name="Rear Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            positions=1,
            label="rearport1",
            description="Rear Port Description 1",
        ),
        RearPortTemplate.objects.create(
            device_type=device_types[1],
            name="Rear Port 2",
            type=PortTypeChoices.TYPE_110_PUNCH,
            positions=2,
            label="rearport2",
            description="Rear Port Description 2",
        ),
        RearPortTemplate.objects.create(
            device_type=device_types[2],
            name="Rear Port 3",
            type=PortTypeChoices.TYPE_BNC,
            positions=3,
            label="rearport3",
            description="Rear Port Description 3",
        ),
    )

    FrontPortTemplate.objects.create(
        device_type=device_types[0],
        name="Front Port 1",
        rear_port_template=rear_ports[0],
        type=PortTypeChoices.TYPE_8P8C,
        rear_port_position=1,
        label="frontport1",
        description="Front Port Description 1",
    )
    FrontPortTemplate.objects.create(
        device_type=device_types[1],
        name="Front Port 2",
        rear_port_template=rear_ports[1],
        type=PortTypeChoices.TYPE_110_PUNCH,
        rear_port_position=2,
        label="frontport2",
        description="Front Port Description 2",
    )
    FrontPortTemplate.objects.create(
        device_type=device_types[2],
        name="Front Port 3",
        rear_port_template=rear_ports[2],
        type=PortTypeChoices.TYPE_BNC,
        rear_port_position=3,
        label="frontport3",
        description="Front Port Description 3",
    )

    DeviceBayTemplate.objects.create(
        device_type=device_types[0],
        name="Device Bay 1",
        label="devicebay1",
        description="Device Bay Description 1",
    )
    DeviceBayTemplate.objects.create(
        device_type=device_types[1],
        name="Device Bay 2",
        label="devicebay2",
        description="Device Bay Description 2",
    )
    DeviceBayTemplate.objects.create(
        device_type=device_types[2],
        name="Device Bay 3",
        label="devicebay3",
        description="Device Bay Description 3",
    )

    secrets_groups = (
        SecretsGroup.objects.create(name="Secrets group 1"),
        SecretsGroup.objects.create(name="Secrets group 2"),
        SecretsGroup.objects.create(name="Secrets group 3"),
    )

    device_statuses = Status.objects.get_for_model(Device)

    devices = (
        Device.objects.create(
            name="Device 1",
            device_type=device_types[0],
            role=cls.device_roles[0],
            platform=platforms[0],
            rack=racks[0],
            location=loc0,
            tenant=tenants[0],
            status=device_statuses[0],
            cluster=clusters[0],
            asset_tag="1001",
            face=DeviceFaceChoices.FACE_FRONT,
            serial="ABC",
            position=1,
            secrets_group=secrets_groups[0],
        ),
        Device.objects.create(
            name="Device 2",
            device_type=device_types[1],
            role=cls.device_roles[1],
            platform=platforms[1],
            rack=racks[1],
            location=loc0,
            tenant=tenants[1],
            status=device_statuses[1],
            cluster=clusters[1],
            asset_tag="1002",
            face=DeviceFaceChoices.FACE_FRONT,
            serial="DEF",
            position=2,
            secrets_group=secrets_groups[1],
            local_config_context_data={"foo": 123},
        ),
        Device.objects.create(
            name="Device 3",
            device_type=device_types[2],
            role=cls.device_roles[2],
            platform=platforms[2],
            rack=racks[2],
            location=loc1,
            tenant=tenants[2],
            status=device_statuses[2],
            cluster=clusters[2],
            asset_tag="1003",
            face=DeviceFaceChoices.FACE_REAR,
            serial="GHI",
            position=3,
            secrets_group=secrets_groups[2],
        ),
    )
    devices[0].tags.set(Tag.objects.get_for_model(Device))
    devices[1].tags.set(Tag.objects.get_for_model(Device)[:3])


class LocationTypeFilterSetTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = LocationType.objects.all()
    filterset = LocationTypeFilterSet
    generic_filter_tests = [
        ("description",),
        ("parent", "parent__id"),
        ("parent", "parent__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        cls.lt1 = LocationType.objects.get(name="Building")
        cls.lt1.description = "It's a building"
        cls.lt1.validated_save()
        cls.lt2 = LocationType.objects.get(name="Floor")
        cls.lt2.description = "It's a floor"
        cls.lt2.validated_save()

    def test_content_types(self):
        with self.subTest():
            params = {"content_types": ["dcim.rackgroup"]}
            ct = ContentType.objects.get_for_model(RackGroup)
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                LocationType.objects.filter(content_types=ct).count(),
            )
        with self.subTest():
            params = {"content_types": ["dcim.device", "dcim.rack"]}
            ct_1 = [ContentType.objects.get_for_model(Device)]
            ct_2 = [ContentType.objects.get_for_model(Rack)]
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                LocationType.objects.filter(Q(content_types__in=ct_1)).filter(Q(content_types__in=ct_2)).count(),
            )


class LocationFilterSetTestCase(FilterTestCases.NameOnlyFilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Location.objects.all()
    filterset = LocationFilterSet
    tenancy_related_name = "locations"
    generic_filter_tests = [
        ("asn",),
        ("circuit_terminations", "circuit_terminations__id"),
        ("clusters", "clusters__id"),
        ("clusters", "clusters__name"),
        ("comments",),
        ("contact_email",),
        ("contact_name",),
        ("contact_phone",),
        ("description",),
        ("devices", "devices__id"),
        ("devices", "devices__name"),
        ("facility",),
        ("latitude",),
        ("longitude",),
        ("location_type", "location_type__id"),
        ("location_type", "location_type__name"),
        ("parent", "parent__id"),
        ("parent", "parent__name"),
        ("physical_address",),
        ("power_panels", "power_panels__id"),
        ("power_panels", "power_panels__name"),
        ("prefixes", "prefixes__id"),
        ("rack_groups", "rack_groups__id"),
        ("rack_groups", "rack_groups__name"),
        ("racks", "racks__id"),
        ("racks", "racks__name"),
        ("shipping_address",),
        ("status", "status__name"),
        ("time_zone",),
        ("vlan_groups", "vlan_groups__id"),
        ("vlan_groups", "vlan_groups__name"),
        ("vlans", "vlans__id"),
        ("vlans", "vlans__vid"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

    def test_subtree(self):
        params = {"subtree": [self.loc1.name, self.nested_loc.pk]}
        expected = Location.objects.get(name=self.loc1.name).descendants(include_self=True)
        expected |= Location.objects.get(name=self.nested_loc.name).descendants(include_self=True)
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected.distinct())

    def test_child_location_type(self):
        params = {"child_location_type": ["Room", LocationType.objects.get(name="Floor").pk]}
        query_params = Q(
            location_type__children__in=[LocationType.objects.get(name="Room"), LocationType.objects.get(name="Floor")]
        ) | Q(
            location_type__in=[LocationType.objects.get(name="Room"), LocationType.objects.get(name="Floor")],
            location_type__nestable=True,
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, Location.objects.filter(query_params)
        )

    def test_content_type(self):
        params = {"content_type": ["dcim.device"]}
        ct = ContentType.objects.get_for_model(Device)
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            Location.objects.filter(location_type__content_types=ct),
        )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, self.queryset.filter(pk=value))


class RackGroupTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = RackGroup.objects.all()
    filterset = RackGroupFilterSet
    generic_filter_tests = [
        ("description",),
        ("parent", "parent__id"),
        ("parent", "parent__name"),
        ("power_panels", "power_panels__id"),
        ("power_panels", "power_panels__name"),
        ("racks", "racks__id"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        parent_rack_groups = RackGroup.objects.filter(parent__isnull=True)

        RackGroup.objects.create(
            name="Child Rack Group 1",
            location=cls.loc0,
            parent=parent_rack_groups[0],
            description="A",
        )
        RackGroup.objects.create(
            name="Child Rack Group 2",
            location=cls.loc0,
            parent=parent_rack_groups[1],
            description="B",
        )
        RackGroup.objects.create(
            name="Child Rack Group 3",
            location=cls.loc1,
            parent=parent_rack_groups[2],
            description="C",
        )
        RackGroup.objects.create(
            name="Rack Group 4",
            location=cls.loc1,
        )

    def test_children(self):
        child_groups = RackGroup.objects.filter(name__startswith="Child").filter(parent__isnull=False)[:2]
        with self.subTest():
            params = {"children": [child_groups[0].pk, child_groups[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            rack_group_4 = RackGroup.objects.filter(name="Rack Group 4").first()
            params = {"children": [rack_group_4.pk, rack_group_4.pk]}
            self.assertFalse(self.filterset(params, self.queryset).qs.exists())


class RackTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Rack.objects.all()
    filterset = RackFilterSet
    tenancy_related_name = "racks"
    generic_filter_tests = [
        ("asset_tag",),
        ("comments",),
        ("devices", "devices__id"),
        ("facility_id",),
        ("name",),
        ("outer_depth",),
        ("outer_width",),
        ("power_feeds", "power_feeds__id"),
        ("power_feeds", "power_feeds__name"),
        ("rack_group", "rack_group__id"),
        ("rack_group", "rack_group__name"),
        ("rack_reservations", "rack_reservations__id"),
        ("role", "role__name"),
        ("serial",),
        ("status", "status__name"),
        ("type",),
        ("u_height",),
        ("width",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        rack_group = RackGroup.objects.get(name="Rack Group 3")
        tenant = Tenant.objects.filter(tenant_group__isnull=False).first()
        rack_role = Role.objects.get_for_model(Rack).first()

        Rack.objects.create(
            name="Rack 4",
            facility_id="rack-4",
            location=cls.loc1,
            rack_group=rack_group,
            tenant=tenant,
            status=cls.rack_statuses[0],
            role=rack_role,
            serial="ABCDEF",
            asset_tag="1004",
            type=RackTypeChoices.TYPE_2POST,
            width=RackWidthChoices.WIDTH_19IN,
            u_height=42,
            desc_units=False,
            outer_width=100,
            outer_depth=100,
        )

    def test_desc_units(self):
        # TODO: not a generic_filter_test since this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"desc_units": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        with self.subTest():
            params = {"desc_units": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_outer_unit(self):
        # TODO: Not a generic_filter_test since this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        with self.subTest():
            self.assertEqual(Rack.objects.exclude(outer_unit="").count(), 3)
        with self.subTest():
            params = {"outer_unit": [RackDimensionUnitChoices.UNIT_MILLIMETER]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class RackReservationTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = RackReservation.objects.all()
    filterset = RackReservationFilterSet
    tenancy_related_name = "rack_reservations"
    generic_filter_tests = [
        ("description",),
        ("rack", "rack__id"),
        ("rack", "rack__name"),
        ("rack_group", "rack__rack_group__id"),
        ("rack_group", "rack__rack_group__name"),
        ("user", "user__id"),
        ("user", "user__username"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class ManufacturerTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = Manufacturer.objects.all()
    filterset = ManufacturerFilterSet
    generic_filter_tests = [
        ("description",),
        ("device_types", "device_types__id"),
        ("device_types", "device_types__model"),
        ("inventory_items", "inventory_items__id"),
        ("inventory_items", "inventory_items__name"),
        ("platforms", "platforms__id"),
        ("platforms", "platforms__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = list(Device.objects.all()[:3])

        InventoryItem.objects.create(device=devices[0], name="Inventory Item 1", manufacturer=cls.manufacturers[0])
        InventoryItem.objects.create(device=devices[1], name="Inventory Item 2", manufacturer=cls.manufacturers[1])
        InventoryItem.objects.create(device=devices[2], name="Inventory Item 3", manufacturer=cls.manufacturers[2])


class DeviceTypeTestCase(FilterTestCases.FilterTestCase):
    queryset = DeviceType.objects.all()
    filterset = DeviceTypeFilterSet
    generic_filter_tests = [
        ("comments",),
        ("console_port_templates", "console_port_templates__id"),
        ("console_port_templates", "console_port_templates__name"),
        ("console_server_port_templates", "console_server_port_templates__id"),
        ("console_server_port_templates", "console_server_port_templates__name"),
        ("device_bay_templates", "device_bay_templates__id"),
        ("device_bay_templates", "device_bay_templates__name"),
        ("devices", "devices__id"),
        ("front_port_templates", "front_port_templates__id"),
        ("front_port_templates", "front_port_templates__name"),
        ("interface_templates", "interface_templates__id"),
        ("interface_templates", "interface_templates__name"),
        ("manufacturer", "manufacturer__id"),
        ("manufacturer", "manufacturer__name"),
        ("model",),
        ("part_number",),
        ("power_outlet_templates", "power_outlet_templates__id"),
        ("power_outlet_templates", "power_outlet_templates__name"),
        ("power_port_templates", "power_port_templates__id"),
        ("power_port_templates", "power_port_templates__name"),
        ("rear_port_templates", "rear_port_templates__id"),
        ("rear_port_templates", "rear_port_templates__name"),
        ("u_height",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            comments="Device type 4",
            model="Model 4",
            part_number="Part Number 4",
            u_height=4,
            is_full_depth=True,
        )
        device_type.tags.set(Tag.objects.get_for_model(DeviceType))

    def test_is_full_depth(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"is_full_depth": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(is_full_depth=True),
            )
        with self.subTest():
            params = {"is_full_depth": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(is_full_depth=False),
            )

    def test_subdevice_role(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        with self.subTest():
            params = {"subdevice_role": [SubdeviceRoleChoices.ROLE_PARENT]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(subdevice_role=SubdeviceRoleChoices.ROLE_PARENT),
            )
        with self.subTest():
            params = {"subdevice_role": [SubdeviceRoleChoices.ROLE_CHILD]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(subdevice_role=SubdeviceRoleChoices.ROLE_CHILD),
            )

    def test_console_ports(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"console_ports": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(console_port_templates__isnull=True),
            )
        with self.subTest():
            params = {"console_ports": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(console_port_templates__isnull=False),
            )

    def test_console_server_ports(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"console_server_ports": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(console_server_port_templates__isnull=True),
            )
        with self.subTest():
            params = {"console_server_ports": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(console_server_port_templates__isnull=False),
            )

    def test_power_ports(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"power_ports": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(power_port_templates__isnull=True),
            )
        with self.subTest():
            params = {"power_ports": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(power_port_templates__isnull=False),
            )

    def test_power_outlets(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"power_outlets": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(power_outlet_templates__isnull=True),
            )
        with self.subTest():
            params = {"power_outlets": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(power_outlet_templates__isnull=False),
            )

    def test_interfaces(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"interfaces": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(interface_templates__isnull=True),
            )
        with self.subTest():
            params = {"interfaces": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(interface_templates__isnull=False),
            )

    def test_pass_through_ports(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        query = Q(front_port_templates__isnull=False, rear_port_templates__isnull=False)
        with self.subTest():
            params = {"pass_through_ports": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(query),
            )
        with self.subTest():
            params = {"pass_through_ports": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(~query),
            )

    def test_device_bays(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"device_bays": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(device_bay_templates__isnull=True),
            )
        with self.subTest():
            params = {"device_bays": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(device_bay_templates__isnull=False),
            )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class Mixins:
    class ComponentTemplateMixin(FilterTestCases.FilterTestCase):
        generic_filter_tests = [
            ("description",),
            ("device_type", "device_type__id"),
            ("device_type", "device_type__model"),
            ("label",),
            ("name",),
        ]

        @classmethod
        def setUpTestData(cls):
            common_test_data(cls)


class ConsolePortTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = ConsolePortTemplate.objects.all()
    filterset = ConsolePortTemplateFilterSet


class ConsoleServerPortTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = ConsoleServerPortTemplate.objects.all()
    filterset = ConsoleServerPortTemplateFilterSet


class PowerPortTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = PowerPortTemplate.objects.all()
    filterset = PowerPortTemplateFilterSet
    generic_filter_tests = Mixins.ComponentTemplateMixin.generic_filter_tests + [
        ("allocated_draw",),
        ("maximum_draw",),
        ("power_outlet_templates", "power_outlet_templates__id"),
        ("power_outlet_templates", "power_outlet_templates__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        device_type = DeviceType.objects.get(model="Model 3")
        PowerPortTemplate.objects.create(
            device_type=device_type,
            name="Power Port 4",
            maximum_draw=400,
            allocated_draw=450,
            label="powerport4",
            description="Power Port Description 4",
        )


class PowerOutletTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = PowerOutletTemplate.objects.all()
    filterset = PowerOutletTemplateFilterSet
    generic_filter_tests = Mixins.ComponentTemplateMixin.generic_filter_tests + [
        ("power_port_template", "power_port_template__id"),
        ("power_port_template", "power_port_template__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        device_type = DeviceType.objects.get(model="Model 3")
        PowerOutletTemplate.objects.create(
            device_type=device_type,
            name="Power Outlet 4",
            feed_leg=PowerOutletFeedLegChoices.FEED_LEG_A,
            label="poweroutlet4",
            description="Power Outlet Description 4",
        )

    def test_feed_leg(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"feed_leg": [PowerOutletFeedLegChoices.FEED_LEG_A]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(feed_leg=PowerOutletFeedLegChoices.FEED_LEG_A),
        )


class InterfaceTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = InterfaceTemplate.objects.all()
    filterset = InterfaceTemplateFilterSet

    def test_type(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"type": [InterfaceTypeChoices.TYPE_1GE_FIXED]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(type=InterfaceTypeChoices.TYPE_1GE_FIXED),
        )

    def test_mgmt_only(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"mgmt_only": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(**params),
            )
        with self.subTest():
            params = {"mgmt_only": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(**params),
            )


class FrontPortTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = FrontPortTemplate.objects.all()
    filterset = FrontPortTemplateFilterSet
    generic_filter_tests = Mixins.ComponentTemplateMixin.generic_filter_tests + [
        ("rear_port_position",),
        ("rear_port_template", "rear_port_template__id"),
    ]

    def test_type(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"type": [PortTypeChoices.TYPE_8P8C]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(type=PortTypeChoices.TYPE_8P8C),
        )


class RearPortTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = RearPortTemplate.objects.all()
    filterset = RearPortTemplateFilterSet
    generic_filter_tests = Mixins.ComponentTemplateMixin.generic_filter_tests + [
        ("front_port_templates", "front_port_templates__id"),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        device_type = DeviceType.objects.get(model="Model 3")
        RearPortTemplate.objects.create(
            device_type=device_type,
            name="Rear Port 4",
            type=PortTypeChoices.TYPE_BNC,
            positions=4,
            label="rearport4",
            description="Rear Port Description 4",
        )

    def test_type(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"type": [PortTypeChoices.TYPE_8P8C]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(type=PortTypeChoices.TYPE_8P8C),
        )

    def test_positions(self):
        positions = [1, 2]
        params = {"positions": positions}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(positions__in=positions),
        )


class DeviceBayTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = DeviceBayTemplate.objects.all()
    filterset = DeviceBayTemplateFilterSet


class PlatformTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = Platform.objects.all()
    filterset = PlatformFilterSet
    generic_filter_tests = [
        ("description",),
        ("devices", "devices__id"),
        ("manufacturer", "manufacturer__id"),
        ("manufacturer", "manufacturer__name"),
        ("napalm_driver",),
        ("virtual_machines", "virtual_machines__id"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

    def test_napalm_args(self):
        """Not currently suitable as a generic_filter_tests entry because we need JSON strings as inputs."""
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        napalm_args = ['["--test", "--arg1"]', '["--test", "--arg2"]']
        params = {"napalm_args": napalm_args}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(napalm_args))

    def test_network_driver(self):
        drivers = ["driver_1", "driver_3"]
        params = {"network_driver": drivers}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, Platform.objects.filter(network_driver__in=drivers)
        )

    def test_devices(self):
        devices = [Device.objects.first(), Device.objects.last()]
        params = {"devices": [devices[0].pk, devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(devices))

    def test_has_devices(self):
        with self.subTest():
            params = {"has_devices": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(devices__isnull=True),
            )
        with self.subTest():
            params = {"has_devices": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(devices__isnull=False),
            )

    def test_virtual_machines(self):
        virtual_machines = [VirtualMachine.objects.first(), VirtualMachine.objects.last()]
        params = {"virtual_machines": [virtual_machines[0].pk, virtual_machines[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(virtual_machines))

    def test_has_virtual_machines(self):
        with self.subTest():
            params = {"has_virtual_machines": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(virtual_machines__isnull=True),
            )
        with self.subTest():
            params = {"has_virtual_machines": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(virtual_machines__isnull=False),
            )


class DeviceTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Device.objects.all()
    filterset = DeviceFilterSet
    tenancy_related_name = "devices"
    generic_filter_tests = [
        ("asset_tag",),
        ("cluster", "cluster__id"),
        ("cluster", "cluster__name"),
        ("console_ports", "console_ports__id"),
        ("console_server_ports", "console_server_ports__id"),
        ("device_bays", "device_bays__id"),
        ("device_redundancy_group", "device_redundancy_group__id"),
        ("device_redundancy_group", "device_redundancy_group__name"),
        ("device_redundancy_group_priority",),
        ("device_type", "device_type__id"),
        ("device_type", "device_type__model"),
        ("front_ports", "front_ports__id"),
        ("interfaces", "interfaces__id"),
        ("mac_address", "interfaces__mac_address"),
        ("manufacturer", "device_type__manufacturer__id"),
        ("manufacturer", "device_type__manufacturer__name"),
        ("name",),
        ("platform", "platform__id"),
        ("platform", "platform__name"),
        ("position",),
        ("power_outlets", "power_outlets__id"),
        ("power_ports", "power_ports__id"),
        ("rack", "rack__id"),
        ("rack", "rack__name"),
        ("rack_group", "rack__rack_group__id"),
        ("rack_group", "rack__rack_group__name"),
        ("rear_ports", "rear_ports__id"),
        ("role", "role__id"),
        ("role", "role__name"),
        ("secrets_group", "secrets_group__id"),
        ("secrets_group", "secrets_group__name"),
        ("status", "status__name"),
        ("vc_position",),
        ("vc_priority",),
        ("virtual_chassis", "virtual_chassis__id"),
        ("virtual_chassis", "virtual_chassis__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = Device.objects.all()

        # Create a device with no components for testing the "has_*" filters
        device_type = DeviceType.objects.create(
            manufacturer=cls.manufacturers[0],
            comments="Non-component Device Type",
            model="Non-component Model",
            part_number="Part Number 1",
            u_height=1,
            is_full_depth=True,
        )

        Device.objects.create(
            device_type=device_type,
            location=devices[0].location,
            name="Device 4",
            platform=Platform.objects.first(),
            role=cls.device_roles[0],
            status=Status.objects.get_for_model(Device).first(),
        )

        # Create additional components for filtering
        InventoryItem.objects.create(device=devices[0], name="Inventory Item 1")
        InventoryItem.objects.create(device=devices[1], name="Inventory Item 2")
        Service.objects.create(device=devices[0], name="ssh", protocol="tcp", ports=[22])
        Service.objects.create(device=devices[1], name="dns", protocol="udp", ports=[53])

        cls.device_redundancy_groups = list(DeviceRedundancyGroup.objects.all()[:2])
        Device.objects.filter(pk=devices[0].pk).update(device_redundancy_group=cls.device_redundancy_groups[0])
        Device.objects.filter(pk=devices[1].pk).update(
            device_redundancy_group=cls.device_redundancy_groups[0], device_redundancy_group_priority=1
        )
        Device.objects.filter(pk=devices[2].pk).update(
            device_redundancy_group=cls.device_redundancy_groups[1], device_redundancy_group_priority=100
        )

        # Assign primary IPs for filtering
        interfaces = Interface.objects.all()
        ipaddr_status = Status.objects.get_for_model(IPAddress).first()
        prefix_status = Status.objects.get_for_model(Prefix).first()
        namespace = Namespace.objects.first()
        Prefix.objects.create(prefix="192.0.2.0/24", namespace=namespace, status=prefix_status)
        Prefix.objects.create(prefix="2600::/64", namespace=namespace, status=prefix_status)
        ipaddresses = (
            IPAddress.objects.create(address="192.0.2.1/24", namespace=namespace, status=ipaddr_status),
            IPAddress.objects.create(address="192.0.2.2/24", namespace=namespace, status=ipaddr_status),
            IPAddress.objects.create(address="2600::1/120", namespace=namespace, status=ipaddr_status),
            IPAddress.objects.create(address="2600::0100/120", namespace=namespace, status=ipaddr_status),
        )

        interfaces[0].add_ip_addresses([ipaddresses[0], ipaddresses[2]])
        interfaces[1].add_ip_addresses([ipaddresses[1], ipaddresses[3]])

        Device.objects.filter(pk=devices[0].pk).update(
            primary_ip4=ipaddresses[0],
            primary_ip6=ipaddresses[2],
            comments="Comment A",
        )
        Device.objects.filter(pk=devices[1].pk).update(
            primary_ip4=ipaddresses[1],
            primary_ip6=ipaddresses[3],
            comments="Comment B",
        )

        # Update existing interface objects with mac addresses for filtering
        Interface.objects.filter(pk=interfaces[0].pk).update(mac_address="00-00-00-00-00-01")
        Interface.objects.filter(pk=interfaces[1].pk).update(mac_address="00-00-00-00-00-02")

        # VirtualChassis assignment for filtering
        virtual_chassis_1 = VirtualChassis.objects.create(name="vc1", master=devices[0])
        Device.objects.filter(pk=devices[0].pk).update(virtual_chassis=virtual_chassis_1, vc_position=1, vc_priority=1)
        Device.objects.filter(pk=devices[1].pk).update(virtual_chassis=virtual_chassis_1, vc_position=2, vc_priority=2)
        virtual_chassis_2 = VirtualChassis.objects.create(name="vc2", master=devices[2])
        Device.objects.filter(pk=devices[2].pk).update(virtual_chassis=virtual_chassis_2, vc_position=1, vc_priority=1)

    def test_face(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"face": [DeviceFaceChoices.FACE_FRONT]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            Device.objects.filter(face=DeviceFaceChoices.FACE_FRONT),
        )

    def test_is_full_depth(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"is_full_depth": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(device_type__is_full_depth=True),
            )
        with self.subTest():
            params = {"is_full_depth": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(device_type__is_full_depth=False),
            )

    def test_serial(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        with self.subTest():
            params = {"serial": "ABC"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        with self.subTest():
            params = {"serial": "abc"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_primary_ip(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"has_primary_ip": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(Q(primary_ip4__isnull=False) | Q(primary_ip6__isnull=False)),
            )
        with self.subTest():
            params = {"has_primary_ip": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(primary_ip4__isnull=True, primary_ip6__isnull=True),
            )

    def test_virtual_chassis_member(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"virtual_chassis_member": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(virtual_chassis__isnull=False),
            )
        with self.subTest():
            params = {"virtual_chassis_member": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(virtual_chassis__isnull=True),
            )

    def test_is_virtual_chassis_member(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"is_virtual_chassis_member": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(virtual_chassis__isnull=False),
            )
        with self.subTest():
            params = {"is_virtual_chassis_member": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(virtual_chassis__isnull=True),
            )

    def test_local_config_context_data(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"local_config_context_data": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(local_config_context_data__isnull=False),
            )
        with self.subTest():
            params = {"local_config_context_data": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                Device.objects.filter(local_config_context_data__isnull=True),
            )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class ConsolePortTestCase(FilterTestCases.FilterTestCase):
    queryset = ConsolePort.objects.all()
    filterset = ConsolePortFilterSet
    generic_filter_tests = [
        ("cable", "cable__id"),
        ("description",),
        ("device", "device__id"),
        ("device", "device__name"),
        ("label",),
        ("name",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        console_server_ports = (
            devices[1].console_server_ports.get(name="Console Server Port 2"),
            devices[2].console_server_ports.get(name="Console Server Port 3"),
        )

        console_ports = (
            devices[0].console_ports.get(name="Console Port 1"),
            devices[1].console_ports.get(name="Console Port 2"),
        )
        console_ports[0].tags.set(Tag.objects.get_for_model(ConsolePort))

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(name="Connected")

        # Cables
        Cable.objects.create(
            termination_a=console_ports[0],
            termination_b=console_server_ports[0],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=console_ports[1],
            termination_b=console_server_ports[1],
            status=status_connected,
        )
        # Third port is not connected

    def test_connected(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class ConsoleServerPortTestCase(FilterTestCases.FilterTestCase):
    queryset = ConsoleServerPort.objects.all()
    filterset = ConsoleServerPortFilterSet
    generic_filter_tests = [
        ("cable", "cable__id"),
        ("description",),
        ("device", "device__id"),
        ("device", "device__name"),
        ("label",),
        ("name",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        console_ports = (
            devices[0].console_ports.get(name="Console Port 1"),
            devices[1].console_ports.get(name="Console Port 2"),
        )

        console_server_ports = (
            devices[1].console_server_ports.get(name="Console Server Port 2"),
            devices[2].console_server_ports.get(name="Console Server Port 3"),
        )
        console_server_ports[0].tags.set(Tag.objects.get_for_model(ConsoleServerPort))

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(name="Connected")

        # Cables
        Cable.objects.create(
            termination_a=console_server_ports[0],
            termination_b=console_ports[0],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=console_server_ports[1],
            termination_b=console_ports[1],
            status=status_connected,
        )
        # Third port is not connected

    def test_connected(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class PowerPortTestCase(FilterTestCases.FilterTestCase):
    queryset = PowerPort.objects.all()
    filterset = PowerPortFilterSet
    generic_filter_tests = [
        ("allocated_draw",),
        ("cable", "cable__id"),
        ("description",),
        ("device", "device__id"),
        ("device", "device__name"),
        ("label",),
        ("maximum_draw",),
        ("name",),
        ("power_outlets", "power_outlets__id"),
        ("power_outlets", "power_outlets__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        power_outlets = (
            devices[1].power_outlets.get(name="Power Outlet 2"),
            devices[2].power_outlets.get(name="Power Outlet 3"),
        )

        power_ports = (
            devices[0].power_ports.get(name="Power Port 1"),
            devices[1].power_ports.get(name="Power Port 2"),
            PowerPort.objects.create(name="Power Port 4", device=devices[2]),
        )
        power_ports[0].tags.set(Tag.objects.get_for_model(PowerPort))
        power_ports[1].tags.set(Tag.objects.get_for_model(PowerPort)[:3])

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(name="Connected")

        # Cables
        Cable.objects.create(
            termination_a=power_ports[0],
            termination_b=power_outlets[0],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=power_ports[1],
            termination_b=power_outlets[1],
            status=status_connected,
        )
        # Third port is not connected

    def test_connected(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class PowerOutletTestCase(FilterTestCases.FilterTestCase):
    queryset = PowerOutlet.objects.all()
    filterset = PowerOutletFilterSet
    generic_filter_tests = [
        ("cable", "cable__id"),
        ("description",),
        ("device", "device__id"),
        ("device", "device__name"),
        ("label",),
        ("name",),
        ("power_port", "power_port__id"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        power_outlets = (
            devices[1].power_outlets.get(name="Power Outlet 2"),
            devices[2].power_outlets.get(name="Power Outlet 3"),
        )
        power_outlets[0].tags.set(Tag.objects.get_for_model(PowerOutlet))
        power_outlets[1].tags.set(Tag.objects.get_for_model(PowerOutlet)[:3])

        power_ports = (
            devices[0].power_ports.get(name="Power Port 1"),
            devices[1].power_ports.get(name="Power Port 2"),
        )

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(name="Connected")

        # Cables
        Cable.objects.create(
            termination_a=power_outlets[0],
            termination_b=power_ports[0],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=power_outlets[1],
            termination_b=power_ports[1],
            status=status_connected,
        )
        # Third port is not connected

    def test_feed_leg(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        params = {"feed_leg": [PowerOutletFeedLegChoices.FEED_LEG_A]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_connected(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class InterfaceTestCase(FilterTestCases.FilterTestCase):
    queryset = Interface.objects.all()
    filterset = InterfaceFilterSet
    generic_filter_tests = [
        ("bridge", "bridge__id"),
        ("bridge", "bridge__name"),
        ("bridged_interfaces", "bridged_interfaces__id"),
        ("bridged_interfaces", "bridged_interfaces__name"),
        ("cable", "cable__id"),
        ("child_interfaces", "child_interfaces__id"),
        ("child_interfaces", "child_interfaces__name"),
        ("description",),
        # ("device", "device__id"),  # TODO - InterfaceFilterSet overrides device as a MultiValueCharFilter on name only
        ("device", "device__name"),
        ("label",),
        ("lag", "lag__id"),
        ("lag", "lag__name"),
        ("mac_address",),
        ("member_interfaces", "member_interfaces__id"),
        ("member_interfaces", "member_interfaces__name"),
        ("mtu",),
        ("name",),
        ("parent_interface", "parent_interface__id"),
        ("parent_interface", "parent_interface__name"),
        ("status", "status__name"),
        ("type",),
        ("tagged_vlans", "tagged_vlans__id"),
        ("tagged_vlans", "tagged_vlans__vid"),
        ("untagged_vlan", "untagged_vlan__id"),
        ("untagged_vlan", "untagged_vlan__vid"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )
        vlans = VLAN.objects.all()[:3]

        interface_statuses = Status.objects.get_for_model(Interface)

        # Cabled interfaces
        cabled_interfaces = (
            Interface.objects.get(name="Interface 1"),
            Interface.objects.get(name="Interface 2"),
            Interface.objects.get(name="Interface 3"),
            Interface.objects.create(
                device=devices[2],
                name="Parent Interface 1",
                type=InterfaceTypeChoices.TYPE_OTHER,
                mode=InterfaceModeChoices.MODE_TAGGED,
                enabled=True,
                mgmt_only=True,
                status=interface_statuses[2],
                untagged_vlan=vlans[2],
            ),
            Interface.objects.create(
                device=devices[2],
                name="Parent Interface 2",
                type=InterfaceTypeChoices.TYPE_OTHER,
                mode=InterfaceModeChoices.MODE_TAGGED,
                enabled=True,
                mgmt_only=True,
                status=interface_statuses[3],
            ),
            Interface.objects.create(
                device=devices[2],
                name="Parent Interface 3",
                type=InterfaceTypeChoices.TYPE_OTHER,
                mode=InterfaceModeChoices.MODE_TAGGED,
                enabled=False,
                mgmt_only=True,
                status=interface_statuses[0],
            ),
        )
        interface_taggable_vlan_1 = VLAN.objects.filter(location=devices[2].location).first()
        interface_taggable_vlan_2 = VLAN.objects.filter(location=devices[2].location).last()

        cabled_interfaces[0].tags.set(Tag.objects.get_for_model(Interface))
        cabled_interfaces[1].tags.set(Tag.objects.get_for_model(Interface)[:3])
        cabled_interfaces[3].tagged_vlans.add(interface_taggable_vlan_1)
        cabled_interfaces[4].tagged_vlans.add(interface_taggable_vlan_1)
        cabled_interfaces[5].tagged_vlans.add(interface_taggable_vlan_2)

        Interface.objects.filter(pk=cabled_interfaces[0].pk).update(
            enabled=True,
            mac_address="00-00-00-00-00-01",
            mode=InterfaceModeChoices.MODE_ACCESS,
            mtu=100,
            status=interface_statuses[0],
            untagged_vlan=vlans[0],
        )

        Interface.objects.filter(pk=cabled_interfaces[1].pk).update(
            enabled=True,
            mac_address="00-00-00-00-00-02",
            mode=InterfaceModeChoices.MODE_TAGGED,
            mtu=200,
            status=interface_statuses[3],
            untagged_vlan=vlans[1],
        )

        Interface.objects.filter(pk=cabled_interfaces[2].pk).update(
            enabled=False,
            mac_address="00-00-00-00-00-03",
            mode=InterfaceModeChoices.MODE_TAGGED_ALL,
            mtu=300,
            status=interface_statuses[2],
        )

        for interface in cabled_interfaces:
            interface.refresh_from_db()

        cable_statuses = Status.objects.get_for_model(Cable)
        connected_status = cable_statuses.get(name="Connected")

        # Cables
        Cable.objects.create(
            termination_a=cabled_interfaces[0],
            termination_b=cabled_interfaces[3],
            status=connected_status,
        )
        Cable.objects.create(
            termination_a=cabled_interfaces[1],
            termination_b=cabled_interfaces[4],
            status=connected_status,
        )
        # Third pair is not connected

        # Child interfaces
        Interface.objects.create(
            device=cabled_interfaces[3].device,
            name="Child 1",
            parent_interface=cabled_interfaces[3],
            status=interface_statuses[3],
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
        )
        Interface.objects.create(
            device=cabled_interfaces[4].device,
            name="Child 2",
            parent_interface=cabled_interfaces[4],
            status=interface_statuses[3],
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
        )
        Interface.objects.create(
            device=cabled_interfaces[5].device,
            name="Child 3",
            parent_interface=cabled_interfaces[5],
            status=interface_statuses[3],
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
        )

        # Bridged interfaces
        bridge_interfaces = (
            Interface.objects.create(
                device=devices[2],
                name="Bridge 1",
                status=interface_statuses[3],
                type=InterfaceTypeChoices.TYPE_BRIDGE,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Bridge 2",
                status=interface_statuses[3],
                type=InterfaceTypeChoices.TYPE_BRIDGE,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Bridge 3",
                status=interface_statuses[3],
                type=InterfaceTypeChoices.TYPE_BRIDGE,
            ),
        )
        Interface.objects.create(
            device=bridge_interfaces[0].device,
            name="Bridged 1",
            bridge=bridge_interfaces[0],
            status=interface_statuses[3],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
        )
        Interface.objects.create(
            device=bridge_interfaces[1].device,
            name="Bridged 2",
            bridge=bridge_interfaces[1],
            status=interface_statuses[3],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
        )
        Interface.objects.create(
            device=bridge_interfaces[2].device,
            name="Bridged 3",
            bridge=bridge_interfaces[2],
            status=interface_statuses[3],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
        )

        # LAG interfaces
        lag_interfaces = (
            Interface.objects.create(
                device=devices[2],
                name="LAG 1",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=interface_statuses[3],
            ),
            Interface.objects.create(
                device=devices[2],
                name="LAG 2",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=interface_statuses[3],
            ),
            Interface.objects.create(
                device=devices[2],
                name="LAG 3",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=interface_statuses[3],
            ),
        )
        Interface.objects.create(
            device=devices[2],
            name="Member 1",
            lag=lag_interfaces[0],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=interface_statuses[3],
        )
        Interface.objects.create(
            device=devices[2],
            name="Member 2",
            lag=lag_interfaces[1],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=interface_statuses[3],
        )
        Interface.objects.create(
            device=devices[2],
            name="Member 3",
            lag=lag_interfaces[2],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=interface_statuses[3],
        )

    def test_connected(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 17)

    def test_enabled(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"enabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 19)
        with self.subTest():
            params = {"enabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_mgmt_only(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"mgmt_only": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"mgmt_only": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 17)

    def test_mode(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"mode": [InterfaceModeChoices.MODE_ACCESS]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device_with_common_vc(self):
        """Assert only interfaces belonging to devices with common VC are returned"""
        device_type = DeviceType.objects.first()
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        devices = (
            Device.objects.create(
                name="Device in vc 1",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=self.loc1,
            ),
            Device.objects.create(
                name="Device in vc 2",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=self.loc1,
            ),
            Device.objects.create(
                name="Device not in vc",
                device_type=device_type,
                role=device_role,
                status=device_status,
                location=self.loc1,
            ),
        )

        # VirtualChassis assignment for filtering
        virtual_chassis = VirtualChassis.objects.create(master=devices[0])
        Device.objects.filter(pk=devices[0].pk).update(virtual_chassis=virtual_chassis, vc_position=1, vc_priority=1)
        Device.objects.filter(pk=devices[1].pk).update(virtual_chassis=virtual_chassis, vc_position=2, vc_priority=2)

        interface_status = Status.objects.get_for_model(Interface).first()
        Interface.objects.create(device=devices[0], name="int1", status=interface_status)
        Interface.objects.create(device=devices[0], name="int2", status=interface_status)
        Interface.objects.create(device=devices[1], name="int3", status=interface_status)
        Interface.objects.create(device=devices[2], name="int4", status=interface_status)

        params = {"device_with_common_vc": devices[0].pk}
        queryset = self.filterset(params, self.queryset).qs

        # Capture the first device so that we can use it in the next test.
        device = Device.objects.get(pk=devices[0].pk)
        with self.subTest():
            self.assertQuerysetEqual(
                queryset,
                self.queryset.filter(pk__in=device.common_vc_interfaces.values_list("pk", flat=True)),
            )
        # Assert interface of a device belonging to same VC as `device` are returned
        with self.subTest():
            self.assertTrue(queryset.filter(name="int3").exists())

        # Assert interface of a device not belonging as `device` to same VC are not returned
        with self.subTest():
            self.assertFalse(queryset.filter(name="int4").exists())

    def test_kind(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        with self.subTest():
            params = {"kind": "physical"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 12)
        with self.subTest():
            params = {"kind": "virtual"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 9)

    def test_vlan(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        vlan = VLAN.objects.filter(
            Q(interfaces_as_untagged__isnull=False) | Q(interfaces_as_tagged__isnull=False)
        ).first()
        params = {"vlan": vlan.vid}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(Q(untagged_vlan=vlan) | Q(tagged_vlans=vlan))
        )

    def test_vlan_id(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        vlan = VLAN.objects.filter(
            Q(interfaces_as_untagged__isnull=False) | Q(interfaces_as_tagged__isnull=False)
        ).first()
        params = {"vlan_id": vlan.id}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(Q(untagged_vlan=vlan) | Q(tagged_vlans=vlan))
        )


class FrontPortTestCase(FilterTestCases.FilterTestCase):
    queryset = FrontPort.objects.all()
    filterset = FrontPortFilterSet
    generic_filter_tests = [
        ("description",),
        ("cable", "cable__id"),
        ("device", "device__id"),
        ("device", "device__name"),
        ("label",),
        ("name",),
        ("rear_port", "rear_port__id"),
        ("rear_port", "rear_port__name"),
        ("rear_port_position",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        rear_ports = (
            devices[0].rear_ports.get(name="Rear Port 1"),
            devices[1].rear_ports.get(name="Rear Port 2"),
            devices[2].rear_ports.get(name="Rear Port 3"),
            RearPort.objects.create(
                device=devices[2],
                name="Rear Port 4",
                type=PortTypeChoices.TYPE_8P8C,
                positions=6,
            ),
            RearPort.objects.create(
                device=devices[2],
                name="Rear Port 5",
                type=PortTypeChoices.TYPE_8P8C,
                positions=6,
            ),
        )

        front_ports = (
            devices[0].front_ports.get(name="Front Port 1"),
            devices[1].front_ports.get(name="Front Port 2"),
            devices[2].front_ports.get(name="Front Port 3"),
            FrontPort.objects.create(
                device=devices[2],
                name="Front Port 4",
                type=PortTypeChoices.TYPE_FC,
                rear_port=rear_ports[3],
                rear_port_position=1,
            ),
            FrontPort.objects.create(
                device=devices[2],
                name="Front Port 5",
                type=PortTypeChoices.TYPE_FC,
                rear_port=rear_ports[4],
                rear_port_position=1,
            ),
        )
        front_ports[0].tags.set(Tag.objects.get_for_model(FrontPort))
        front_ports[1].tags.set(Tag.objects.get_for_model(FrontPort)[:3])

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(name="Connected")

        # Cables
        Cable.objects.create(
            termination_a=front_ports[0],
            termination_b=front_ports[3],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=front_ports[1],
            termination_b=front_ports[4],
            status=status_connected,
        )
        # Third port is not connected

    def test_type(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"type": [PortTypeChoices.TYPE_8P8C]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class RearPortTestCase(FilterTestCases.FilterTestCase):
    queryset = RearPort.objects.all()
    filterset = RearPortFilterSet
    generic_filter_tests = [
        ("cable", "cable__id"),
        ("description",),
        ("device", "device__id"),
        ("device", "device__name"),
        ("front_ports", "front_ports__id"),
        ("front_ports", "front_ports__name"),
        ("label",),
        ("name",),
        ("positions",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        rear_ports = (
            devices[0].rear_ports.get(name="Rear Port 1"),
            devices[1].rear_ports.get(name="Rear Port 2"),
            devices[2].rear_ports.get(name="Rear Port 3"),
            RearPort.objects.create(
                device=devices[2],
                name="Rear Port 4",
                type=PortTypeChoices.TYPE_8P8C,
                positions=6,
            ),
            RearPort.objects.create(
                device=devices[2],
                name="Rear Port 5",
                type=PortTypeChoices.TYPE_8P8C,
                positions=6,
            ),
        )
        rear_ports[0].tags.set(Tag.objects.get_for_model(RearPort))
        rear_ports[1].tags.set(Tag.objects.get_for_model(RearPort)[:3])

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(name="Connected")

        # Cables
        Cable.objects.create(
            termination_a=rear_ports[0],
            termination_b=rear_ports[3],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=rear_ports[1],
            termination_b=rear_ports[4],
            status=status_connected,
        )
        # Third port is not connected

    def test_type(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"type": [PortTypeChoices.TYPE_8P8C]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)


class DeviceBayTestCase(FilterTestCases.FilterTestCase):
    queryset = DeviceBay.objects.all()
    filterset = DeviceBayFilterSet
    generic_filter_tests = [
        ("description",),
        ("device", "device__id"),
        ("device", "device__name"),
        ("installed_device", "installed_device__id"),
        ("installed_device", "installed_device__name"),
        ("label",),
        ("name",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        device_role = Role.objects.get_for_model(Device).first()
        parent_device_type = DeviceType.objects.get(model="Model 2")
        child_device_type = DeviceType.objects.get(model="Model 3")

        device_statuses = Status.objects.get_for_model(Device)

        child_devices = (
            Device.objects.create(
                name="Child Device 1",
                device_type=child_device_type,
                role=device_role,
                location=cls.loc1,
                status=device_statuses[0],
            ),
            Device.objects.create(
                name="Child Device 2",
                device_type=child_device_type,
                role=device_role,
                location=cls.loc1,
                status=device_statuses[0],
            ),
        )

        parent_devices = (
            Device.objects.create(
                name="Parent Device 1",
                device_type=parent_device_type,
                role=device_role,
                location=cls.loc1,
                status=device_statuses[0],
            ),
            Device.objects.create(
                name="Parent Device 2",
                device_type=parent_device_type,
                role=device_role,
                location=cls.loc1,
                status=device_statuses[0],
            ),
        )

        device_bays = (
            parent_devices[0].device_bays.first(),
            parent_devices[1].device_bays.first(),
        )
        device_bays[0].tags.set(Tag.objects.get_for_model(DeviceBay))
        device_bays[0].installed_device = child_devices[0]
        device_bays[1].installed_device = child_devices[1]
        device_bays[0].save()
        device_bays[1].save()


class InventoryItemTestCase(FilterTestCases.FilterTestCase):
    queryset = InventoryItem.objects.all()
    filterset = InventoryItemFilterSet
    generic_filter_tests = [
        ("asset_tag",),
        ("children", "children__id"),
        ("description",),
        ("device", "device__id"),
        ("device", "device__name"),
        ("label",),
        ("manufacturer", "manufacturer__id"),
        ("manufacturer", "manufacturer__name"),
        ("name",),
        ("parent", "parent__id"),
        ("parent", "parent__name"),
        ("part_id",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        inventory_items = (
            InventoryItem.objects.create(
                device=devices[0],
                manufacturer=cls.manufacturers[0],
                name="Inventory Item 1",
                part_id="1001",
                serial="ABC",
                asset_tag="1001",
                discovered=True,
                description="First",
                label="inventoryitem1",
            ),
            InventoryItem.objects.create(
                device=devices[1],
                manufacturer=cls.manufacturers[1],
                name="Inventory Item 2",
                part_id="1002",
                serial="DEF",
                asset_tag="1002",
                discovered=True,
                description="Second",
                label="inventoryitem2",
            ),
            InventoryItem.objects.create(
                device=devices[2],
                manufacturer=cls.manufacturers[2],
                name="Inventory Item 3",
                part_id="1003",
                serial="GHI",
                asset_tag="1003",
                discovered=False,
                description="Third",
                label="inventoryitem3",
            ),
        )
        inventory_items[0].tags.set(Tag.objects.get_for_model(InventoryItem))
        inventory_items[1].tags.set(Tag.objects.get_for_model(InventoryItem)[:3])

        InventoryItem.objects.create(device=devices[0], name="Inventory Item 1A", parent=inventory_items[0])
        InventoryItem.objects.create(device=devices[1], name="Inventory Item 2A", parent=inventory_items[1])
        InventoryItem.objects.create(device=devices[2], name="Inventory Item 3A", parent=inventory_items[2])

    def test_discovered(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        # 2.0 TODO: Fix boolean value
        with self.subTest():
            params = {"discovered": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"discovered": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_serial(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        with self.subTest():
            params = {"serial": "ABC"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        with self.subTest():
            params = {"serial": "abc"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class VirtualChassisTestCase(FilterTestCases.FilterTestCase):
    queryset = VirtualChassis.objects.all()
    filterset = VirtualChassisFilterSet
    generic_filter_tests = [
        ("domain",),
        ("master", "master__id"),
        ("master", "master__name"),
        ("members", "members__id"),
        ("name",),
    ]

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Model 1")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()

        cls.locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:3]
        devices = (
            Device.objects.create(
                name="Device 1",
                device_type=device_type,
                role=device_role,
                location=cls.locations[0],
                vc_position=1,
                status=device_status,
            ),
            Device.objects.create(
                name="Device 2",
                device_type=device_type,
                role=device_role,
                location=cls.locations[0],
                vc_position=2,
                status=device_status,
            ),
            Device.objects.create(
                name="Device 3",
                device_type=device_type,
                role=device_role,
                location=cls.locations[1],
                vc_position=1,
                status=device_status,
            ),
            Device.objects.create(
                name="Device 4",
                device_type=device_type,
                role=device_role,
                location=cls.locations[1],
                vc_position=2,
                status=device_status,
            ),
            Device.objects.create(
                name="Device 5",
                device_type=device_type,
                role=device_role,
                location=cls.locations[2],
                vc_position=1,
                status=device_status,
            ),
            Device.objects.create(
                name="Device 6",
                device_type=device_type,
                role=device_role,
                location=cls.locations[2],
                vc_position=2,
                status=device_status,
            ),
        )

        virtual_chassis = (
            VirtualChassis.objects.create(name="VC 1", master=devices[0], domain="Domain 1"),
            VirtualChassis.objects.create(name="VC 2", master=devices[2], domain="Domain 2"),
            VirtualChassis.objects.create(name="VC 3", master=devices[4], domain="Domain 3"),
            VirtualChassis.objects.create(name="VC 4"),
        )
        virtual_chassis[0].tags.set(Tag.objects.get_for_model(VirtualChassis))
        virtual_chassis[1].tags.set(Tag.objects.get_for_model(VirtualChassis)[:3])

        Device.objects.filter(pk=devices[1].pk).update(virtual_chassis=virtual_chassis[0])
        Device.objects.filter(pk=devices[3].pk).update(virtual_chassis=virtual_chassis[1])
        Device.objects.filter(pk=devices[5].pk).update(virtual_chassis=virtual_chassis[2])

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class CableTestCase(FilterTestCases.FilterTestCase):
    queryset = Cable.objects.all()
    filterset = CableFilterSet
    generic_filter_tests = [
        ("color",),
        ("label",),
        ("length",),
        ("status", "status__name"),
        ("termination_a_id",),
        ("termination_b_id",),
        ("type",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        tenants = Tenant.objects.all()[:3]

        cls.locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:3]
        racks = (
            Rack.objects.get(name="Rack 1"),
            Rack.objects.get(name="Rack 2"),
            Rack.objects.get(name="Rack 3"),
        )

        device_types = (
            DeviceType.objects.get(model="Model 1"),
            DeviceType.objects.get(model="Model 2"),
            DeviceType.objects.get(model="Model 3"),
        )

        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
            Device.objects.create(
                name="Device 4",
                device_type=device_types[0],
                role=device_role,
                status=device_status,
                tenant=tenants[0],
                location=cls.locations[0],
                rack=racks[0],
                position=2,
            ),
            Device.objects.create(
                name="Device 5",
                device_type=device_types[1],
                role=device_role,
                status=device_status,
                tenant=tenants[1],
                location=cls.locations[1],
                rack=racks[1],
                position=1,
            ),
            Device.objects.create(
                name="Device 6",
                device_type=device_types[2],
                role=device_role,
                status=device_status,
                tenant=tenants[2],
                location=cls.locations[2],
                rack=racks[2],
                position=2,
            ),
        )

        interface_status = Status.objects.get_for_model(Interface).first()
        interfaces = (
            Interface.objects.get(device__name="Device 1"),
            Interface.objects.get(device__name="Device 2"),
            Interface.objects.get(device__name="Device 3"),
            Interface.objects.get(device__name="Device 4"),
            Interface.objects.get(device__name="Device 5"),
            Interface.objects.get(device__name="Device 6"),
            Interface.objects.create(
                device=devices[0],
                name="Interface 7",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Interface 8",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Interface 9",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[3],
                name="Interface 10",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[4],
                name="Interface 11",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[5],
                name="Interface 12",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
        )

        statuses = Status.objects.get_for_model(Cable)
        cls.status_connected = statuses.get(name="Connected")
        cls.status_decommissioning = statuses.get(name="Decommissioning")
        cls.status_planned = statuses.get(name="Planned")

        console_port = ConsolePort.objects.filter(device=devices[2]).first()
        console_server_port = ConsoleServerPort.objects.filter(device=devices[5]).first()

        # Cables
        cables = (
            Cable.objects.create(
                termination_a=interfaces[0],
                termination_b=interfaces[3],
                label="Cable 1",
                type=CableTypeChoices.TYPE_MMF,
                status=cls.status_connected,
                color="aa1409",
                length=10,
                length_unit=CableLengthUnitChoices.UNIT_FOOT,
            ),
            Cable.objects.create(
                termination_a=interfaces[1],
                termination_b=interfaces[4],
                label="Cable 2",
                type=CableTypeChoices.TYPE_MMF,
                status=cls.status_connected,
                color="aa1409",
                length=20,
                length_unit=CableLengthUnitChoices.UNIT_FOOT,
            ),
            Cable.objects.create(
                termination_a=interfaces[2],
                termination_b=interfaces[5],
                label="Cable 3",
                type=CableTypeChoices.TYPE_CAT5E,
                status=cls.status_connected,
                color="f44336",
                length=30,
                length_unit=CableLengthUnitChoices.UNIT_FOOT,
            ),
            Cable.objects.create(
                termination_a=interfaces[6],
                termination_b=interfaces[9],
                label="Cable 4",
                type=CableTypeChoices.TYPE_CAT5E,
                status=cls.status_planned,
                color="f44336",
                length=40,
                length_unit=CableLengthUnitChoices.UNIT_FOOT,
            ),
            Cable.objects.create(
                termination_a=interfaces[7],
                termination_b=interfaces[10],
                label="Cable 5",
                type=CableTypeChoices.TYPE_CAT6,
                status=cls.status_planned,
                color="e91e63",
                length=10,
                length_unit=CableLengthUnitChoices.UNIT_METER,
            ),
            Cable.objects.create(
                termination_a=console_port,
                termination_b=console_server_port,
                label="Cable 6",
                type=CableTypeChoices.TYPE_CAT6,
                status=cls.status_decommissioning,
                color="e91e63",
                length=20,
                length_unit=CableLengthUnitChoices.UNIT_METER,
            ),
        )
        cables[0].tags.set(Tag.objects.get_for_model(Cable))
        cables[1].tags.set(Tag.objects.get_for_model(Cable)[:3])

    def test_length_unit(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"length_unit": [CableLengthUnitChoices.UNIT_FOOT]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_device(self):
        # TODO: Not a generic_filter_test because this is a method filter.
        devices = [
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
        ]
        with self.subTest():
            params = {"device_id": [devices[0].pk, devices[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"device": [devices[0].name, devices[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_rack(self):
        # TODO: Not a generic_filter_test because this is a method filter.
        racks = Rack.objects.all()[:2]
        with self.subTest():
            params = {"rack_id": [racks[0].pk, racks[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"rack": [racks[0].name, racks[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_tenant(self):
        # TODO: Not a generic_filter_test because this is a method filter.
        tenants = list(Tenant.objects.filter(devices__isnull=False))[:2]
        with self.subTest():
            params = {"tenant_id": [tenants[0].pk, tenants[1].pk]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(
                    Q(_termination_a_device__tenant__in=tenants) | Q(_termination_b_device__tenant__in=tenants)
                ),
            )
        with self.subTest():
            params = {"tenant": [tenants[0].name, tenants[1].name]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(
                    Q(_termination_a_device__tenant__in=tenants) | Q(_termination_b_device__tenant__in=tenants)
                ),
            )

    def test_termination_type(self):
        # TODO: Not a generic_filter_test because we only have one valid value in the current test data (interface),
        #       plus the filter expects content-type strings, but the generic test would use content-type IDs.
        type_interface = "dcim.interface"
        type_console_port = "dcim.consoleport"
        type_console_server_port = "dcim.consoleserverport"
        with self.subTest():
            params = {"termination_a_type": [type_interface, type_console_port]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 6)
        with self.subTest():
            params = {"termination_a_type": [type_interface]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)
        with self.subTest():
            params = {"termination_b_type": [type_interface, type_console_server_port]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 6)
        with self.subTest():
            params = {"termination_b_type": [type_interface]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)
        with self.subTest():
            params = {"termination_type": [type_interface]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)
        with self.subTest():
            params = {"termination_type": [type_console_port, type_console_server_port]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class PowerPanelTestCase(FilterTestCases.FilterTestCase):
    queryset = PowerPanel.objects.all()
    filterset = PowerPanelFilterSet
    generic_filter_tests = [
        ("name",),
        ("power_feeds", "power_feeds__id"),
        ("power_feeds", "power_feeds__name"),
        ("rack_group", "rack_group__id"),
        ("rack_group", "rack_group__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        PowerPanel.objects.create(name="Power Panel 4", location=cls.loc1)


class PowerFeedTestCase(FilterTestCases.FilterTestCase):
    queryset = PowerFeed.objects.all()
    filterset = PowerFeedFilterSet
    generic_filter_tests = [
        ("amperage",),
        ("available_power",),
        ("cable", "cable__id"),
        ("comments",),
        ("max_utilization",),
        ("name",),
        ("power_panel", "power_panel__id"),
        ("power_panel", "power_panel__name"),
        ("rack", "rack__id"),
        ("rack", "rack__name"),
        ("status", "status__name"),
        ("voltage",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        power_feeds = (
            PowerFeed.objects.get(name="Power Feed 1"),
            PowerFeed.objects.get(name="Power Feed 2"),
            PowerFeed.objects.get(name="Power Feed 3"),
        )

        pf_statuses = Status.objects.get_for_model(PowerFeed)

        PowerFeed.objects.filter(pk=power_feeds[0].pk).update(
            status=pf_statuses[0],
            type=PowerFeedTypeChoices.TYPE_PRIMARY,
            supply=PowerFeedSupplyChoices.SUPPLY_AC,
            phase=PowerFeedPhaseChoices.PHASE_3PHASE,
            voltage=100,
            amperage=100,
            max_utilization=10,
            comments="PFA",
        )
        PowerFeed.objects.filter(pk=power_feeds[1].pk).update(
            status=pf_statuses[1],
            type=PowerFeedTypeChoices.TYPE_PRIMARY,
            supply=PowerFeedSupplyChoices.SUPPLY_AC,
            phase=PowerFeedPhaseChoices.PHASE_3PHASE,
            voltage=200,
            amperage=200,
            max_utilization=20,
            comments="PFB",
        )
        PowerFeed.objects.filter(pk=power_feeds[2].pk).update(
            status=pf_statuses[2],
            type=PowerFeedTypeChoices.TYPE_REDUNDANT,
            supply=PowerFeedSupplyChoices.SUPPLY_DC,
            phase=PowerFeedPhaseChoices.PHASE_SINGLE,
            voltage=300,
            amperage=300,
            max_utilization=30,
            comments="PFC",
        )

        power_feeds[0].refresh_from_db()
        power_feeds[1].refresh_from_db()
        power_feeds[2].refresh_from_db()
        power_feeds[0].validated_save()
        power_feeds[1].validated_save()
        power_feeds[2].validated_save()

        power_ports = (
            PowerPort.objects.get(name="Power Port 1"),
            PowerPort.objects.get(name="Power Port 2"),
        )

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(name="Connected")

        Cable.objects.create(
            termination_a=power_feeds[0],
            termination_b=power_ports[0],
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=power_feeds[1],
            termination_b=power_ports[1],
            status=status_connected,
        )

    def test_type(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"type": [PowerFeedTypeChoices.TYPE_PRIMARY]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_supply(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"supply": [PowerFeedSupplyChoices.SUPPLY_AC]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_phase(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        params = {"phase": [PowerFeedPhaseChoices.PHASE_3PHASE]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_connected(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class DeviceRedundancyGroupTestCase(FilterTestCases.FilterTestCase):
    queryset = DeviceRedundancyGroup.objects.all()
    filterset = DeviceRedundancyGroupFilterSet
    generic_filter_tests = [
        ("name",),
        ("secrets_group", "secrets_group__id"),
        ("secrets_group", "secrets_group__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        device_redundancy_groups = list(DeviceRedundancyGroup.objects.all()[:2])

        secrets_groups = list(SecretsGroup.objects.all()[:2])

        device_redundancy_groups[0].secrets_group = secrets_groups[0]
        device_redundancy_groups[0].validated_save()

        device_redundancy_groups[1].secrets_group = secrets_groups[1]
        device_redundancy_groups[1].validated_save()

    def test_failover_strategy(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        with self.subTest():
            params = {"failover_strategy": ["active-active"]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                DeviceRedundancyGroup.objects.filter(failover_strategy="active-active"),
            )
        with self.subTest():
            params = {"failover_strategy": ["active-passive"]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                DeviceRedundancyGroup.objects.filter(failover_strategy="active-passive"),
            )


# TODO: Connection filters


class InterfaceRedundancyGroupTestCase(FilterTestCases.FilterTestCase):
    queryset = InterfaceRedundancyGroup.objects.all()
    filterset = InterfaceRedundancyGroupFilterSet

    generic_filter_tests = (
        ["name"],
        ["secrets_group", "secrets_group__id"],
        ["secrets_group", "secrets_group__name"],
        ["protocol"],
        ["protocol_group_id"],
    )

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        statuses = Status.objects.get_for_model(InterfaceRedundancyGroup)
        cls.ips = IPAddress.objects.all()

        interface_redundancy_groups = (
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 1",
                protocol="hsrp",
                protocol_group_id="1",
                status=statuses[0],
                virtual_ip=cls.ips[0],
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 2",
                protocol="carp",
                protocol_group_id="2",
                status=statuses[1],
                virtual_ip=cls.ips[1],
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 3",
                protocol="vrrp",
                protocol_group_id="3",
                status=statuses[2],
                virtual_ip=cls.ips[2],
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 4",
                protocol="glbp",
                protocol_group_id="4",
                status=statuses[3],
                virtual_ip=cls.ips[3],
            ),
        )
        tags = Tag.objects.get_for_model(InterfaceRedundancyGroup)
        for group in interface_redundancy_groups:
            group.tags.set(tags)
            group.validated_save()

        secrets_groups = list(SecretsGroup.objects.all()[:2])

        interface_redundancy_groups[0].secrets_group = secrets_groups[0]
        interface_redundancy_groups[0].validated_save()

        interface_redundancy_groups[1].secrets_group = secrets_groups[1]
        interface_redundancy_groups[1].validated_save()

    def test_virtual_ip(self):
        with self.subTest():
            params = {"virtual_ip": [self.ips[0].pk, self.ips[1].pk]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                InterfaceRedundancyGroup.objects.filter(virtual_ip__in=params["virtual_ip"]),
            )
        with self.subTest():
            params = {"virtual_ip": [str(self.ips[2].address), str(self.ips[3].address)]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                InterfaceRedundancyGroup.objects.filter(virtual_ip__in=[self.ips[2], self.ips[3]]),
            )


class InterfaceRedundancyGroupAssociationTestCase(FilterTestCases.FilterTestCase):
    queryset = InterfaceRedundancyGroupAssociation.objects.all()
    filterset = InterfaceRedundancyGroupAssociationFilterSet
    generic_filter_tests = (
        ["interface_redundancy_group", "interface_redundancy_group__id"],
        ["interface_redundancy_group", "interface_redundancy_group__name"],
        ["interface", "interface__id"],
        ["interface", "interface__name"],
        ["priority"],
    )

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        statuses = Status.objects.get_for_model(InterfaceRedundancyGroup)
        cls.ips = IPAddress.objects.all()
        cls.interfaces = Interface.objects.all()[:4]

        interface_redundancy_groups = (
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 1",
                protocol="hsrp",
                status=statuses[0],
                virtual_ip=cls.ips[0],
                protocol_group_id="2",
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 2",
                protocol="carp",
                status=statuses[1],
                virtual_ip=cls.ips[1],
                protocol_group_id="3",
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 3",
                protocol="vrrp",
                status=statuses[2],
                virtual_ip=cls.ips[2],
                protocol_group_id="1",
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 4",
                protocol="glbp",
                status=statuses[3],
                virtual_ip=cls.ips[3],
                protocol_group_id="4",
            ),
        )

        for group in interface_redundancy_groups:
            group.validated_save()

        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 4"),
            SecretsGroup.objects.create(name="Secrets Group 5"),
            SecretsGroup.objects.create(name="Secrets Group 6"),
        )

        interface_redundancy_groups[0].secrets_group = secrets_groups[0]
        interface_redundancy_groups[0].validated_save()

        interface_redundancy_groups[1].secrets_group = secrets_groups[1]
        interface_redundancy_groups[1].validated_save()

        for i, interface in enumerate(cls.interfaces):
            interface_redundancy_groups[i].add_interface(interface, 100 * i)
