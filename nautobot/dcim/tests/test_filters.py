import netaddr
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

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
    DeviceRoleFilterSet,
    DeviceTypeFilterSet,
    FrontPortFilterSet,
    FrontPortTemplateFilterSet,
    InterfaceFilterSet,
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
    RackRoleFilterSet,
    RearPortFilterSet,
    RearPortTemplateFilterSet,
    RegionFilterSet,
    SiteFilterSet,
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
    DeviceRole,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
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
    RackRole,
    RearPort,
    RearPortTemplate,
    Region,
    Site,
    VirtualChassis,
)
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.extras.models import SecretsGroup, Status
from nautobot.ipam.models import IPAddress, Prefix, Service, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.utilities.testing import FilterTestCases
from nautobot.utilities.utils import flatten_iterable
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine


# Use the proper swappable User model
User = get_user_model()


def common_test_data(cls):

    tenants = Tenant.objects.filter(group__isnull=False)
    cls.tenants = tenants

    regions = (
        Region.objects.create(name="Region 1", slug="region-1", description="A"),
        Region.objects.create(name="Region 2", slug="region-2", description="B"),
        Region.objects.create(name="Region 3", slug="region-3", description="C"),
    )
    cls.regions = regions

    site_statuses = Status.objects.get_for_model(Site)
    cls.site_status_map = {s.slug: s for s in site_statuses.all()}

    sites = (
        Site.objects.create(
            name="Site 1",
            slug="site-1",
            description="Site 1 description",
            region=regions[0],
            tenant=tenants[0],
            status=cls.site_status_map["active"],
            facility="Facility 1",
            asn=65001,
            latitude=10,
            longitude=10,
            contact_name="Contact 1",
            contact_phone="123-555-0001",
            contact_email="contact1@example.com",
            physical_address="1 road st, albany, ny",
            shipping_address="PO Box 1, albany, ny",
            comments="comment1",
            time_zone="America/Chicago",
        ),
        Site.objects.create(
            name="Site 2",
            slug="site-2",
            description="Site 2 description",
            region=regions[1],
            tenant=tenants[1],
            status=cls.site_status_map["planned"],
            facility="Facility 2",
            asn=65002,
            latitude=20,
            longitude=20,
            contact_name="Contact 2",
            contact_phone="123-555-0002",
            contact_email="contact2@example.com",
            physical_address="2 road st, albany, ny",
            shipping_address="PO Box 2, albany, ny",
            comments="comment2",
            time_zone="America/Los_Angeles",
        ),
        Site.objects.create(
            name="Site 3",
            slug="site-3",
            region=regions[2],
            tenant=tenants[2],
            status=cls.site_status_map["retired"],
            facility="Facility 3",
            asn=65003,
            latitude=30,
            longitude=30,
            contact_name="Contact 3",
            contact_phone="123-555-0003",
            contact_email="contact3@example.com",
            comments="comment3",
            time_zone="America/Detroit",
        ),
    )

    provider = Provider.objects.create(name="Provider 1", slug="provider-1", asn=65001, account="1234")
    circuit_type = CircuitType.objects.create(name="Test Circuit Type 1", slug="test-circuit-type-1")
    circuit = Circuit.objects.create(provider=provider, type=circuit_type, cid="Test Circuit 1")
    CircuitTermination.objects.create(circuit=circuit, site=sites[0], term_side="A")
    CircuitTermination.objects.create(circuit=circuit, site=sites[1], term_side="Z")

    manufacturers = list(Manufacturer.objects.all()[:3])
    cls.manufacturers = manufacturers

    platforms = (
        Platform.objects.create(
            name="Platform 1",
            slug="platform-1",
            manufacturer=manufacturers[0],
            napalm_driver="driver-1",
            napalm_args=["--test", "--arg1"],
            description="A",
        ),
        Platform.objects.create(
            name="Platform 2",
            slug="platform-2",
            manufacturer=manufacturers[1],
            napalm_driver="driver-2",
            napalm_args=["--test", "--arg2"],
            description="B",
        ),
        Platform.objects.create(
            name="Platform 3",
            slug="platform-3",
            manufacturer=manufacturers[2],
            napalm_driver="driver-3",
            napalm_args=["--test", "--arg3"],
            description="C",
        ),
    )
    cls.platforms = platforms

    device_types = (
        DeviceType.objects.create(
            manufacturer=manufacturers[0],
            comments="Device type 1",
            model="Model 1",
            slug="model-1",
            part_number="Part Number 1",
            u_height=1,
            is_full_depth=True,
        ),
        DeviceType.objects.create(
            manufacturer=manufacturers[1],
            comments="Device type 2",
            model="Model 2",
            slug="model-2",
            part_number="Part Number 2",
            u_height=2,
            is_full_depth=True,
            subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
        ),
        DeviceType.objects.create(
            manufacturer=manufacturers[2],
            comments="Device type 3",
            model="Model 3",
            slug="model-3",
            part_number="Part Number 3",
            u_height=3,
            is_full_depth=False,
            subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
        ),
    )
    cls.device_types = device_types

    rack_groups = (
        RackGroup.objects.create(name="Rack Group 1", slug="rack-group-1", site=sites[0]),
        RackGroup.objects.create(name="Rack Group 2", slug="rack-group-2", site=sites[1]),
        RackGroup.objects.create(name="Rack Group 3", slug="rack-group-3", site=sites[2]),
    )

    power_panels = (
        PowerPanel.objects.create(name="Power Panel 1", site=sites[0], rack_group=rack_groups[0]),
        PowerPanel.objects.create(name="Power Panel 2", site=sites[1], rack_group=rack_groups[1]),
        PowerPanel.objects.create(name="Power Panel 3", site=sites[2], rack_group=rack_groups[2]),
    )

    rackroles = (
        RackRole.objects.create(name="Rack Role 1", slug="rack-role-1", color="ff0000"),
        RackRole.objects.create(name="Rack Role 2", slug="rack-role-2", color="00ff00"),
        RackRole.objects.create(name="Rack Role 3", slug="rack-role-3", color="0000ff"),
    )

    rack_statuses = Status.objects.get_for_model(Rack)
    cls.rack_status_map = {s.slug: s for s in rack_statuses.all()}

    racks = (
        Rack.objects.create(
            name="Rack 1",
            comments="comment1",
            facility_id="rack-1",
            site=sites[0],
            group=rack_groups[0],
            tenant=tenants[0],
            status=cls.rack_status_map["active"],
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
            site=sites[1],
            group=rack_groups[1],
            tenant=tenants[1],
            status=cls.rack_status_map["planned"],
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
            site=sites[2],
            group=rack_groups[2],
            tenant=tenants[2],
            status=cls.rack_status_map["reserved"],
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

    device_roles = (
        DeviceRole.objects.create(
            name="Device Role 1",
            slug="device-role-1",
            color="ff0000",
            vm_role=False,
            description="Device Role Description 1",
        ),
        DeviceRole.objects.create(
            name="Device Role 2",
            slug="device-role-2",
            color="00ff00",
            vm_role=False,
            description="Device Role Description 2",
        ),
        DeviceRole.objects.create(
            name="Device Role 3",
            slug="device-role-3",
            color="0000ff",
            vm_role=False,
            description="Device Role Description 3",
        ),
    )
    cls.device_roles = device_roles

    cluster_type = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
    clusters = (
        Cluster.objects.create(name="Cluster 1", type=cluster_type, site=sites[0]),
        Cluster.objects.create(name="Cluster 2", type=cluster_type, site=sites[1]),
        Cluster.objects.create(name="Cluster 3", type=cluster_type, site=sites[2]),
    )

    VirtualMachine.objects.create(cluster=clusters[0], name="VM 1", role=device_roles[0], platform=platforms[0])
    VirtualMachine.objects.create(cluster=clusters[0], name="VM 2", role=device_roles[1], platform=platforms[1])
    VirtualMachine.objects.create(cluster=clusters[0], name="VM 3", role=device_roles[2], platform=platforms[2])

    Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.0.0/16"), site=sites[0])
    Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.1.0/24"), site=sites[1])
    Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.2.0/24"), site=sites[2])

    # TODO: remove these once we have a Sites fixture; for now SiteTestCase needs VLANGroups and VLANs with Sites
    VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=sites[0])
    VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=sites[1])
    VLANGroup.objects.create(name="VLAN Group 3", slug="vlan-group-3", site=sites[2])

    VLAN.objects.create(name="VLAN 101", vid=101, site=sites[0])
    VLAN.objects.create(name="VLAN 102", vid=102, site=sites[1])
    VLAN.objects.create(name="VLAN 103", vid=103, site=sites[2])

    PowerFeed.objects.create(name="Power Feed 1", rack=racks[0], power_panel=power_panels[0])
    PowerFeed.objects.create(name="Power Feed 2", rack=racks[1], power_panel=power_panels[1])
    PowerFeed.objects.create(name="Power Feed 3", rack=racks[2], power_panel=power_panels[2])

    users = (
        User.objects.create_user(username="TestCaseUser 1"),
        User.objects.create_user(username="TestCaseUser 2"),
        User.objects.create_user(username="TestCaseUser 3"),
    )

    RackReservation.objects.create(
        rack=racks[0],
        units=(1, 2, 3),
        user=users[0],
        description="Rack Reservation 1",
        tenant=tenants[0],
    )
    RackReservation.objects.create(
        rack=racks[1],
        units=(4, 5, 6),
        user=users[1],
        description="Rack Reservation 2",
        tenant=tenants[1],
    )
    RackReservation.objects.create(
        rack=racks[2],
        units=(7, 8, 9),
        user=users[2],
        description="Rack Reservation 3",
        tenant=tenants[2],
    )

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
        power_port=power_port_templates[0],
        name="Power Outlet 1",
        feed_leg=PowerOutletFeedLegChoices.FEED_LEG_A,
        label="poweroutlet1",
        description="Power Outlet Description 1",
    )
    PowerOutletTemplate.objects.create(
        device_type=device_types[1],
        power_port=power_port_templates[1],
        name="Power Outlet 2",
        feed_leg=PowerOutletFeedLegChoices.FEED_LEG_B,
        label="poweroutlet2",
        description="Power Outlet Description 2",
    )
    PowerOutletTemplate.objects.create(
        device_type=device_types[2],
        power_port=power_port_templates[2],
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
        rear_port=rear_ports[0],
        type=PortTypeChoices.TYPE_8P8C,
        rear_port_position=1,
        label="frontport1",
        description="Front Port Description 1",
    )
    FrontPortTemplate.objects.create(
        device_type=device_types[1],
        name="Front Port 2",
        rear_port=rear_ports[1],
        type=PortTypeChoices.TYPE_110_PUNCH,
        rear_port_position=2,
        label="frontport2",
        description="Front Port Description 2",
    )
    FrontPortTemplate.objects.create(
        device_type=device_types[2],
        name="Front Port 3",
        rear_port=rear_ports[2],
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
        SecretsGroup.objects.create(name="Secrets group 1", slug="secrets-group-1"),
        SecretsGroup.objects.create(name="Secrets group 2", slug="secrets-group-2"),
        SecretsGroup.objects.create(name="Secrets group 3", slug="secrets-group-3"),
    )

    device_statuses = Status.objects.get_for_model(Device)
    device_status_map = {ds.slug: ds for ds in device_statuses.all()}

    Device.objects.create(
        name="Device 1",
        device_type=device_types[0],
        device_role=device_roles[0],
        platform=platforms[0],
        rack=racks[0],
        site=sites[0],
        tenant=tenants[0],
        status=device_status_map["active"],
        cluster=clusters[0],
        asset_tag="1001",
        face=DeviceFaceChoices.FACE_FRONT,
        serial="ABC",
        position=1,
        secrets_group=secrets_groups[0],
    )
    Device.objects.create(
        name="Device 2",
        device_type=device_types[1],
        device_role=device_roles[1],
        platform=platforms[1],
        rack=racks[1],
        site=sites[1],
        tenant=tenants[1],
        status=device_status_map["staged"],
        cluster=clusters[1],
        asset_tag="1002",
        face=DeviceFaceChoices.FACE_FRONT,
        serial="DEF",
        position=2,
        secrets_group=secrets_groups[1],
        local_context_data={"foo": 123},
    )
    Device.objects.create(
        name="Device 3",
        device_type=device_types[2],
        device_role=device_roles[2],
        platform=platforms[2],
        rack=racks[2],
        site=sites[2],
        tenant=tenants[2],
        status=device_status_map["failed"],
        cluster=clusters[2],
        asset_tag="1003",
        face=DeviceFaceChoices.FACE_REAR,
        serial="GHI",
        position=3,
        secrets_group=secrets_groups[2],
    )


class RegionTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Region.objects.all()
    filterset = RegionFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        cls.parent_regions = list(Region.objects.filter(children__isnull=False)[:3])
        cls.child_regions = list(Region.objects.filter(parent__in=cls.parent_regions)[:3])

    def test_description(self):
        regions = Region.objects.exclude(description="")[:2]
        params = {"description": [regions[0].description, regions[1].description]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(description__in=[regions[0].description, regions[1].description]).count(),
        )

    def test_parent(self):
        with self.subTest():
            params = {"parent_id": [self.parent_regions[0].pk, self.parent_regions[1].pk]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(parent__in=[self.parent_regions[0].pk, self.parent_regions[1].pk]).count(),
            )
        with self.subTest():
            params = {"parent": [self.parent_regions[0].slug, self.parent_regions[1].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(parent__in=[self.parent_regions[0], self.parent_regions[1]]).count(),
            )

    def test_children(self):
        with self.subTest():
            params = {"children": [self.child_regions[0].pk, self.child_regions[1].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(children__in=[self.child_regions[0].pk, self.child_regions[1].pk]).count(),
            )
        with self.subTest():
            params = {"children": [self.child_regions[0].pk, self.child_regions[2].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(children__in=[self.child_regions[0].pk, self.child_regions[2].pk]).count(),
            )

    def test_has_children(self):
        with self.subTest():
            params = {"has_children": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(children__isnull=False),
            )
        with self.subTest():
            params = {"has_children": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(children__isnull=True),
            )

    def test_sites(self):
        regions = Region.objects.filter(sites__isnull=False).distinct()[:2]
        sites = [regions[0].sites.first(), regions[1].sites.first()]
        params = {"sites": [sites[0].pk, sites[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(sites__in=[sites[0].pk, sites[1].pk]).distinct(),
        )

    def test_has_sites(self):
        with self.subTest():
            params = {"has_sites": True}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(sites__isnull=False).distinct().count(),
            )
        with self.subTest():
            params = {"has_sites": False}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(sites__isnull=True).count(),
            )


class SiteTestCase(FilterTestCases.NameSlugFilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Site.objects.all()
    filterset = SiteFilterSet
    tenancy_related_name = "sites"

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        cls.regions = Region.objects.filter(sites__isnull=True, parent__isnull=True, children__isnull=True)[:2]
        Site.objects.create(name="Site 4", status=cls.site_status_map["retired"])
        Site.objects.create(name="Site 5", region=cls.regions[0], status=cls.site_status_map["active"])
        Site.objects.create(name="Site 6", region=cls.regions[1], status=cls.site_status_map["active"])

    def test_facility(self):
        params = {"facility": ["Facility 1", "Facility 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_asn(self):
        params = {"asn": [65001, 65002]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(), self.queryset.filter(asn__in=[65001, 65002]).count()
        )

    def test_latitude(self):
        params = {"latitude": [10, 20]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_longitude(self):
        params = {"longitude": [10, 20]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_contact_name(self):
        params = {"contact_name": ["Contact 1", "Contact 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_contact_phone(self):
        params = {"contact_phone": ["123-555-0001", "123-555-0002"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_contact_email(self):
        params = {"contact_email": ["contact1@example.com", "contact2@example.com"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_status(self):
        statuses = list(Status.objects.get_for_model(Site)[:2])
        params = {"status": [statuses[0].slug, statuses[1].slug]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(status__slug__in=params["status"]).count(),
        )

    def test_region(self):
        with self.subTest():
            params = {"region_id": [self.regions[0].pk, self.regions[1].pk]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(region__in=[self.regions[0].pk, self.regions[1].pk]).distinct().count(),
            )
        with self.subTest():
            params = {"region": [self.regions[0].slug, self.regions[1].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(region__slug__in=[self.regions[0].slug, self.regions[1].slug]).distinct().count(),
            )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_comments(self):
        with self.subTest():
            params = {"comments": "COMMENT"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)
        with self.subTest():
            params = {"comments": "comment123"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)
        with self.subTest():
            params = {"comments": "comment2"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_circuit_terminations(self):
        circuit_terminations = CircuitTermination.objects.all()[:2]
        params = {"circuit_terminations": [circuit_terminations[0].pk, circuit_terminations[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_circuit_terminations(self):
        with self.subTest():
            params = {"has_circuit_terminations": True}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                Site.objects.filter(circuit_terminations__isnull=False).distinct().count(),
            )
        with self.subTest():
            params = {"has_circuit_terminations": False}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(circuit_terminations__isnull=True).count(),
            )

    def test_devices(self):
        devices = Device.objects.all()[:2]
        params = {"devices": [devices[0].pk, devices[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_devices(self):
        with self.subTest():
            params = {"has_devices": True}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(devices__isnull=False).distinct().count(),
            )
        with self.subTest():
            params = {"has_devices": False}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(), self.queryset.filter(devices__isnull=True).count()
            )

    def test_power_panels(self):
        power_panels = PowerPanel.objects.all()[:2]
        params = {"power_panels": [power_panels[0].pk, power_panels[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_power_panels(self):
        with self.subTest():
            params = {"has_power_panels": True}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(powerpanel__isnull=False).distinct().count(),
            )
        with self.subTest():
            params = {"has_power_panels": False}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(powerpanel__isnull=True).count(),
            )

    def test_rack_groups(self):
        rack_groups = RackGroup.objects.all()[:2]
        params = {"rack_groups": [rack_groups[0].pk, rack_groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_rack_groups(self):
        with self.subTest():
            params = {"has_rack_groups": True}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(rack_groups__isnull=False).distinct().count(),
            )
        with self.subTest():
            params = {"has_rack_groups": False}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(rack_groups__isnull=True).distinct().count(),
            )

    def test_racks(self):
        racks = Rack.objects.all()[:2]
        params = {"racks": [racks[0].pk, racks[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_racks(self):
        with self.subTest():
            params = {"has_racks": True}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(racks__isnull=False).distinct().count(),
            )
        with self.subTest():
            params = {"has_racks": False}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(), self.queryset.filter(racks__isnull=True).count()
            )

    def test_prefixes(self):
        prefixes = list(Prefix.objects.filter(site__isnull=False)[:2])
        params = {"prefixes": [prefixes[0].pk, prefixes[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, Site.objects.filter(prefixes__in=prefixes).distinct()
        )

    def test_has_prefixes(self):
        with self.subTest():
            params = {"has_prefixes": True}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(prefixes__isnull=False).distinct().count(),
            )
        with self.subTest():
            params = {"has_prefixes": False}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(prefixes__isnull=True).distinct().count(),
            )

    def test_vlan_groups(self):
        vlan_groups = list(VLANGroup.objects.filter(site__isnull=False))[:2]
        params = {"vlan_groups": [vlan_groups[0].pk, vlan_groups[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vlan_groups__in=vlan_groups).distinct()
        )

    def test_has_vlan_groups(self):
        with self.subTest():
            params = {"has_vlan_groups": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(vlan_groups__isnull=False).distinct()
            )
        with self.subTest():
            params = {"has_vlan_groups": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(vlan_groups__isnull=True).distinct()
            )

    def test_vlans(self):
        vlans = list(VLAN.objects.filter(site__isnull=False))[:2]
        params = {"vlans": [vlans[0].pk, vlans[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vlans__in=vlans).distinct()
        )

    def test_has_vlans(self):
        with self.subTest():
            params = {"has_vlans": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(vlans__isnull=False).distinct()
            )
        with self.subTest():
            params = {"has_vlans": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(vlans__isnull=True).distinct()
            )

    def test_clusters(self):
        clusters = Cluster.objects.all()[:2]
        params = {"clusters": [clusters[0].pk, clusters[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_clusters(self):
        with self.subTest():
            params = {"has_clusters": True}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(clusters__isnull=False).distinct().count(),
            )
        with self.subTest():
            params = {"has_clusters": False}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(), self.queryset.filter(clusters__isnull=True).count()
            )

    def test_time_zone(self):
        with self.subTest():
            params = {"time_zone": ["America/Los_Angeles", "America/Chicago"]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(time_zone__in=params["time_zone"]).count(),
            )
        with self.subTest():
            params = {"time_zone": [""]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(), self.queryset.filter(time_zone="").count()
            )

    def test_physical_address(self):
        with self.subTest():
            params = {"physical_address": "1 road st, albany, ny"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        with self.subTest():
            params = {"physical_address": "nomatch"}
            self.assertFalse(self.filterset(params, self.queryset).qs.exists())

    def test_shipping_address(self):
        with self.subTest():
            params = {"shipping_address": "PO Box 1, albany, ny"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        with self.subTest():
            params = {"shipping_address": "nomatch"}
            self.assertFalse(self.filterset(params, self.queryset).qs.exists())

    def test_description(self):
        with self.subTest():
            params = {"description": "Site 1 description"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        with self.subTest():
            params = {"description": "nomatch"}
            self.assertFalse(self.filterset(params, self.queryset).qs.exists())


class LocationTypeFilterSetTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = LocationType.objects.all()
    filterset = LocationTypeFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.lt1 = LocationType.objects.get(name="Building")
        cls.lt2 = LocationType.objects.get(name="Floor")

    def test_description(self):
        params = {"description": [self.lt1.description, self.lt2.description]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_parent(self):
        params = {"parent": ["building", LocationType.objects.get(name="Floor").pk]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(
                parent__in=[LocationType.objects.get(name="Building"), LocationType.objects.get(name="Floor")]
            ).count(),
        )

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


class LocationFilterSetTestCase(FilterTestCases.NameSlugFilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Location.objects.all()
    filterset = LocationFilterSet
    tenancy_related_name = "locations"

    @classmethod
    def setUpTestData(cls):
        lt1 = LocationType.objects.get(name="Campus")
        lt2 = LocationType.objects.get(name="Building")
        lt3 = LocationType.objects.get(name="Floor")
        lt4 = LocationType.objects.get(name="Room")
        lt4.content_types.add(ContentType.objects.get_for_model(Device))

        status_active = Status.objects.get(slug="active")
        cls.site = Site.objects.first()
        tenants = Tenant.objects.filter(group__isnull=False)[:2]

        loc1 = Location.objects.create(
            name="RTP", location_type=lt1, status=status_active, site=cls.site, description="Research Triangle Park"
        )
        loc2 = Location.objects.create(name="RTP4E", location_type=lt2, status=status_active, parent=loc1)
        loc3 = Location.objects.create(
            name="RTP4E-3", location_type=lt3, status=status_active, parent=loc2, tenant=tenants[0]
        )
        loc4 = Location.objects.create(
            name="RTP4E-3-0101",
            location_type=lt4,
            status=status_active,
            parent=loc3,
            tenant=tenants[1],
            description="Cube",
        )
        nested_loc = Location.objects.create(name="RTP South", location_type=lt1, status=status_active, parent=loc1)
        for loc in [loc1, loc2, loc3, loc4, nested_loc]:
            loc.validated_save()

    def test_location_type(self):
        params = {
            "location_type": [
                LocationType.objects.get(name="Building").slug,
                LocationType.objects.get(name="Floor").pk,
            ]
        }
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(
                location_type__in=[
                    LocationType.objects.get(name="Building"),
                    LocationType.objects.get(name="Floor"),
                ]
            )
            .distinct()
            .count(),
        )

    def test_parent(self):
        params = {"parent": ["rtp", Location.objects.get(name="RTP4E").pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_base_site(self):
        params = {"base_site": [self.site.slug, self.site.pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            list(flatten_iterable([x.descendants(include_self=True) for x in Location.objects.filter(site=self.site)])),
        )

    def test_subtree(self):
        params = {"subtree": [Location.objects.get(name="RTP").slug, Location.objects.get(name="RTP South").pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, Location.objects.get(name="RTP").descendants(include_self=True)
        )

    def test_child_location_type(self):
        params = {"child_location_type": ["room", LocationType.objects.get(name="Floor").pk]}
        query_params = Q(
            location_type__children__in=[LocationType.objects.get(name="Room"), LocationType.objects.get(name="Floor")]
        ) | Q(
            location_type__in=[LocationType.objects.get(name="Room"), LocationType.objects.get(name="Floor")],
            location_type__nestable=True,
        )
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(), Location.objects.filter(query_params).count()
        )

    def test_content_type(self):
        params = {"content_type": ["dcim.device"]}
        ct = ContentType.objects.get_for_model(Device)
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            Location.objects.filter(location_type__content_types=ct).count(),
        )

    def test_description(self):
        params = {"description": ["Research Triangle Park", "Cube"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        params = {"site": [Site.objects.first().slug, Site.objects.first().pk]}
        # TODO: should this filter return descendant locations as well?
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(), Location.objects.filter(site=self.site).count()
        )


class RackGroupTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = RackGroup.objects.all()
    filterset = RackGroupFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        sites = Site.objects.all()[:3]
        parent_rack_groups = RackGroup.objects.filter(parent__isnull=True)

        RackGroup.objects.create(
            name="Child Rack Group 1",
            slug="rack-group-1c",
            site=sites[0],
            parent=parent_rack_groups[0],
            description="A",
        )
        RackGroup.objects.create(
            name="Child Rack Group 2",
            slug="rack-group-2c",
            site=sites[1],
            parent=parent_rack_groups[1],
            description="B",
        )
        RackGroup.objects.create(
            name="Child Rack Group 3",
            slug="rack-group-3c",
            site=sites[2],
            parent=parent_rack_groups[2],
            description="C",
        )
        RackGroup.objects.create(
            name="Rack Group 4",
            slug="rack-group-4",
            site=sites[2],
        )

    def test_description(self):
        params = {"description": ["A", "B"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = Region.objects.filter(slug__in=["region-1", "region-2"])
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(site__region__in=params["region_id"]).count(),
            )
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(site__region__slug__in=params["region"]).count(),
            )

    def test_site(self):
        sites = Site.objects.filter(slug__in=["site-1", "site-2"])
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(site__in=params["site_id"]).count(),
            )
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(site__slug__in=params["site"]).count(),
            )

    def test_parent(self):
        parent_rack_groups = RackGroup.objects.filter(children__isnull=False)[:2]
        with self.subTest():
            params = {"parent_id": [parent_rack_groups[0].pk, parent_rack_groups[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"parent": [parent_rack_groups[0].slug, parent_rack_groups[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_children(self):
        child_groups = RackGroup.objects.filter(name__startswith="Child").filter(parent__isnull=False)[:2]
        with self.subTest():
            params = {"children": [child_groups[0].pk, child_groups[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            rack_group_4 = RackGroup.objects.filter(slug="rack-group-4").first()
            params = {"children": [rack_group_4.pk, rack_group_4.pk]}
            self.assertFalse(self.filterset(params, self.queryset).qs.exists())

    def test_has_children(self):
        with self.subTest():
            self.assertEqual(self.filterset({"has_children": True}, self.queryset).qs.count(), 3)
        with self.subTest():
            self.assertEqual(self.filterset({"has_children": False}, self.queryset).qs.count(), 4)

    def test_power_panels(self):
        power_panels = PowerPanel.objects.all()[:2]
        params = {"power_panels": [power_panels[0].pk, power_panels[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_power_panels(self):
        with self.subTest():
            self.assertEqual(self.filterset({"has_power_panels": True}, self.queryset).qs.count(), 3)
        with self.subTest():
            self.assertEqual(self.filterset({"has_power_panels": False}, self.queryset).qs.count(), 4)

    def test_racks(self):
        racks = Rack.objects.all()[:2]
        params = {"racks": [racks[0].pk, racks[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_racks(self):
        with self.subTest():
            self.assertEqual(self.filterset({"has_racks": True}, self.queryset).qs.count(), 3)
        with self.subTest():
            self.assertEqual(self.filterset({"has_racks": False}, self.queryset).qs.count(), 4)


class RackRoleTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = RackRole.objects.all()
    filterset = RackRoleFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        RackRole.objects.create(name="Rack Role 4", slug="rack-role-4", color="abcdef")

    def test_color(self):
        params = {"color": ["ff0000", "00ff00"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_racks(self):
        racks = Rack.objects.all()[:2]
        params = {"racks": [racks[0].pk, racks[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_racks(self):
        with self.subTest():
            self.assertEqual(self.filterset({"has_racks": True}, self.queryset).qs.count(), 3)
        with self.subTest():
            self.assertEqual(self.filterset({"has_racks": False}, self.queryset).qs.count(), 1)


class RackTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Rack.objects.all()
    filterset = RackFilterSet
    tenancy_related_name = "racks"

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        site = Site.objects.get(slug="site-3")
        rack_group = RackGroup.objects.get(slug="rack-group-3")
        tenant = Tenant.objects.filter(group__isnull=False).first()
        rack_role = RackRole.objects.get(slug="rack-role-3")

        Rack.objects.create(
            name="Rack 4",
            facility_id="rack-4",
            site=site,
            group=rack_group,
            tenant=tenant,
            status=cls.rack_status_map["active"],
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

    def test_name(self):
        params = {"name": ["Rack 1", "Rack 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_facility_id(self):
        params = {"facility_id": ["rack-1", "rack-2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_asset_tag(self):
        params = {"asset_tag": ["1001", "1002"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type(self):
        params = {"type": [RackTypeChoices.TYPE_2POST, RackTypeChoices.TYPE_4POST]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_width(self):
        params = {"width": [RackWidthChoices.WIDTH_19IN, RackWidthChoices.WIDTH_21IN]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_u_height(self):
        params = {"u_height": [42, 43]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_desc_units(self):
        with self.subTest():
            params = {"desc_units": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        with self.subTest():
            params = {"desc_units": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_outer_width(self):
        params = {"outer_width": [100, 200]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_outer_depth(self):
        params = {"outer_depth": [100, 200]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_outer_unit(self):
        with self.subTest():
            self.assertEqual(Rack.objects.exclude(outer_unit="").count(), 3)
        with self.subTest():
            params = {"outer_unit": RackDimensionUnitChoices.UNIT_MILLIMETER}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = (Region.objects.get(slug="region-1"), Region.objects.get(slug="region-2"))
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (Site.objects.get(slug="site-1"), Site.objects.get(slug="site-2"))
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_group(self):
        groups = RackGroup.objects.all()[:2]
        with self.subTest():
            params = {"group_id": [groups[0].pk, groups[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"group": [groups[0].slug, groups[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_status(self):
        statuses = list(Status.objects.get_for_model(Rack)[:2])
        params = {"status": [statuses[0].slug, statuses[1].slug]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(status__slug__in=params["status"]).count(),
        )

    def test_role(self):
        roles = RackRole.objects.all()[:2]
        with self.subTest():
            params = {"role_id": [roles[0].pk, roles[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"role": [roles[0].slug, roles[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_serial(self):
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

    def test_comments(self):
        rack_1 = Rack.objects.filter(name="Rack 1").first()
        with self.subTest():
            self.assertEqual(self.filterset({"comments": "comment1"}).qs.count(), 1)
        with self.subTest():
            self.assertEqual(self.filterset({"comments": "comment1"}).qs.first().pk, rack_1.pk)

    def test_devices(self):
        devices = Device.objects.all()[:2]
        params = {"devices": [devices[0].pk, devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_devices(self):
        with self.subTest():
            params = {"has_devices": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_devices": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_power_feeds(self):
        power_feeds = PowerFeed.objects.all()[:2]
        params = {"power_feeds": [power_feeds[0].pk, power_feeds[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_power_feeds(self):
        with self.subTest():
            params = {"has_power_feeds": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_power_feeds": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_reservations(self):
        reservations = RackReservation.objects.all()[:2]
        params = {"reservations": [reservations[0], reservations[1]]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_reservations(self):
        with self.subTest():
            params = {"has_reservations": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_reservations": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class RackReservationTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = RackReservation.objects.all()
    filterset = RackReservationFilterSet
    tenancy_related_name = "rackreservations"

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

    def test_site(self):
        sites = Site.objects.filter(slug__in=["site-1", "site-2"])
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_group(self):
        groups = RackGroup.objects.all()[:2]
        with self.subTest():
            params = {"group_id": [groups[0].pk, groups[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"group": [groups[0].slug, groups[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_user(self):
        users = User.objects.filter(username__startswith="TestCaseUser")[:2]
        with self.subTest():
            params = {"user_id": [users[0].pk, users[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"user": [users[0].username, users[1].username]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_description(self):
        params = {"description": "Rack Reservation 1"}
        with self.subTest():
            self.assertSequenceEqual(self.filterset(params, self.queryset).qs.first().units, (1, 2, 3))
        with self.subTest():
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"description": "Rack Reservation 3"}
        with self.subTest():
            self.assertSequenceEqual(self.filterset(params, self.queryset).qs.first().units, (7, 8, 9))
        with self.subTest():
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_rack(self):
        racks = Rack.objects.filter(name__startswith="Rack ")[:2]
        params = {"rack": [racks[0].pk, racks[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class ManufacturerTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Manufacturer.objects.all()
    filterset = ManufacturerFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = list(Device.objects.all()[:3])

        InventoryItem.objects.create(device=devices[0], name="Inventory Item 1", manufacturer=cls.manufacturers[0])
        InventoryItem.objects.create(device=devices[1], name="Inventory Item 2", manufacturer=cls.manufacturers[1])
        InventoryItem.objects.create(device=devices[2], name="Inventory Item 3", manufacturer=cls.manufacturers[2])

    def test_description(self):
        manufacturers = self.queryset.exclude(description="")[:2]
        params = {"description": [manufacturers[0].description, manufacturers[1].description]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(description__in=params["description"])
        )

    def test_inventory_items(self):
        inventory_items = list(InventoryItem.objects.all()[:2])
        params = {"inventory_items": [inventory_items[0].pk, inventory_items[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(inventory_items))

    def test_has_inventory_items(self):
        with self.subTest():
            params = {"has_inventory_items": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(inventory_items__isnull=True),
            )
        with self.subTest():
            params = {"has_inventory_items": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(inventory_items__isnull=False),
            )

    def test_device_types(self):
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        device_types = list(DeviceType.objects.filter(model__startswith="Model")[:2])
        params = {"device_types": [device_types[0].pk, device_types[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(device_types))

    def test_has_device_types(self):
        with self.subTest():
            params = {"has_device_types": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(device_types__isnull=True),
            )
        with self.subTest():
            params = {"has_device_types": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(device_types__isnull=False),
            )

    def test_platforms(self):
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        platforms = list(Platform.objects.filter(name__startswith="Platform")[:2])
        params = {"platforms": [platforms[0].pk, platforms[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(platforms))

    def test_has_platforms(self):
        with self.subTest():
            params = {"has_platforms": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(platforms__isnull=True),
            )
        with self.subTest():
            params = {"has_platforms": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(platforms__isnull=False),
            )


class DeviceTypeTestCase(FilterTestCases.FilterTestCase):
    queryset = DeviceType.objects.all()
    filterset = DeviceTypeFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        manufacturer = Manufacturer.objects.first()
        DeviceType.objects.create(
            manufacturer=manufacturer,
            comments="Device type 4",
            model="Model 4",
            slug="model-4",
            part_number="Part Number 4",
            u_height=4,
            is_full_depth=True,
        )

    def test_model(self):
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        models = ["Model 1", "Model 2"]
        params = {"model": models}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(models))

    def test_slug(self):
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        slugs = ["model-1", "model-2"]
        params = {"slug": slugs}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(slugs))

    def test_part_number(self):
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        part_numbers = ["Part Number 1", "Part Number 2"]
        params = {"part_number": part_numbers}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(part_numbers))

    def test_u_height(self):
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        heights = [1, 2]
        params = {"u_height": heights}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(), self.queryset.filter(u_height__in=heights).count()
        )

    def test_is_full_depth(self):
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
        with self.subTest():
            params = {"subdevice_role": SubdeviceRoleChoices.ROLE_PARENT}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(subdevice_role=SubdeviceRoleChoices.ROLE_PARENT),
            )
        with self.subTest():
            params = {"subdevice_role": SubdeviceRoleChoices.ROLE_CHILD}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(subdevice_role=SubdeviceRoleChoices.ROLE_CHILD),
            )

    def test_manufacturer(self):
        manufacturers = [Manufacturer.objects.first(), Manufacturer.objects.last()]
        with self.subTest():
            pk_list = [manufacturers[0].pk, manufacturers[1].pk]
            params = {"manufacturer_id": pk_list}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(manufacturer_id__in=pk_list),
            )
        with self.subTest():
            slugs = [manufacturers[0].slug, manufacturers[1].slug]
            params = {"manufacturer": slugs}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(manufacturer__slug__in=slugs),
            )

    def test_console_ports(self):
        with self.subTest():
            params = {"console_ports": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(consoleporttemplates__isnull=True),
            )
        with self.subTest():
            params = {"console_ports": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(consoleporttemplates__isnull=False),
            )

    def test_console_server_ports(self):
        with self.subTest():
            params = {"console_server_ports": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(consoleserverporttemplates__isnull=True),
            )
        with self.subTest():
            params = {"console_server_ports": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(consoleserverporttemplates__isnull=False),
            )

    def test_power_ports(self):
        with self.subTest():
            params = {"power_ports": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(powerporttemplates__isnull=True),
            )
        with self.subTest():
            params = {"power_ports": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(powerporttemplates__isnull=False),
            )

    def test_power_outlets(self):
        with self.subTest():
            params = {"power_outlets": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(poweroutlettemplates__isnull=True),
            )
        with self.subTest():
            params = {"power_outlets": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(poweroutlettemplates__isnull=False),
            )

    def test_interfaces(self):
        with self.subTest():
            params = {"interfaces": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(interfacetemplates__isnull=True),
            )
        with self.subTest():
            params = {"interfaces": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(interfacetemplates__isnull=False),
            )

    def test_pass_through_ports(self):
        query = Q(frontporttemplates__isnull=False, rearporttemplates__isnull=False)
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
        with self.subTest():
            params = {"device_bays": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(devicebaytemplates__isnull=True),
            )
        with self.subTest():
            params = {"device_bays": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(devicebaytemplates__isnull=False),
            )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_comments(self):
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        comments = ["Device type 1", "Device type 2"]
        params = {"comments": comments}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(comments))

    def test_instances(self):
        instances = list(Device.objects.all()[:2])
        params = {"instances": [instances[0].pk, instances[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(instances))

    def test_has_instances(self):
        with self.subTest():
            params = {"has_instances": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(instances__isnull=True),
            )
        with self.subTest():
            params = {"has_instances": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(instances__isnull=False),
            )

    def test_console_port_templates(self):
        console_port_templates = list(ConsolePortTemplate.objects.all()[:2])
        params = {"console_port_templates": [console_port_templates[0].pk, console_port_templates[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(console_port_templates))

    def test_has_console_port_templates(self):
        with self.subTest():
            params = {"has_console_port_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(consoleporttemplates__isnull=True),
            )
        with self.subTest():
            params = {"has_console_port_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(consoleporttemplates__isnull=False),
            )

    def test_console_server_port_templates(self):
        csp_templates = list(ConsoleServerPortTemplate.objects.all()[:2])
        params = {"console_server_port_templates": [csp_templates[0].pk, csp_templates[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(csp_templates))

    def test_has_console_server_port_templates(self):
        with self.subTest():
            params = {"has_console_server_port_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(consoleserverporttemplates__isnull=True),
            )
        with self.subTest():
            params = {"has_console_server_port_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(consoleserverporttemplates__isnull=False),
            )

    def test_power_port_templates(self):
        power_port_templates = list(PowerPortTemplate.objects.all()[:2])
        params = {"power_port_templates": [power_port_templates[0].pk, power_port_templates[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(power_port_templates))

    def test_has_power_port_templates(self):
        with self.subTest():
            params = {"has_power_port_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(powerporttemplates__isnull=True),
            )
        with self.subTest():
            params = {"has_power_port_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(powerporttemplates__isnull=False),
            )

    def test_power_outlet_templates(self):
        power_outlet_templates = list(PowerOutletTemplate.objects.all()[:2])
        params = {"power_outlet_templates": [power_outlet_templates[0].pk, power_outlet_templates[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(power_outlet_templates))

    def test_has_power_outlet_templates(self):
        with self.subTest():
            params = {"has_power_outlet_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(poweroutlettemplates__isnull=True),
            )
        with self.subTest():
            params = {"has_power_outlet_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(poweroutlettemplates__isnull=False),
            )

    def test_interface_templates(self):
        interface_templates = list(InterfaceTemplate.objects.all()[:2])
        params = {"interface_templates": [interface_templates[0].pk, interface_templates[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(interface_templates))

    def test_has_interface_templates(self):
        with self.subTest():
            params = {"has_interface_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(interfacetemplates__isnull=True),
            )
        with self.subTest():
            params = {"has_interface_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(interfacetemplates__isnull=False),
            )

    def test_front_port_templates(self):
        front_port_templates = list(FrontPortTemplate.objects.all()[:2])
        params = {"front_port_templates": [front_port_templates[0].pk, front_port_templates[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(front_port_templates))

    def test_has_front_port_templates(self):
        with self.subTest():
            params = {"has_front_port_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(frontporttemplates__isnull=True),
            )
        with self.subTest():
            params = {"has_front_port_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(frontporttemplates__isnull=False),
            )

    def test_rear_port_templates(self):
        rear_port_templates = list(RearPortTemplate.objects.all()[:2])
        params = {"rear_port_templates": [rear_port_templates[0].pk, rear_port_templates[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(rear_port_templates))

    def test_has_rear_port_templates(self):
        with self.subTest():
            params = {"has_rear_port_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(rearporttemplates__isnull=True),
            )
        with self.subTest():
            params = {"has_rear_port_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(rearporttemplates__isnull=False),
            )

    def test_device_bay_templates(self):
        device_bay_templates = list(DeviceBayTemplate.objects.all()[:2])
        params = {"device_bay_templates": [device_bay_templates[0].pk, device_bay_templates[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(device_bay_templates))

    def test_has_device_bay_templates(self):
        with self.subTest():
            params = {"has_device_bay_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(devicebaytemplates__isnull=True),
            )
        with self.subTest():
            params = {"has_device_bay_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(devicebaytemplates__isnull=False),
            )


class Mixins:
    class ComponentTemplateMixin(FilterTestCases.FilterTestCase):
        test_names = None
        test_labels = None
        test_descriptions = None

        @classmethod
        def setUpTestData(cls):
            common_test_data(cls)

            cls.device_types = list(DeviceType.objects.filter(model__in=["Model 1", "Model 2"]))

        def test_name(self):
            params = {"name": self.test_names}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(self.test_names))

        def test_devicetype_id(self):
            pk_list = [self.device_types[0].pk, self.device_types[1].pk]
            params = {"devicetype_id": pk_list}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(device_type_id__in=pk_list),
            )

        def test_device_type(self):
            slugs = [self.device_types[0].slug, self.device_types[1].slug]
            params = {"device_type": slugs}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(device_type__slug__in=slugs),
            )

        def test_label(self):
            params = {"label": self.test_labels}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(self.test_labels))

        def test_description(self):
            params = {"description": self.test_descriptions}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(self.test_descriptions))


class ConsolePortTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = ConsolePortTemplate.objects.all()
    filterset = ConsolePortTemplateFilterSet
    test_descriptions = ["Front Console Port 1", "Front Console Port 2"]
    test_labels = ["console1", "console2"]
    test_names = ["Console Port 1", "Console Port 2"]


class ConsoleServerPortTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = ConsoleServerPortTemplate.objects.all()
    filterset = ConsoleServerPortTemplateFilterSet
    test_descriptions = ["Front Console Server Port 1", "Front Console Server Port 2"]
    test_labels = ["consoleserverport1", "consoleserverport2"]
    test_names = ["Console Server Port 1", "Console Server Port 2"]


class PowerPortTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = PowerPortTemplate.objects.all()
    filterset = PowerPortTemplateFilterSet
    test_descriptions = ["Power Port Description 1", "Power Port Description 2"]
    test_labels = ["powerport1", "powerport2"]
    test_names = ["Power Port 1", "Power Port 2"]

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

    def test_maximum_draw(self):
        draws = [100, 200]
        params = {"maximum_draw": draws}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(draws))

    def test_allocated_draw(self):
        draws = [50, 100]
        params = {"allocated_draw": draws}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(draws))

    def test_power_outlet_templates(self):
        power_outlet_templates = list(PowerOutletTemplate.objects.all()[:2])
        params = {"power_outlet_templates": [power_outlet_templates[0].pk, power_outlet_templates[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(power_outlet_templates))

    def test_has_power_outlet_templates(self):
        with self.subTest():
            params = {"has_power_outlet_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(poweroutlet_templates__isnull=True),
            )
        with self.subTest():
            params = {"has_power_outlet_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(poweroutlet_templates__isnull=False),
            )


class PowerOutletTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = PowerOutletTemplate.objects.all()
    filterset = PowerOutletTemplateFilterSet
    test_descriptions = ["Power Outlet Description 1", "Power Outlet Description 2"]
    test_labels = ["poweroutlet1", "poweroutlet2"]
    test_names = ["Power Outlet 1", "Power Outlet 2"]

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
        # TODO: Support filtering for multiple values
        params = {"feed_leg": PowerOutletFeedLegChoices.FEED_LEG_A}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(**params),
        )

    def test_power_port_template(self):
        power_port_templates = list(PowerPortTemplate.objects.all()[:2])
        params = {"power_port_template": [power_port_templates[0].pk, power_port_templates[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(power_port_templates))


class InterfaceTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = InterfaceTemplate.objects.all()
    filterset = InterfaceTemplateFilterSet
    test_descriptions = ["Interface Description 1", "Interface Description 2"]
    test_labels = ["interface1", "interface2"]
    test_names = ["Interface 1", "Interface 2"]

    def test_type(self):
        # TODO: Support filtering for multiple values
        params = {"type": InterfaceTypeChoices.TYPE_1GE_FIXED}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(**params),
        )

    def test_mgmt_only(self):
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
    test_descriptions = ["Front Port Description 1", "Front Port Description 2"]
    test_labels = ["frontport1", "frontport2"]
    test_names = ["Front Port 1", "Front Port 2"]

    def test_type(self):
        # TODO: Support filtering for multiple values
        params = {"type": PortTypeChoices.TYPE_8P8C}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(**params),
        )

    def test_rear_port_position(self):
        positions = [1, 2]
        params = {"rear_port_position": positions}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(rear_port_position__in=positions),
        )

    def test_rear_port_template(self):
        rear_port_templates = list(RearPortTemplate.objects.all()[:2])
        params = {"rear_port_template": [rear_port_templates[0].pk, rear_port_templates[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(rear_port_templates))


class RearPortTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = RearPortTemplate.objects.all()
    filterset = RearPortTemplateFilterSet
    test_descriptions = ["Rear Port Description 1", "Rear Port Description 2"]
    test_labels = ["rearport1", "rearport2"]
    test_names = ["Rear Port 1", "Rear Port 2"]

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
        # TODO: Support filtering for multiple values
        params = {"type": PortTypeChoices.TYPE_8P8C}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(**params),
        )

    def test_positions(self):
        positions = [1, 2]
        params = {"positions": positions}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(positions__in=positions),
        )

    def test_front_port_templates(self):
        front_port_templates = list(FrontPortTemplate.objects.all()[:2])
        params = {"front_port_templates": [front_port_templates[0].pk, front_port_templates[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(front_port_templates))

    def test_has_front_port_templates(self):
        with self.subTest():
            params = {"has_front_port_templates": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(frontport_templates__isnull=True),
            )
        with self.subTest():
            params = {"has_front_port_templates": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(frontport_templates__isnull=False),
            )


class DeviceBayTemplateTestCase(Mixins.ComponentTemplateMixin):
    queryset = DeviceBayTemplate.objects.all()
    filterset = DeviceBayTemplateFilterSet
    test_descriptions = ["Device Bay Description 1", "Device Bay Description 2"]
    test_labels = ["devicebay1", "devicebay2"]
    test_names = ["Device Bay 1", "Device Bay 2"]


class DeviceRoleTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = DeviceRole.objects.all()
    filterset = DeviceRoleFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

    def test_color(self):
        colors = ["ff0000", "00ff00"]
        params = {"color": colors}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(color__in=colors),
        )

    def test_vm_role(self):
        with self.subTest():
            params = {"vm_role": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(vm_role=True),
            )
        with self.subTest():
            params = {"vm_role": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(vm_role=False),
            )

    def test_description(self):
        descriptions = ["Device Role Description 1", "Device Role Description 2"]
        params = {"description": descriptions}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(descriptions))

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


class PlatformTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Platform.objects.all()
    filterset = PlatformFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

    def test_description(self):
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        descriptions = ["A", "B"]
        params = {"description": descriptions}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(descriptions))

    def test_napalm_driver(self):
        drivers = ["driver-1", "driver-2"]
        params = {"napalm_driver": drivers}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(drivers))

    def test_manufacturer(self):
        manufacturers = [Manufacturer.objects.first(), Manufacturer.objects.last()]
        with self.subTest():
            pk_list = [manufacturers[0].pk, manufacturers[1].pk]
            params = {"manufacturer_id": pk_list}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(manufacturer_id__in=pk_list),
            )
        with self.subTest():
            slugs = [manufacturers[0].slug, manufacturers[1].slug]
            params = {"manufacturer": slugs}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(manufacturer__slug__in=slugs),
            )

    def test_napalm_args(self):
        # FIXME(jathan): Hard-coding around expected values should be ripped out
        # once all fixture factory work has completed.
        napalm_args = ['["--test", "--arg1"]', '["--test", "--arg2"]']
        params = {"napalm_args": napalm_args}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(napalm_args))

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

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = Device.objects.exclude(name="Device 3")

        # Components for filtering
        ConsolePort.objects.first().delete()
        ConsoleServerPort.objects.first().delete()
        DeviceBay.objects.get(name="Device Bay 3").delete()
        Interface.objects.get(name="Interface 3").delete()
        PowerPort.objects.first().delete()
        PowerOutlet.objects.first().delete()
        RearPort.objects.first().delete()
        InventoryItem.objects.create(device=devices[0], name="Inventory Item 1")
        InventoryItem.objects.create(device=devices[1], name="Inventory Item 2")
        Service.objects.create(device=devices[0], name="ssh", protocol="tcp", ports=[22])
        Service.objects.create(device=devices[1], name="dns", protocol="udp", ports=[53])

        cls.device_redundancy_group = DeviceRedundancyGroup.objects.first()
        Device.objects.filter(pk=devices[0].pk).update(device_redundancy_group=cls.device_redundancy_group)
        Device.objects.filter(pk=devices[1].pk).update(
            device_redundancy_group=cls.device_redundancy_group, device_redundancy_group_priority=1
        )

        # Assign primary IPs for filtering
        interfaces = Interface.objects.all()
        ipaddresses = (
            IPAddress.objects.create(address="192.0.2.1/24", assigned_object=interfaces[0]),
            IPAddress.objects.create(address="192.0.2.2/24", assigned_object=interfaces[1]),
            IPAddress.objects.create(address="2600::1/120", assigned_object=interfaces[0]),
            IPAddress.objects.create(address="2600::0100/120", assigned_object=interfaces[1]),
        )

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
        virtual_chassis = VirtualChassis.objects.create(name="vc1", master=devices[0])
        Device.objects.filter(pk=devices[0].pk).update(virtual_chassis=virtual_chassis, vc_position=1, vc_priority=1)
        Device.objects.filter(pk=devices[1].pk).update(virtual_chassis=virtual_chassis, vc_position=2, vc_priority=2)

    def test_name(self):
        params = {"name": ["Device 1", "Device 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_asset_tag(self):
        params = {"asset_tag": ["1001", "1002"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_face(self):
        params = {"face": DeviceFaceChoices.FACE_FRONT}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_position(self):
        params = {"position": [1, 2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_vc_position(self):
        params = {"vc_position": [1, 2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_vc_priority(self):
        params = {"vc_priority": [1, 2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_manufacturer(self):
        manufacturers = Manufacturer.objects.all()[:2]
        with self.subTest():
            params = {"manufacturer_id": [manufacturers[0].pk, manufacturers[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"manufacturer": [manufacturers[0].slug, manufacturers[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_devicetype(self):
        device_types = self.device_types[:2]
        params = {"device_type_id": [device_types[0].pk, device_types[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(device_types))

    def test_devicerole(self):
        device_roles = self.device_roles[:2]
        with self.subTest():
            params = {"role_id": [device_roles[0].pk, device_roles[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(device_roles))
        with self.subTest():
            params = {"role": [device_roles[0].slug, device_roles[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(device_roles))

    def test_platform(self):
        platforms = self.platforms[:2]
        with self.subTest():
            params = {"platform_id": [platforms[0].pk, platforms[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(platforms))
        with self.subTest():
            params = {"platform": [platforms[0].slug, platforms[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(platforms))

    def test_region(self):
        regions = (
            Region.objects.get(slug="region-1"),
            Region.objects.get(slug="region-2"),
        )
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(regions))
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(regions))

    def test_secrets_group(self):
        secrets_groups = list(SecretsGroup.objects.all()[:2])
        with self.subTest():
            params = {"secrets_group_id": [secrets_groups[0].pk, secrets_groups[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"secrets_group": [secrets_groups[0].slug, secrets_groups[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (
            Site.objects.get(slug="site-1"),
            Site.objects.get(slug="site-2"),
        )
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_rackgroup(self):
        rack_groups = RackGroup.objects.all()[:2]
        params = {"rack_group_id": [rack_groups[0].pk, rack_groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_rack(self):
        racks = Rack.objects.all()[:2]
        params = {"rack_id": [racks[0].pk, racks[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cluster(self):
        clusters = Cluster.objects.all()[:2]
        params = {"cluster_id": [clusters[0].pk, clusters[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_model(self):
        params = {"model": ["model-1", "model-2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_status(self):
        statuses = list(Status.objects.get_for_model(Device)[:2])
        params = {"status": [statuses[0].slug, statuses[1].slug]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(status__slug__in=params["status"]).count(),
        )

    def test_is_full_depth(self):
        with self.subTest():
            params = {"is_full_depth": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"is_full_depth": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_mac_address(self):
        params = {"mac_address": ["00-00-00-00-00-01", "00-00-00-00-00-02"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_serial(self):
        with self.subTest():
            params = {"serial": "ABC"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        with self.subTest():
            params = {"serial": "abc"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_primary_ip(self):
        with self.subTest():
            params = {"has_primary_ip": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"has_primary_ip": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_virtual_chassis_id(self):
        params = {"virtual_chassis_id": [VirtualChassis.objects.first().pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_virtual_chassis_member(self):
        with self.subTest():
            params = {"virtual_chassis_member": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"virtual_chassis_member": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_is_virtual_chassis_member(self):
        with self.subTest():
            params = {"is_virtual_chassis_member": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"is_virtual_chassis_member": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_console_ports(self):
        with self.subTest():
            params = {"console_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"console_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_console_ports(self):
        with self.subTest():
            params = {"has_console_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"has_console_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_console_server_ports(self):
        with self.subTest():
            params = {"console_server_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"console_server_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_console_server_ports(self):
        with self.subTest():
            params = {"has_console_server_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"has_console_server_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_power_ports(self):
        with self.subTest():
            params = {"power_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"power_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_power_ports(self):
        with self.subTest():
            params = {"has_power_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"has_power_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_power_outlets(self):
        with self.subTest():
            params = {"power_outlets": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"power_outlets": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_power_outlets(self):
        with self.subTest():
            params = {"has_power_outlets": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"has_power_outlets": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_interfaces(self):
        with self.subTest():
            params = {"interfaces": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"interfaces": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_interfaces(self):
        with self.subTest():
            params = {"has_interfaces": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"has_interfaces": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_pass_through_ports(self):
        with self.subTest():
            params = {"pass_through_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"pass_through_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_front_ports(self):
        with self.subTest():
            params = {"has_front_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"has_front_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_rear_ports(self):
        with self.subTest():
            params = {"has_rear_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"has_rear_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device_bays(self):
        with self.subTest():
            params = {"device_bays": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device_bays": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_has_device_bays(self):
        with self.subTest():
            params = {"has_device_bays": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"has_device_bays": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_local_context_data(self):
        with self.subTest():
            params = {"local_context_data": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        with self.subTest():
            params = {"local_context_data": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_device_redundancy_group(self):
        with self.subTest():
            params = {"device_redundancy_group": [self.device_redundancy_group.pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device_redundancy_group": [self.device_redundancy_group.slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {
                "device_redundancy_group": [self.device_redundancy_group.pk],
                "device_redundancy_group_priority": [1],
            }
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class ConsolePortTestCase(FilterTestCases.FilterTestCase):
    queryset = ConsolePort.objects.all()
    filterset = ConsolePortFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        console_server_ports = (
            devices[1].consoleserverports.get(name="Console Server Port 2"),
            devices[2].consoleserverports.get(name="Console Server Port 3"),
        )

        console_ports = (
            devices[0].consoleports.get(name="Console Port 1"),
            devices[1].consoleports.get(name="Console Port 2"),
        )

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(slug="connected")

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

    def test_name(self):
        params = {"name": ["Console Port 1", "Console Port 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_description(self):
        params = {"description": ["Front Console Port 1", "Front Console Port 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_connected(self):
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_region(self):
        regions = (
            Region.objects.get(slug="region-1"),
            Region.objects.get(slug="region-2"),
        )
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (
            Site.objects.get(slug="site-1"),
            Site.objects.get(slug="site-2"),
        )
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        devices = [
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
        ]
        with self.subTest():
            params = {"device_id": [devices[0].pk, devices[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device": [devices[0].name, devices[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cabled(self):
        with self.subTest():
            params = {"cabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"cabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_label(self):
        labels = ["console1", "console2"]
        params = {"label": labels}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cable(self):
        cable = Cable.objects.all()[:2]
        params = {"cable": [cable[0].pk, cable[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class ConsoleServerPortTestCase(FilterTestCases.FilterTestCase):
    queryset = ConsoleServerPort.objects.all()
    filterset = ConsoleServerPortFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        console_ports = (
            devices[0].consoleports.get(name="Console Port 1"),
            devices[1].consoleports.get(name="Console Port 2"),
        )

        console_server_ports = (
            devices[1].consoleserverports.get(name="Console Server Port 2"),
            devices[2].consoleserverports.get(name="Console Server Port 3"),
        )

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(slug="connected")

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

    def test_name(self):
        params = {"name": ["Console Server Port 1", "Console Server Port 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_description(self):
        params = {"description": ["Front Console Server Port 1", "Front Console Server Port 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_connected(self):
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_region(self):
        regions = (
            Region.objects.get(slug="region-1"),
            Region.objects.get(slug="region-2"),
        )
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (
            Site.objects.get(slug="site-1"),
            Site.objects.get(slug="site-2"),
        )
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        devices = [
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
        ]
        with self.subTest():
            params = {"device_id": [devices[0].pk, devices[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device": [devices[0].name, devices[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cabled(self):
        with self.subTest():
            params = {"cabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"cabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_label(self):
        labels = ["consoleserverport1", "consoleserverport2"]
        params = {"label": labels}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cable(self):
        cable = Cable.objects.all()[:2]
        params = {"cable": [cable[0].pk, cable[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class PowerPortTestCase(FilterTestCases.FilterTestCase):
    queryset = PowerPort.objects.all()
    filterset = PowerPortFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        power_outlets = (
            devices[1].poweroutlets.get(name="Power Outlet 2"),
            devices[2].poweroutlets.get(name="Power Outlet 3"),
        )

        power_ports = (
            devices[0].powerports.get(name="Power Port 1"),
            devices[1].powerports.get(name="Power Port 2"),
            PowerPort.objects.create(name="Power Port 4", device=devices[2]),
        )

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(slug="connected")

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

    def test_name(self):
        params = {"name": ["Power Port 1", "Power Port 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_description(self):
        params = {"description": ["Power Port Description 1", "Power Port Description 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_maximum_draw(self):
        params = {"maximum_draw": [100, 200]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_allocated_draw(self):
        params = {"allocated_draw": [50, 100]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_connected(self):
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = [
            Region.objects.get(name="Region 1"),
            Region.objects.get(name="Region 2"),
        ]
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = [
            Site.objects.get(name="Site 1"),
            Site.objects.get(name="Site 2"),
        ]
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        devices = [
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
        ]
        with self.subTest():
            params = {"device_id": [devices[0].pk, devices[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device": [devices[0].name, devices[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cabled(self):
        with self.subTest():
            params = {"cabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"cabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_label(self):
        labels = ["powerport1", "powerport2"]
        params = {"label": labels}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_power_outlets(self):
        power_outlets = PowerOutlet.objects.all()[:2]
        params = {"power_outlets": [power_outlets[0].pk, power_outlets[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_power_outlets(self):
        with self.subTest():
            params = {"has_power_outlets": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_power_outlets": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_cable(self):
        cable = Cable.objects.all()[:2]
        params = {"cable": [cable[0].pk, cable[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class PowerOutletTestCase(FilterTestCases.FilterTestCase):
    queryset = PowerOutlet.objects.all()
    filterset = PowerOutletFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        power_outlets = (
            devices[1].poweroutlets.get(name="Power Outlet 2"),
            devices[2].poweroutlets.get(name="Power Outlet 3"),
        )

        power_ports = (
            devices[0].powerports.get(name="Power Port 1"),
            devices[1].powerports.get(name="Power Port 2"),
        )

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(slug="connected")

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

    def test_name(self):
        params = {"name": ["Power Outlet 1", "Power Outlet 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_description(self):
        params = {"description": ["Power Outlet Description 1", "Power Outlet Description 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_feed_leg(self):
        # TODO: Support filtering for multiple values
        params = {"feed_leg": PowerOutletFeedLegChoices.FEED_LEG_A}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_connected(self):
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_region(self):
        regions = (
            Region.objects.get(slug="region-1"),
            Region.objects.get(slug="region-2"),
        )
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (
            Site.objects.get(slug="site-1"),
            Site.objects.get(slug="site-2"),
        )
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        devices = [
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
        ]
        with self.subTest():
            params = {"device_id": [devices[0].pk, devices[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device": [devices[0].name, devices[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cabled(self):
        with self.subTest():
            params = {"cabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"cabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_label(self):
        labels = ["poweroutlet1", "poweroutlet2"]
        params = {"label": labels}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_power_port(self):
        power_port = PowerPort.objects.all()[:2]
        params = {"power_port": [power_port[0].pk, power_port[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cable(self):
        cable = Cable.objects.all()[:2]
        params = {"cable": [cable[0].pk, cable[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class InterfaceTestCase(FilterTestCases.FilterTestCase):
    queryset = Interface.objects.all()
    filterset = InterfaceFilterSet

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
        interface_status_map = {s.slug: s for s in interface_statuses.all()}

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
                status=interface_status_map["failed"],
                untagged_vlan=vlans[2],
            ),
            Interface.objects.create(
                device=devices[2],
                name="Parent Interface 2",
                type=InterfaceTypeChoices.TYPE_OTHER,
                mode=InterfaceModeChoices.MODE_TAGGED,
                enabled=True,
                mgmt_only=True,
                status=interface_status_map["planned"],
            ),
            Interface.objects.create(
                device=devices[2],
                name="Parent Interface 3",
                type=InterfaceTypeChoices.TYPE_OTHER,
                mode=InterfaceModeChoices.MODE_TAGGED,
                enabled=False,
                mgmt_only=True,
                status=interface_status_map["active"],
            ),
        )

        cabled_interfaces[3].tagged_vlans.add(vlans[0])
        cabled_interfaces[4].tagged_vlans.add(vlans[1])
        cabled_interfaces[5].tagged_vlans.add(vlans[2])

        Interface.objects.filter(pk=cabled_interfaces[0].pk).update(
            enabled=True,
            mac_address="00-00-00-00-00-01",
            mode=InterfaceModeChoices.MODE_ACCESS,
            mtu=100,
            status=interface_status_map["active"],
            untagged_vlan=vlans[0],
        )

        Interface.objects.filter(pk=cabled_interfaces[1].pk).update(
            enabled=True,
            mac_address="00-00-00-00-00-02",
            mode=InterfaceModeChoices.MODE_TAGGED,
            mtu=200,
            status=interface_status_map["planned"],
            untagged_vlan=vlans[1],
        )

        Interface.objects.filter(pk=cabled_interfaces[2].pk).update(
            enabled=False,
            mac_address="00-00-00-00-00-03",
            mode=InterfaceModeChoices.MODE_TAGGED_ALL,
            mtu=300,
            status=interface_status_map["failed"],
        )

        for interface in cabled_interfaces:
            interface.refresh_from_db()

        cable_statuses = Status.objects.get_for_model(Cable)
        cable_status_map = {cs.slug: cs for cs in cable_statuses.all()}

        # Cables
        Cable.objects.create(
            termination_a=cabled_interfaces[0],
            termination_b=cabled_interfaces[3],
            status=cable_status_map["connected"],
        )
        Cable.objects.create(
            termination_a=cabled_interfaces[1],
            termination_b=cabled_interfaces[4],
            status=cable_status_map["connected"],
        )
        # Third pair is not connected

        # Child interfaces
        Interface.objects.create(
            device=cabled_interfaces[3].device,
            name="Child 1",
            parent_interface=cabled_interfaces[3],
            status=interface_status_map["planned"],
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
        )
        Interface.objects.create(
            device=cabled_interfaces[4].device,
            name="Child 2",
            parent_interface=cabled_interfaces[4],
            status=interface_status_map["planned"],
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
        )
        Interface.objects.create(
            device=cabled_interfaces[5].device,
            name="Child 3",
            parent_interface=cabled_interfaces[5],
            status=interface_status_map["planned"],
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
        )

        # Bridged interfaces
        bridge_interfaces = (
            Interface.objects.create(
                device=devices[2],
                name="Bridge 1",
                status=interface_status_map["planned"],
                type=InterfaceTypeChoices.TYPE_BRIDGE,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Bridge 2",
                status=interface_status_map["planned"],
                type=InterfaceTypeChoices.TYPE_BRIDGE,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Bridge 3",
                status=interface_status_map["planned"],
                type=InterfaceTypeChoices.TYPE_BRIDGE,
            ),
        )
        Interface.objects.create(
            device=bridge_interfaces[0].device,
            name="Bridged 1",
            bridge=bridge_interfaces[0],
            status=interface_status_map["planned"],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
        )
        Interface.objects.create(
            device=bridge_interfaces[1].device,
            name="Bridged 2",
            bridge=bridge_interfaces[1],
            status=interface_status_map["planned"],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
        )
        Interface.objects.create(
            device=bridge_interfaces[2].device,
            name="Bridged 3",
            bridge=bridge_interfaces[2],
            status=interface_status_map["planned"],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
        )

        # LAG interfaces
        lag_interfaces = (
            Interface.objects.create(
                device=devices[2],
                name="LAG 1",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=interface_status_map["planned"],
            ),
            Interface.objects.create(
                device=devices[2],
                name="LAG 2",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=interface_status_map["planned"],
            ),
            Interface.objects.create(
                device=devices[2],
                name="LAG 3",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=interface_status_map["planned"],
            ),
        )
        Interface.objects.create(
            device=devices[2],
            name="Member 1",
            lag=lag_interfaces[0],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=interface_status_map["planned"],
        )
        Interface.objects.create(
            device=devices[2],
            name="Member 2",
            lag=lag_interfaces[1],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=interface_status_map["planned"],
        )
        Interface.objects.create(
            device=devices[2],
            name="Member 3",
            lag=lag_interfaces[2],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=interface_status_map["planned"],
        )

    def test_name(self):
        params = {"name": ["Interface 1", "Interface 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_connected(self):
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 17)

    def test_enabled(self):
        with self.subTest():
            params = {"enabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 19)
        with self.subTest():
            params = {"enabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_mtu(self):
        params = {"mtu": [100, 200]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_mgmt_only(self):
        with self.subTest():
            params = {"mgmt_only": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"mgmt_only": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 17)

    def test_mode(self):
        params = {"mode": InterfaceModeChoices.MODE_ACCESS}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_description(self):
        params = {"description": ["Interface Description 1", "Interface Description 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_parent(self):
        parent_interfaces = Interface.objects.filter(name__startswith="Parent")[:2]
        params = {"parent_interface": [parent_interfaces[0].pk, parent_interfaces[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_bridge(self):
        bridge_interfaces = Interface.objects.filter(type=InterfaceTypeChoices.TYPE_BRIDGE)[:2]
        params = {"bridge": [bridge_interfaces[0].pk, bridge_interfaces[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_lag(self):
        lag_interfaces = Interface.objects.filter(type=InterfaceTypeChoices.TYPE_LAG)[:2]
        with self.subTest():
            params = {"lag_id": [lag_interfaces[0].pk, lag_interfaces[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"lag": [lag_interfaces[0].pk, lag_interfaces[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device_with_common_vc(self):
        """Assert only interfaces belonging to devices with common VC are returned"""
        site = Site.objects.first()
        device_type = DeviceType.objects.first()
        device_role = DeviceRole.objects.first()
        devices = (
            Device.objects.create(
                name="Device in vc 1",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device in vc 2",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device not in vc",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
        )

        # VirtualChassis assignment for filtering
        virtual_chassis = VirtualChassis.objects.create(master=devices[0])
        Device.objects.filter(pk=devices[0].pk).update(virtual_chassis=virtual_chassis, vc_position=1, vc_priority=1)
        Device.objects.filter(pk=devices[1].pk).update(virtual_chassis=virtual_chassis, vc_position=2, vc_priority=2)

        Interface.objects.create(device=devices[0], name="int1")
        Interface.objects.create(device=devices[0], name="int2")
        Interface.objects.create(device=devices[1], name="int3")
        Interface.objects.create(device=devices[2], name="int4")

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

    def test_region(self):
        regions = (Region.objects.get(name="Region 1"), Region.objects.get(name="Region 2"))
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (Site.objects.get(name="Site 1"), Site.objects.get(name="Site 2"))
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        devices = [
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
        ]
        with self.subTest():
            params = {"device_id": [devices[0].pk, devices[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device": [devices[0].name, devices[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cabled(self):
        with self.subTest():
            params = {"cabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"cabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 17)

    def test_kind(self):
        with self.subTest():
            params = {"kind": "physical"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 12)
        with self.subTest():
            params = {"kind": "virtual"}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 9)

    def test_mac_address(self):
        params = {"mac_address": ["00-00-00-00-00-01", "00-00-00-00-00-02"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type(self):
        params = {
            "type": [
                InterfaceTypeChoices.TYPE_1GE_FIXED,
                InterfaceTypeChoices.TYPE_1GE_GBIC,
            ]
        }
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_vlan(self):
        vlan = VLAN.objects.filter(
            Q(interfaces_as_untagged__isnull=False) | Q(interfaces_as_tagged__isnull=False)
        ).first()
        params = {"vlan": vlan.vid}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(Q(untagged_vlan=vlan) | Q(tagged_vlans=vlan))
        )

    def test_vlan_id(self):
        vlan = VLAN.objects.filter(
            Q(interfaces_as_untagged__isnull=False) | Q(interfaces_as_tagged__isnull=False)
        ).first()
        params = {"vlan_id": vlan.id}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(Q(untagged_vlan=vlan) | Q(tagged_vlans=vlan))
        )

    def test_status(self):
        statuses = list(Status.objects.get_for_model(Interface)[:2])
        params = {"status": [statuses[0].slug, statuses[1].slug]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(status__slug__in=params["status"]).count(),
        )

    def test_label(self):
        labels = ["interface1", "interface2"]
        params = {"label": labels}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cable(self):
        cable = Cable.objects.all()[:2]
        params = {"cable": [cable[0].pk, cable[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_untagged_vlan(self):
        untagged_vlans = list(VLAN.objects.filter(interfaces_as_untagged__isnull=False))[:2]
        params = {"untagged_vlan": [untagged_vlans[0].pk, untagged_vlans[1].vid]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(untagged_vlan__in=untagged_vlans)
        )

    def test_tagged_vlans(self):
        tagged_vlans = list(VLAN.objects.filter(interfaces_as_tagged__isnull=False))[:2]
        params = {"tagged_vlans": [tagged_vlans[0].pk, tagged_vlans[1].vid]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(tagged_vlans__in=tagged_vlans)
        )

    def test_has_tagged_vlans(self):
        with self.subTest():
            params = {"has_tagged_vlans": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_tagged_vlans": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 18)

    def test_child_interfaces(self):
        child_interfaces = Interface.objects.filter(name__startswith="Child")[:2]
        params = {"child_interfaces": [child_interfaces[0].pk, child_interfaces[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_child_interfaces(self):
        with self.subTest():
            params = {"has_child_interfaces": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_child_interfaces": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 18)

    def test_bridged_interfaces(self):
        bridged_interfaces = Interface.objects.filter(name__startswith="Bridged")[:2]
        params = {"bridged_interfaces": [bridged_interfaces[0].pk, bridged_interfaces[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_bridged_interfaces(self):
        with self.subTest():
            params = {"has_bridged_interfaces": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_bridged_interfaces": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 18)

    def test_member_interfaces(self):
        member_interfaces = Interface.objects.filter(name__startswith="Member")[:2]
        params = {"member_interfaces": [member_interfaces[0].pk, member_interfaces[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_member_interfaces(self):
        with self.subTest():
            params = {"has_member_interfaces": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_member_interfaces": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 18)


class FrontPortTestCase(FilterTestCases.FilterTestCase):
    queryset = FrontPort.objects.all()
    filterset = FrontPortFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        rear_ports = (
            devices[0].rearports.get(name="Rear Port 1"),
            devices[1].rearports.get(name="Rear Port 2"),
            devices[2].rearports.get(name="Rear Port 3"),
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
            devices[0].frontports.get(name="Front Port 1"),
            devices[1].frontports.get(name="Front Port 2"),
            devices[2].frontports.get(name="Front Port 3"),
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

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(slug="connected")

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

    def test_name(self):
        params = {"name": ["Front Port 1", "Front Port 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type(self):
        # TODO: Test for multiple values
        params = {"type": PortTypeChoices.TYPE_8P8C}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_description(self):
        params = {"description": ["Front Port Description 1", "Front Port Description 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = (Region.objects.get(name="Region 1"), Region.objects.get(name="Region 2"))
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (Site.objects.get(name="Site 1"), Site.objects.get(name="Site 2"))
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        devices = [
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
        ]
        with self.subTest():
            params = {"device_id": [devices[0].pk, devices[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device": [devices[0].name, devices[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cabled(self):
        with self.subTest():
            params = {"cabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"cabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_label(self):
        labels = ["frontport1", "frontport2"]
        params = {"label": labels}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_rear_port(self):
        rear_port = (RearPort.objects.get(name="Rear Port 1"), RearPort.objects.get(name="Rear Port 2"))
        params = {"rear_port": [rear_port[0].pk, rear_port[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_rear_port_position(self):
        params = {"rear_port_position": [2, 3]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cable(self):
        cable = Cable.objects.all()[:2]
        params = {"cable": [cable[0].pk, cable[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)


class RearPortTestCase(FilterTestCases.FilterTestCase):
    queryset = RearPort.objects.all()
    filterset = RearPortFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        rear_ports = (
            devices[0].rearports.get(name="Rear Port 1"),
            devices[1].rearports.get(name="Rear Port 2"),
            devices[2].rearports.get(name="Rear Port 3"),
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

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(slug="connected")

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

    def test_name(self):
        params = {"name": ["Rear Port 1", "Rear Port 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type(self):
        # TODO: Test for multiple values
        params = {"type": PortTypeChoices.TYPE_8P8C}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_positions(self):
        params = {"positions": [1, 2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_description(self):
        params = {"description": ["Rear Port Description 1", "Rear Port Description 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = (Region.objects.get(name="Region 1"), Region.objects.get(name="Region 2"))
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (Site.objects.get(name="Site 1"), Site.objects.get(name="Site 2"))
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        devices = [
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
        ]
        with self.subTest():
            params = {"device_id": [devices[0].pk, devices[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device": [devices[0].name, devices[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cabled(self):
        with self.subTest():
            params = {"cabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"cabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_label(self):
        labels = ["rearport1", "rearport2"]
        params = {"label": labels}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_front_ports(self):
        front_ports = (FrontPort.objects.get(name="Front Port 1"), FrontPort.objects.get(name="Front Port 2"))
        params = {"front_ports": [front_ports[0].pk, front_ports[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_front_ports(self):
        with self.subTest():
            params = {"has_front_ports": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_front_ports": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cable(self):
        cable = Cable.objects.all()[:2]
        params = {"cable": [cable[0].pk, cable[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)


class DeviceBayTestCase(FilterTestCases.FilterTestCase):
    queryset = DeviceBay.objects.all()
    filterset = DeviceBayFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        device_role = DeviceRole.objects.first()
        parent_device_type = DeviceType.objects.get(slug="model-2")
        child_device_type = DeviceType.objects.get(slug="model-3")
        site = Site.objects.get(name="Site 3")

        device_statuses = Status.objects.get_for_model(Device)
        device_status_map = {ds.slug: ds for ds in device_statuses.all()}

        child_devices = (
            Device.objects.create(
                name="Child Device 1",
                device_type=child_device_type,
                device_role=device_role,
                site=site,
                status=device_status_map["active"],
            ),
            Device.objects.create(
                name="Child Device 2",
                device_type=child_device_type,
                device_role=device_role,
                site=site,
                status=device_status_map["active"],
            ),
        )

        parent_devices = (
            Device.objects.create(
                name="Parent Device 1",
                device_type=parent_device_type,
                device_role=device_role,
                site=site,
                status=device_status_map["active"],
            ),
            Device.objects.create(
                name="Parent Device 2",
                device_type=parent_device_type,
                device_role=device_role,
                site=site,
                status=device_status_map["active"],
            ),
        )

        device_bays = (
            parent_devices[0].devicebays.first(),
            parent_devices[1].devicebays.first(),
        )
        device_bays[0].installed_device = child_devices[0]
        device_bays[1].installed_device = child_devices[1]
        device_bays[0].save()
        device_bays[1].save()

    def test_name(self):
        params = {"name": ["Device Bay 1", "Device Bay 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_description(self):
        params = {"description": ["Device Bay Description 1", "Device Bay Description 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_region(self):
        regions = (Region.objects.get(name="Region 1"), Region.objects.get(name="Region 2"))
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (Site.objects.get(name="Site 1"), Site.objects.get(name="Site 2"))
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        devices = [
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
        ]
        with self.subTest():
            params = {"device_id": [devices[0].pk, devices[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device": [devices[0].name, devices[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_label(self):
        labels = ["devicebay1", "devicebay2"]
        params = {"label": labels}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_installed_device(self):
        installed_device = Device.objects.filter(name__startswith="Child")
        params = {"installed_device": [installed_device[0].pk, installed_device[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class InventoryItemTestCase(FilterTestCases.FilterTestCase):
    queryset = InventoryItem.objects.all()
    filterset = InventoryItemFilterSet

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

        InventoryItem.objects.create(device=devices[0], name="Inventory Item 1A", parent=inventory_items[0])
        InventoryItem.objects.create(device=devices[1], name="Inventory Item 2A", parent=inventory_items[1])
        InventoryItem.objects.create(device=devices[2], name="Inventory Item 3A", parent=inventory_items[2])

    def test_name(self):
        params = {"name": ["Inventory Item 1", "Inventory Item 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_part_id(self):
        params = {"part_id": ["1001", "1002"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_asset_tag(self):
        params = {"asset_tag": ["1001", "1002"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_discovered(self):
        # TODO: Fix boolean value
        with self.subTest():
            params = {"discovered": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"discovered": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_region(self):
        regions = (
            Region.objects.get(slug="region-1"),
            Region.objects.get(slug="region-2"),
        )
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_site(self):
        sites = (
            Site.objects.get(slug="site-1"),
            Site.objects.get(slug="site-2"),
        )
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_device(self):
        # TODO: Allow multiple values
        device = Device.objects.first()
        with self.subTest():
            params = {"device_id": device.pk}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"device": device.name}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_parent_id(self):
        parent_items = InventoryItem.objects.filter(parent__isnull=True)[:2]
        params = {"parent_id": [parent_items[0].pk, parent_items[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_parent(self):
        parent = InventoryItem.objects.exclude(name__contains="A")[:2]
        params = {"parent": [parent[0].name, parent[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_manufacturer(self):
        manufacturers = Manufacturer.objects.all()[:2]
        with self.subTest():
            params = {"manufacturer_id": [manufacturers[0].pk, manufacturers[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"manufacturer": [manufacturers[0].slug, manufacturers[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_serial(self):
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

    def test_description(self):
        params = {"description": ["First", "Second"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_label(self):
        params = {"label": ["inventoryitem2", "inventoryitem3"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_child_items(self):
        child_items = InventoryItem.objects.filter(parent__isnull=False)[:2]
        params = {"child_items": [child_items[0].pk, child_items[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_child_items(self):
        with self.subTest():
            params = {"has_child_items": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_child_items": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)


class VirtualChassisTestCase(FilterTestCases.FilterTestCase):
    queryset = VirtualChassis.objects.all()
    filterset = VirtualChassisFilterSet

    @classmethod
    def setUpTestData(cls):

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Model 1", slug="model-1")
        device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")

        cls.regions = Region.objects.filter(sites__isnull=False)[:3]

        cls.sites = (
            Site.objects.filter(region=cls.regions[0]).first(),
            Site.objects.filter(region=cls.regions[1]).first(),
            Site.objects.filter(region=cls.regions[2]).first(),
        )
        devices = (
            Device.objects.create(
                name="Device 1",
                device_type=device_type,
                device_role=device_role,
                site=cls.sites[0],
                vc_position=1,
            ),
            Device.objects.create(
                name="Device 2",
                device_type=device_type,
                device_role=device_role,
                site=cls.sites[0],
                vc_position=2,
            ),
            Device.objects.create(
                name="Device 3",
                device_type=device_type,
                device_role=device_role,
                site=cls.sites[1],
                vc_position=1,
            ),
            Device.objects.create(
                name="Device 4",
                device_type=device_type,
                device_role=device_role,
                site=cls.sites[1],
                vc_position=2,
            ),
            Device.objects.create(
                name="Device 5",
                device_type=device_type,
                device_role=device_role,
                site=cls.sites[2],
                vc_position=1,
            ),
            Device.objects.create(
                name="Device 6",
                device_type=device_type,
                device_role=device_role,
                site=cls.sites[2],
                vc_position=2,
            ),
        )

        virtual_chassis = (
            VirtualChassis.objects.create(name="VC 1", master=devices[0], domain="Domain 1"),
            VirtualChassis.objects.create(name="VC 2", master=devices[2], domain="Domain 2"),
            VirtualChassis.objects.create(name="VC 3", master=devices[4], domain="Domain 3"),
            VirtualChassis.objects.create(name="VC 4"),
        )

        Device.objects.filter(pk=devices[1].pk).update(virtual_chassis=virtual_chassis[0])
        Device.objects.filter(pk=devices[3].pk).update(virtual_chassis=virtual_chassis[1])
        Device.objects.filter(pk=devices[5].pk).update(virtual_chassis=virtual_chassis[2])

    def test_domain(self):
        params = {"domain": ["Domain 1", "Domain 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_master(self):
        masters = Device.objects.all()
        with self.subTest():
            params = {"master_id": [masters[0].pk, masters[2].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"master": [masters[0].name, masters[2].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_name(self):
        params = {"name": ["VC 1", "VC 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        with self.subTest():
            params = {"region_id": [self.regions[0].pk, self.regions[1].pk]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(master__site__region__in=[self.regions[0].pk, self.regions[1].pk])
                .distinct()
                .count(),
            )
        with self.subTest():
            params = {"region": [self.regions[0].slug, self.regions[1].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(master__site__region__slug__in=[self.regions[0].slug, self.regions[1].slug])
                .distinct()
                .count(),
            )

    def test_site(self):
        with self.subTest():
            params = {"site_id": [self.sites[0].pk, self.sites[1].pk]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(master__site__in=[self.sites[0].pk, self.sites[1].pk]).distinct().count(),
            )
        with self.subTest():
            params = {"site": [self.sites[0].slug, self.sites[1].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(master__site__slug__in=[self.sites[0].slug, self.sites[1].slug])
                .distinct()
                .count(),
            )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_members(self):
        members = Device.objects.filter(name__in=["Device 2", "Device 4"])[:2]
        params = {"members": [members[0].pk, members[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_members(self):
        with self.subTest():
            params = {"has_members": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_members": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class CableTestCase(FilterTestCases.FilterTestCase):
    queryset = Cable.objects.all()
    filterset = CableFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        tenants = Tenant.objects.all()[:3]

        cls.sites = Site.objects.all()[:3]
        racks = (
            Rack.objects.get(name="Rack 1"),
            Rack.objects.get(name="Rack 2"),
            Rack.objects.get(name="Rack 3"),
        )

        device_types = (
            DeviceType.objects.get(slug="model-1"),
            DeviceType.objects.get(slug="model-2"),
            DeviceType.objects.get(slug="model-3"),
        )

        device_role = DeviceRole.objects.first()

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
            Device.objects.create(
                name="Device 4",
                device_type=device_types[0],
                device_role=device_role,
                tenant=tenants[0],
                site=cls.sites[0],
                rack=racks[0],
                position=2,
            ),
            Device.objects.create(
                name="Device 5",
                device_type=device_types[1],
                device_role=device_role,
                tenant=tenants[1],
                site=cls.sites[1],
                rack=racks[1],
                position=1,
            ),
            Device.objects.create(
                name="Device 6",
                device_type=device_types[2],
                device_role=device_role,
                tenant=tenants[2],
                site=cls.sites[2],
                rack=racks[2],
                position=2,
            ),
        )

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
            ),
            Interface.objects.create(
                device=devices[1],
                name="Interface 8",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Interface 9",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            ),
            Interface.objects.create(
                device=devices[3],
                name="Interface 10",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            ),
            Interface.objects.create(
                device=devices[4],
                name="Interface 11",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            ),
            Interface.objects.create(
                device=devices[5],
                name="Interface 12",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            ),
        )

        statuses = Status.objects.get_for_model(Cable)
        cls.status_connected = statuses.get(slug="connected")
        cls.status_planned = statuses.get(slug="planned")

        # Cables
        Cable.objects.create(
            termination_a=interfaces[0],
            termination_b=interfaces[3],
            label="Cable 1",
            type=CableTypeChoices.TYPE_MMF,
            status=cls.status_connected,
            color="aa1409",
            length=10,
            length_unit=CableLengthUnitChoices.UNIT_FOOT,
        )
        Cable.objects.create(
            termination_a=interfaces[1],
            termination_b=interfaces[4],
            label="Cable 2",
            type=CableTypeChoices.TYPE_MMF,
            status=cls.status_connected,
            color="aa1409",
            length=20,
            length_unit=CableLengthUnitChoices.UNIT_FOOT,
        )
        Cable.objects.create(
            termination_a=interfaces[2],
            termination_b=interfaces[5],
            label="Cable 3",
            type=CableTypeChoices.TYPE_CAT5E,
            status=cls.status_connected,
            color="f44336",
            length=30,
            length_unit=CableLengthUnitChoices.UNIT_FOOT,
        )
        Cable.objects.create(
            termination_a=interfaces[6],
            termination_b=interfaces[9],
            label="Cable 4",
            type=CableTypeChoices.TYPE_CAT5E,
            status=cls.status_planned,
            color="f44336",
            length=40,
            length_unit=CableLengthUnitChoices.UNIT_FOOT,
        )
        Cable.objects.create(
            termination_a=interfaces[7],
            termination_b=interfaces[10],
            label="Cable 5",
            type=CableTypeChoices.TYPE_CAT6,
            status=cls.status_planned,
            color="e91e63",
            length=10,
            length_unit=CableLengthUnitChoices.UNIT_METER,
        )

        console_port = ConsolePort.objects.filter(device=devices[2]).first()
        console_server_port = ConsoleServerPort.objects.filter(device=devices[5]).first()
        Cable.objects.create(
            termination_a=console_port,
            termination_b=console_server_port,
            label="Cable 6",
            type=CableTypeChoices.TYPE_CAT6,
            status=cls.status_planned,
            color="e91e63",
            length=20,
            length_unit=CableLengthUnitChoices.UNIT_METER,
        )

    def test_label(self):
        params = {"label": ["Cable 1", "Cable 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_length(self):
        params = {"length": [10, 20]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_length_unit(self):
        params = {"length_unit": CableLengthUnitChoices.UNIT_FOOT}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_type(self):
        params = {"type": [CableTypeChoices.TYPE_MMF, CableTypeChoices.TYPE_CAT5E]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_status(self):
        statuses = list(Status.objects.get_for_model(Site)[:2])
        with self.subTest():
            params = {"status": [statuses[0].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(status__slug__in=params["status"]).count(),
            )
        with self.subTest():
            params = {"status": [statuses[1].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                self.queryset.filter(status__slug__in=params["status"]).count(),
            )

    def test_color(self):
        params = {"color": ["aa1409", "f44336"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_device(self):
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
        racks = Rack.objects.all()[:2]
        with self.subTest():
            params = {"rack_id": [racks[0].pk, racks[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"rack": [racks[0].name, racks[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_site(self):
        with self.subTest():
            params = {"site_id": [self.sites[0].pk, self.sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        with self.subTest():
            params = {"site": [self.sites[0].slug, self.sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_tenant(self):
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
            params = {"tenant": [tenants[0].slug, tenants[1].slug]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(
                    Q(_termination_a_device__tenant__in=tenants) | Q(_termination_b_device__tenant__in=tenants)
                ),
            )

    def test_termination_type(self):
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

    def test_termination_id(self):
        cable_terminations_a = Interface.objects.filter(name__in=["Interface 7", "Interface 8"])
        cable_terminations_b = Interface.objects.filter(name__in=["Interface 10", "Interface 11"])
        with self.subTest():
            params = {"termination_a_id": [cable_terminations_a[0].pk, cable_terminations_a[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"termination_b_id": [cable_terminations_b[0].pk, cable_terminations_b[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class PowerPanelTestCase(FilterTestCases.FilterTestCase):
    queryset = PowerPanel.objects.all()
    filterset = PowerPanelFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        site = Site.objects.create(name="Site 4")
        PowerPanel.objects.create(name="Power Panel 4", site=site)

    def test_name(self):
        params = {"name": ["Power Panel 1", "Power Panel 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = (
            Region.objects.get(slug="region-1"),
            Region.objects.get(slug="region-2"),
        )
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (
            Site.objects.get(slug="site-1"),
            Site.objects.get(slug="site-2"),
        )
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_rack_group(self):
        rack_groups = RackGroup.objects.all()[:2]
        with self.subTest():
            params = {"rack_group_id": [rack_groups[0].pk, rack_groups[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"rack_group": [rack_groups[0].pk, rack_groups[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_power_feeds(self):
        power_feeds = PowerFeed.objects.all()[:2]
        params = {"power_feeds": [power_feeds[0].pk, power_feeds[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_power_feeds(self):
        with self.subTest():
            params = {"has_power_feeds": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        with self.subTest():
            params = {"has_power_feeds": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class PowerFeedTestCase(FilterTestCases.FilterTestCase):
    queryset = PowerFeed.objects.all()
    filterset = PowerFeedFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        power_feeds = (
            PowerFeed.objects.get(name="Power Feed 1"),
            PowerFeed.objects.get(name="Power Feed 2"),
            PowerFeed.objects.get(name="Power Feed 3"),
        )

        pf_statuses = Status.objects.get_for_model(PowerFeed)
        pf_status_map = {s.slug: s for s in pf_statuses.all()}

        PowerFeed.objects.filter(pk=power_feeds[0].pk).update(
            status=pf_status_map["active"],
            type=PowerFeedTypeChoices.TYPE_PRIMARY,
            supply=PowerFeedSupplyChoices.SUPPLY_AC,
            phase=PowerFeedPhaseChoices.PHASE_3PHASE,
            voltage=100,
            amperage=100,
            max_utilization=10,
            comments="PFA",
        )
        PowerFeed.objects.filter(pk=power_feeds[1].pk).update(
            status=pf_status_map["failed"],
            type=PowerFeedTypeChoices.TYPE_PRIMARY,
            supply=PowerFeedSupplyChoices.SUPPLY_AC,
            phase=PowerFeedPhaseChoices.PHASE_3PHASE,
            voltage=200,
            amperage=200,
            max_utilization=20,
            comments="PFB",
        )
        PowerFeed.objects.filter(pk=power_feeds[2].pk).update(
            status=pf_status_map["offline"],
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
        status_connected = cable_statuses.get(slug="connected")

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

    def test_name(self):
        params = {"name": ["Power Feed 1", "Power Feed 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_status(self):
        statuses = list(Status.objects.get_for_model(PowerFeed)[:2])
        params = {"status": [statuses[0].slug, statuses[1].slug]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(status__slug__in=params["status"]).count(),
        )

    def test_type(self):
        params = {"type": PowerFeedTypeChoices.TYPE_PRIMARY}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_supply(self):
        params = {"supply": PowerFeedSupplyChoices.SUPPLY_AC}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_phase(self):
        params = {"phase": PowerFeedPhaseChoices.PHASE_3PHASE}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_voltage(self):
        params = {"voltage": [100, 200]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_amperage(self):
        params = {"amperage": [100, 200]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_max_utilization(self):
        params = {"max_utilization": [10, 20]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = (
            Region.objects.get(slug="region-1"),
            Region.objects.get(slug="region-2"),
        )
        with self.subTest():
            params = {"region_id": [regions[0].pk, regions[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"region": [regions[0].slug, regions[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = (
            Site.objects.get(slug="site-1"),
            Site.objects.get(slug="site-2"),
        )
        with self.subTest():
            params = {"site_id": [sites[0].pk, sites[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"site": [sites[0].slug, sites[1].slug]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_power_panel_id(self):
        power_panels = PowerPanel.objects.all()[:2]
        params = {"power_panel_id": [power_panels[0].pk, power_panels[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_rack_id(self):
        racks = Rack.objects.all()[:2]
        params = {"rack_id": [racks[0].pk, racks[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cabled(self):
        with self.subTest():
            params = {"cabled": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"cabled": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_connected(self):
        with self.subTest():
            params = {"connected": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        with self.subTest():
            params = {"connected": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_power_panel(self):
        power_panel = PowerPanel.objects.all()[:2]
        params = {"power_panel": [power_panel[0].pk, power_panel[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_rack(self):
        rack = Rack.objects.all()[:2]
        params = {"rack": [rack[0].pk, rack[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_available_power(self):
        params = {"available_power": [1732, 27000]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_comments(self):
        params = {"comments": ["PFA", "PFC"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cable(self):
        cable = Cable.objects.all()[:2]
        params = {"cable": [cable[0].pk, cable[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class DeviceRedundancyGroupTestCase(FilterTestCases.FilterTestCase):
    queryset = DeviceRedundancyGroup.objects.all()
    filterset = DeviceRedundancyGroupFilterSet

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        device_redundancy_groups = list(DeviceRedundancyGroup.objects.all()[:2])

        secrets_groups = list(SecretsGroup.objects.all()[:2])

        device_redundancy_groups[0].secrets_group = secrets_groups[0]
        device_redundancy_groups[0].validated_save()

        device_redundancy_groups[1].secrets_group = secrets_groups[1]
        device_redundancy_groups[1].validated_save()

    def test_name(self):
        device_redundancy_groups = list(DeviceRedundancyGroup.objects.all()[:2])
        params = {"name": [device_redundancy_groups[0].name, device_redundancy_groups[1].name]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            DeviceRedundancyGroup.objects.filter(name__in=params["name"]).count(),
        )

    def test_slug(self):
        device_redundancy_group = DeviceRedundancyGroup.objects.first()
        params = {"slug": [device_redundancy_group.slug]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            DeviceRedundancyGroup.objects.filter(slug__in=params["slug"]).count(),
        )

    def test_secrets_group(self):
        secrets_groups = list(SecretsGroup.objects.all()[:2])
        with self.subTest():
            params = {"secrets_group": [secrets_groups[0].pk, secrets_groups[1].pk]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                DeviceRedundancyGroup.objects.filter(secrets_group__in=params["secrets_group"]).count(),
            )
        with self.subTest():
            params = {"secrets_group": [secrets_groups[0].slug, secrets_groups[1].slug]}
            self.assertEqual(
                self.filterset(params, self.queryset).qs.count(),
                DeviceRedundancyGroup.objects.filter(secrets_group__slug__in=params["secrets_group"]).count(),
            )

    def test_failover_strategy(self):
        with self.subTest():
            params = {"failover_strategy": "active-active"}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                DeviceRedundancyGroup.objects.filter(failover_strategy="active-active"),
            )
        with self.subTest():
            params = {"failover_strategy": "active-passive"}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                DeviceRedundancyGroup.objects.filter(failover_strategy="active-passive"),
            )


# TODO: Connection filters
