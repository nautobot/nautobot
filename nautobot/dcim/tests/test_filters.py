# pylint: disable=no-member  # it doesn't recognize the class attributes assigned in common_test_data()
import uuid

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
    PowerFeedBreakerPoleChoices,
    PowerFeedPhaseChoices,
    PowerFeedSupplyChoices,
    PowerFeedTypeChoices,
    PowerOutletFeedLegChoices,
    PowerPathChoices,
    RackDimensionUnitChoices,
    RackTypeChoices,
    RackWidthChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.constants import NONCONNECTABLE_IFACE_TYPES, VIRTUAL_IFACE_TYPES
from nautobot.dcim.filters import (
    CableFilterSet,
    ConsolePortFilterSet,
    ConsolePortTemplateFilterSet,
    ConsoleServerPortFilterSet,
    ConsoleServerPortTemplateFilterSet,
    ControllerFilterSet,
    ControllerManagedDeviceGroupFilterSet,
    DeviceBayFilterSet,
    DeviceBayTemplateFilterSet,
    DeviceFamilyFilterSet,
    DeviceFilterSet,
    DeviceRedundancyGroupFilterSet,
    DeviceTypeFilterSet,
    DeviceTypeToSoftwareImageFileFilterSet,
    FrontPortFilterSet,
    FrontPortTemplateFilterSet,
    InterfaceFilterSet,
    InterfaceRedundancyGroupAssociationFilterSet,
    InterfaceRedundancyGroupFilterSet,
    InterfaceTemplateFilterSet,
    InterfaceVDCAssignmentFilterSet,
    InventoryItemFilterSet,
    LocationFilterSet,
    LocationTypeFilterSet,
    ManufacturerFilterSet,
    ModuleBayFilterSet,
    ModuleBayTemplateFilterSet,
    ModuleFamilyFilterSet,
    ModuleFilterSet,
    ModuleTypeFilterSet,
    PlatformFilterSet,
    PowerFeedFilterSet,
    PowerOutletFilterSet,
    PowerOutletTemplateFilterSet,
    PowerPanelFilterSet,
    PowerPortFilterSet,
    PowerPortTemplateFilterSet,
    RackFilterSet,
    RackGroupFilterSet,
    RackReservationFilterSet,
    RearPortFilterSet,
    RearPortTemplateFilterSet,
    SoftwareImageFileFilterSet,
    SoftwareVersionFilterSet,
    VirtualChassisFilterSet,
    VirtualDeviceContextFilterSet,
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
    InterfaceRedundancyGroupAssociation,
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
from nautobot.extras.filters.mixins import RoleFilter, StatusFilter
from nautobot.extras.models import ExternalIntegration, Role, SecretsGroup, Status, Tag
from nautobot.ipam.models import IPAddress, Namespace, Prefix, Service, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine
from nautobot.wireless.models import RadioProfile, WirelessNetwork

# Use the proper swappable User model
User = get_user_model()


def common_test_data(cls):
    Controller.objects.filter(controller_device__isnull=False).delete()
    Device.objects.all().delete()
    tenants = Tenant.objects.filter(tenant_group__isnull=False)
    cls.tenants = tenants
    cls.software_versions = SoftwareVersion.objects.all()

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
    cls.loc2 = loc2
    cls.loc3 = loc3

    provider = Provider.objects.first()
    circuit_type = CircuitType.objects.first()
    circuit_status = Status.objects.get_for_model(Circuit).first()
    circuit = Circuit.objects.create(
        provider=provider, circuit_type=circuit_type, cid="Test Circuit 1", status=circuit_status
    )
    CircuitTermination.objects.create(circuit=circuit, location=loc0, term_side="A")
    CircuitTermination.objects.create(circuit=circuit, location=loc1, term_side="Z")

    manufacturers = list(
        Manufacturer.objects.filter(device_types__isnull=False, platforms__isnull=False).distinct()[:3]
    )
    cls.manufacturers = manufacturers
    device_families = list(DeviceFamily.objects.all())

    platforms = Platform.objects.filter(manufacturer__in=manufacturers)[:3]
    for num, platform in enumerate(platforms):
        platform.napalm_driver = f"driver-{num}"
        platform.napalm_args = ["--test", f"--arg{num}"]
        platform.network_driver = f"driver_{num}"
        platform.save()
    cls.platforms = platforms

    device_types = (
        DeviceType.objects.create(
            manufacturer=manufacturers[0],
            device_family=device_families[0],
            comments="Device type 1",
            model="Model 1",
            part_number="Part Number 1",
            u_height=1,
            is_full_depth=True,
        ),
        DeviceType.objects.create(
            manufacturer=manufacturers[1],
            device_family=device_families[1],
            comments="Device type 2",
            model="Model 2",
            part_number="Part Number 2",
            u_height=2,
            is_full_depth=True,
            subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
        ),
        DeviceType.objects.create(
            manufacturer=manufacturers[2],
            device_family=device_families[2],
            comments="Device type 3",
            model="Model 3",
            part_number="Part Number 3",
            u_height=3,
            is_full_depth=False,
            subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
        ),
    )
    device_types[0].software_image_files.set(SoftwareImageFile.objects.all()[:2])
    device_types[1].software_image_files.set(SoftwareImageFile.objects.all()[2:4])
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
        PowerPanel.objects.create(name="Power Panel 4", location=loc0),
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
        cluster=clusters[0],
        name="VM 1",
        role=cls.device_roles[0],
        platform=platforms[0],
        status=vm_status,
        software_version=cls.software_versions[0],
    )
    VirtualMachine.objects.create(
        cluster=clusters[0],
        name="VM 2",
        role=cls.device_roles[1],
        platform=platforms[1],
        status=vm_status,
        software_version=cls.software_versions[1],
    )
    VirtualMachine.objects.create(
        cluster=clusters[0],
        name="VM 3",
        role=cls.device_roles[2],
        platform=platforms[2],
        status=vm_status,
        software_version=cls.software_versions[2],
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
        PowerFeed.objects.create(
            name="Power Feed 3",
            rack=racks[2],
            power_panel=power_panels[2],
            status=pf_status,
            destination_panel=power_panels[0],
        ),
        PowerFeed.objects.create(
            name="Power Feed 4",
            power_panel=power_panels[1],
            status=pf_status,
            destination_panel=power_panels[3],
        ),
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
        name="Test Interface 1",
        description="Interface Description 1",
        device_type=device_types[0],
        label="interface1",
        mgmt_only=True,
        type=InterfaceTypeChoices.TYPE_1GE_SFP,
    )
    InterfaceTemplate.objects.create(
        name="Test Interface 2",
        description="Interface Description 2",
        device_type=device_types[1],
        label="interface2",
        mgmt_only=False,
        type=InterfaceTypeChoices.TYPE_1GE_GBIC,
    )
    InterfaceTemplate.objects.create(
        name="Test Interface 3",
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

    cls.module_families = (
        ModuleFamily.objects.create(name="Module Family 1"),
        ModuleFamily.objects.create(name="Module Family 2"),
        ModuleFamily.objects.create(name="Module Family 3"),
    )
    ModuleBayTemplate.objects.create(
        device_type=device_types[0],
        name="device test module bay 1",
        position=1,
        label="devicemodulebay1",
        description="device test module bay 1 description",
        module_family=cls.module_families[0],
        requires_first_party_modules=True,
    )
    ModuleBayTemplate.objects.create(
        device_type=device_types[1],
        name="device test module bay 2",
        position=2,
        label="devicemodulebay2",
        description="device test module bay 2 description",
        module_family=cls.module_families[1],
        requires_first_party_modules=False,
    )
    ModuleBayTemplate.objects.create(
        device_type=device_types[2],
        name="device test module bay 3",
        position=3,
        label="devicemodulebay3",
        description="device test module bay 3 without a module family",
        requires_first_party_modules=True,
    )
    secrets_groups = (
        SecretsGroup.objects.create(name="Secrets group 1"),
        SecretsGroup.objects.create(name="Secrets group 2"),
        SecretsGroup.objects.create(name="Secrets group 3"),
    )

    device_statuses = Status.objects.get_for_model(Device)
    cls.devices = (
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
            software_version=cls.software_versions[0],
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
            software_version=cls.software_versions[1],
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
            software_version=cls.software_versions[2],
        ),
    )
    cls.devices[0].tags.set(Tag.objects.get_for_model(Device))
    cls.devices[1].tags.set(Tag.objects.get_for_model(Device)[:3])

    controller_statuses = iter(Status.objects.get_for_model(Controller))
    external_integrations = iter(ExternalIntegration.objects.all())
    device_redundancy_groups = iter(DeviceRedundancyGroup.objects.all())

    module_types = (
        ModuleType.objects.create(
            manufacturer=cls.manufacturers[0], model="Filter Test Module Type 1", comments="Module Type 1"
        ),
        ModuleType.objects.create(
            manufacturer=cls.manufacturers[1],
            model="Filter Test Module Type 2",
            comments="Module Type 2",
            module_family=cls.module_families[0],
        ),
        ModuleType.objects.create(
            manufacturer=cls.manufacturers[2],
            model="Filter Test Module Type 3",
            comments="Module Type 3",
            module_family=cls.module_families[1],
        ),
    )

    # Create 3 of each component template on the first two module types
    for i in range(6):
        ConsolePortTemplate.objects.create(
            name=f"Test Filters Module Console Port {i + 1}",
            module_type=module_types[i % 2],
        )
        ConsoleServerPortTemplate.objects.create(
            name=f"Test Filters Module Console Server Port {i + 1}",
            module_type=module_types[i % 2],
        )
        ppt = PowerPortTemplate.objects.create(
            name=f"Test Filters Module Power Port {i + 1}",
            module_type=module_types[i % 2],
        )
        PowerOutletTemplate.objects.create(
            name=f"Test Filters Module Power Outlet {i + 1}",
            power_port_template=ppt,
            module_type=module_types[i % 2],
        )
        InterfaceTemplate.objects.create(
            name=f"Test Filters Module Interface {i + 1}",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            module_type=module_types[i % 2],
        )
        rpt = RearPortTemplate.objects.create(
            name=f"Test Filters Module Rear Port {i + 1}",
            module_type=module_types[i % 2],
            type=PortTypeChoices.TYPE_8P8C,
            positions=10,
        )
        FrontPortTemplate.objects.create(
            name=f"Test Filters Module Front Port {i + 1}",
            module_type=module_types[i % 2],
            rear_port_template=rpt,
            rear_port_position=i + 1,
            type=PortTypeChoices.TYPE_8P8C,
        )
        ModuleBayTemplate.objects.create(
            name=f"Test Filters Module Module Bay {i + 1}",
            position=i + 1,
            module_type=module_types[i % 2],
            requires_first_party_modules=(i % 2 == 0),  # True for even indices, False for odd
        )

    module_roles = Role.objects.get_for_model(Module)
    cls.module_statuses = Status.objects.get_for_model(Module)
    cls.modules = (
        Module.objects.create(
            module_type=module_types[0],
            status=cls.module_statuses[0],
            asset_tag="Test Filter Asset Tag Module1",
            serial="Test Filter Serial Module1",
            role=module_roles[0],
            tenant=tenants[0],
            parent_module_bay=cls.devices[0].module_bays.first(),
        ),
        Module.objects.create(
            module_type=module_types[1],
            status=cls.module_statuses[0],
            asset_tag="Test Filter Asset Tag Module2",
            serial="Test Filter Serial Module2",
            role=module_roles[0],
            tenant=tenants[1],
            parent_module_bay=cls.devices[1].module_bays.first(),
        ),
        Module.objects.create(
            module_type=module_types[2],
            status=cls.module_statuses[0],
            asset_tag="Test Filter Asset Tag Module3",
            serial="Test Filter Serial Module3",
            role=module_roles[1],
            tenant=tenants[2],
            parent_module_bay=cls.devices[2].module_bays.first(),
        ),
    )
    cls.modules[0].tags.set(Tag.objects.get_for_model(Module))
    cls.modules[1].tags.set(Tag.objects.get_for_model(Module)[:3])

    Module.objects.create(
        module_type=module_types[0],
        status=cls.module_statuses[1],
        asset_tag="Test Filter Asset Tag Module4",
        serial="Test Filter Serial Module4",
        role=module_roles[1],
        tenant=tenants[0],
        parent_module_bay=cls.modules[0].module_bays.first(),
    )
    Module.objects.create(
        module_type=module_types[1],
        status=cls.module_statuses[1],
        asset_tag="Test Filter Asset Tag Module5",
        serial="Test Filter Serial Module5",
        tenant=tenants[1],
        parent_module_bay=cls.modules[1].module_bays.first(),
    )
    Module.objects.create(
        module_type=module_types[2],
        status=cls.module_statuses[1],
        asset_tag="Test Filter Asset Tag Module6",
        serial="Test Filter Serial Module6",
        tenant=tenants[2],
        parent_module_bay=cls.modules[1].module_bays.last(),
    )

    cls.controllers = (
        Controller.objects.create(
            name="Controller 1",
            status=next(controller_statuses),
            description="First",
            location=loc0,
            platform=platforms[0],
            role=cls.device_roles[0],
            tenant=tenants[0],
            external_integration=next(external_integrations),
            controller_device=cls.devices[0],
        ),
        Controller.objects.create(
            name="Controller 2",
            status=next(controller_statuses),
            description="Second",
            location=loc1,
            platform=platforms[1],
            role=cls.device_roles[1],
            tenant=tenants[1],
            external_integration=next(external_integrations),
            controller_device=cls.devices[1],
        ),
        Controller.objects.create(
            name="Controller 3",
            status=next(controller_statuses),
            description="Third",
            location=loc2,
            platform=platforms[2],
            role=cls.device_roles[2],
            tenant=tenants[2],
            external_integration=next(external_integrations),
            controller_device_redundancy_group=next(device_redundancy_groups),
        ),
        Controller.objects.create(
            name="Controller 4",
            status=next(controller_statuses),
            description="Forth",
            location=loc2,
            platform=platforms[2],
            role=cls.device_roles[2],
            tenant=tenants[2],
            external_integration=next(external_integrations),
            controller_device_redundancy_group=next(device_redundancy_groups),
        ),
    )
    cls.controllers[0].tags.set(Tag.objects.get_for_model(Controller))
    cls.controllers[1].tags.set(Tag.objects.get_for_model(Controller)[:3])

    parent_controller_managed_device_group = ControllerManagedDeviceGroup.objects.create(
        name="Managed Device Group 11",
        weight=1000,
        controller=cls.controllers[0],
    )
    cls.controller_managed_device_groups = (
        parent_controller_managed_device_group,
        ControllerManagedDeviceGroup.objects.create(
            name="Managed Device Group 12",
            weight=2000,
            controller=cls.controllers[1],
            parent=parent_controller_managed_device_group,
        ),
        ControllerManagedDeviceGroup.objects.create(
            name="Managed Device Group 13",
            weight=3000,
            controller=cls.controllers[2],
            parent=parent_controller_managed_device_group,
        ),
    )
    parent_controller_managed_device_group.tags.set(Tag.objects.get_for_model(ControllerManagedDeviceGroup))
    cls.controller_managed_device_groups[1].tags.set(Tag.objects.get_for_model(ControllerManagedDeviceGroup)[:3])


class ComponentTemplateTestMixin:
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


class ModularComponentTemplateTestMixin(ComponentTemplateTestMixin):
    generic_filter_tests = [
        *ComponentTemplateTestMixin.generic_filter_tests,
        ("module_type", "module_type__id"),
        ("module_type", "module_type__model"),
    ]


class DeviceComponentTestMixin:
    generic_filter_tests = [
        ("description",),
        ("device", "device__id"),
        ("device", "device__name"),
        ("label",),
        ("name",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)


class ModularDeviceComponentTestMixin(DeviceComponentTestMixin):
    generic_filter_tests = [
        ("description",),
        ("label",),
        ("name",),
        ("module", "module__id"),
        ("module", "module__module_type__model"),
    ]

    def test_device(self):
        """Test that the device filter returns all components for a device and its modules."""
        model = self.queryset.model._meta.model_name
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model=f"Test Device Filter for {model} Device Type"
        )
        device = Device.objects.create(
            device_type=device_type,
            name=f"Test Device Filter for {model} Device",
            location=self.loc0,
            role=self.device_roles[0],
            status=Status.objects.get_for_model(Device).first(),
        )
        parent_module_bay = ModuleBay.objects.create(name="Parent module bay", position="1", parent_device=device)
        module_type = ModuleType.objects.create(
            manufacturer=manufacturer, model=f"Test Device Filter for {model} Module Type", comments="Module Type test"
        )
        module = Module.objects.create(
            module_type=module_type, parent_module_bay=parent_module_bay, status=self.module_statuses[0]
        )
        child_module_bay = ModuleBay.objects.create(name="Child module bay", position="1", parent_module=module)
        child_module = Module.objects.create(
            module_type=module_type, parent_module_bay=child_module_bay, status=self.module_statuses[0]
        )
        top_level_component = self.queryset.create(device=device, name=f"Top level {model}")
        second_level_component = self.queryset.create(module=module, name=f"Second level {model}")
        third_level_component = self.queryset.create(module=child_module, name=f"Third level {model}")
        with self.subTest("device filter (pk)"):
            self.assertQuerySetEqual(
                self.filterset({"device": [device.pk]}, self.queryset).qs,
                [top_level_component, second_level_component, third_level_component],
                ordered=False,
            )
        with self.subTest("device filter (name)"):
            self.assertQuerySetEqual(
                self.filterset({"device": [device.name]}, self.queryset).qs,
                [top_level_component, second_level_component, third_level_component],
                ordered=False,
            )

        with self.subTest("device filter (pk) with an invalid uuid"):
            self.assertFalse(self.filterset({"device": [uuid.uuid4()]}, self.queryset).is_valid())


class ModuleDeviceCommonTestsMixin:
    def test_has_empty_module_bays(self):
        test_instances = self.queryset.all()[:2]
        ModuleBay.objects.create(
            **{
                f"parent_{self.queryset.model._meta.model_name}": test_instances[0],
                "name": "test filters position 1",
                "position": 1,
            }
        )
        ModuleBay.objects.create(
            **{
                f"parent_{self.queryset.model._meta.model_name}": test_instances[1],
                "name": "test filters position 1",
                "position": 1,
            }
        )
        with self.subTest():
            params = {"has_empty_module_bays": True}
            qs = self.filterset(params, self.queryset).qs
            self.assertGreater(qs.count(), 0)
            for instance in qs:
                self.assertTrue(instance.module_bays.filter(installed_module__isnull=True).exists())
        with self.subTest():
            params = {"has_empty_module_bays": False}
            qs = self.filterset(params, self.queryset).qs
            self.assertGreater(qs.count(), 0)
            for instance in qs:
                self.assertFalse(instance.module_bays.filter(installed_module__isnull=True).exists())

    def test_has_modules(self):
        with self.subTest():
            params = {"has_modules": True}
            qs = self.filterset(params, self.queryset).qs
            self.assertGreater(qs.count(), 0)
            for instance in qs:
                self.assertTrue(instance.module_bays.filter(installed_module__isnull=False).exists())
        with self.subTest():
            params = {"has_modules": False}
            qs = self.filterset(params, self.queryset).qs
            self.assertGreater(qs.count(), 0)
            for instance in qs:
                self.assertFalse(instance.module_bays.filter(installed_module__isnull=False).exists())


class PathEndpointModelTestMixin:
    def test_connected(self):
        with self.subTest():
            params = {"connected": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(_path__is_active=True),
            )
        with self.subTest():
            params = {"connected": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(Q(_path__isnull=True) | Q(_path__is_active=False)),
            )


class LocationTypeFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = LocationType.objects.all()
    filterset = LocationTypeFilterSet
    generic_filter_tests = [
        ("description",),
        ("name",),
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


class LocationFilterSetTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
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
        ("name",),
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
        ("status", "status__id"),
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


class RackGroupTestCase(FilterTestCases.FilterTestCase):
    queryset = RackGroup.objects.all()
    filterset = RackGroupFilterSet
    generic_filter_tests = [
        ("description",),
        ("name",),
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
        RackGroup.objects.create(
            name="Rack Group 5",
            location=cls.loc2,
            description="C",
        )
        RackGroup.objects.create(
            name="Rack Group 6",
            location=cls.loc2,
        )
        RackGroup.objects.create(
            name="Rack Group 7",
            location=cls.loc3,
            description="C",
        )
        RackGroup.objects.create(
            name="Rack Group 8",
            location=cls.loc3,
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

    def test_ancestors(self):
        with self.subTest():
            pk_list = []
            parent_locations = self.loc3.ancestors(include_self=True)
            pk_list.extend([v.pk for v in parent_locations])
            params = Q(location__pk__in=pk_list)
            expected_queryset = RackGroup.objects.filter(params)
            params = {"ancestors": [self.loc3.pk]}
            self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected_queryset)
        with self.subTest():
            pk_list = []
            parent_locations = self.loc2.ancestors(include_self=True)
            pk_list.extend([v.pk for v in parent_locations])
            params = Q(location__pk__in=pk_list)
            expected_queryset = RackGroup.objects.filter(params)
            params = {"ancestors": [self.loc2.pk]}
            self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected_queryset)


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
        ("role", "role__id"),
        ("serial",),
        ("status", "status__id"),
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
        cls.rack_role = Role.objects.get_for_model(Rack).first()

        Rack.objects.create(
            name="Rack 4",
            facility_id="rack-4",
            location=cls.loc1,
            rack_group=rack_group,
            tenant=tenant,
            status=cls.rack_statuses[0],
            role=cls.rack_role,
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

    def test_role_status_negation(self):
        """https://github.com/nautobot/nautobot/issues/6456"""
        self.assertIsInstance(self.filterset().filters["role"], RoleFilter)
        self.assertIsInstance(self.filterset().filters["role__n"], RoleFilter)
        with self.subTest("Negated role (id)"):
            params = {"role__n": [self.rack_role.pk]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, Rack.objects.exclude(role=self.rack_role)
            )
        with self.subTest("Negated role (name)"):
            params = {"role__n": [self.rack_role.name]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, Rack.objects.exclude(role=self.rack_role)
            )

        self.assertIsInstance(self.filterset().filters["status"], StatusFilter)
        self.assertIsInstance(self.filterset().filters["status__n"], StatusFilter)
        with self.subTest("Negated status (id)"):
            params = {"status__n": [self.rack_statuses[0].pk]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, Rack.objects.exclude(status=self.rack_statuses[0])
            )
        with self.subTest("Negated status (name)"):
            params = {"status__n": [self.rack_statuses[0].name]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, Rack.objects.exclude(status=self.rack_statuses[0])
            )


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


class ManufacturerTestCase(FilterTestCases.FilterTestCase):
    queryset = Manufacturer.objects.all()
    filterset = ManufacturerFilterSet
    generic_filter_tests = [
        ("description",),
        ("device_types", "device_types__id"),
        ("device_types", "device_types__model"),
        ("inventory_items", "inventory_items__id"),
        ("inventory_items", "inventory_items__name"),
        ("name",),
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


class DeviceFamilyTestCase(FilterTestCases.FilterTestCase):
    queryset = DeviceFamily.objects.all()
    filterset = DeviceFamilyFilterSet
    generic_filter_tests = [
        ("description",),
        ("device_types", "device_types__id"),
        ("device_types", "device_types__model"),
        ("name",),
    ]


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
        ("device_family", "device_family__id"),
        ("device_family", "device_family__name"),
        ("devices", "devices__id"),
        ("front_port_templates", "front_port_templates__id"),
        ("front_port_templates", "front_port_templates__name"),
        ("interface_templates", "interface_templates__id"),
        ("interface_templates", "interface_templates__name"),
        ("manufacturer", "manufacturer__id"),
        ("manufacturer", "manufacturer__name"),
        ("model",),
        ("module_bay_templates", "module_bay_templates__id"),
        ("part_number",),
        ("power_outlet_templates", "power_outlet_templates__id"),
        ("power_outlet_templates", "power_outlet_templates__name"),
        ("power_port_templates", "power_port_templates__id"),
        ("power_port_templates", "power_port_templates__name"),
        ("rear_port_templates", "rear_port_templates__id"),
        ("rear_port_templates", "rear_port_templates__name"),
        ("software_image_files", "software_image_files__id"),
        ("software_image_files", "software_image_files__image_file_name"),
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
                self.queryset.filter(query).distinct(),
            )
        with self.subTest():
            params = {"pass_through_ports": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(~query).distinct(),
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


class ConsolePortTemplateTestCase(ModularComponentTemplateTestMixin, FilterTestCases.FilterTestCase):
    queryset = ConsolePortTemplate.objects.all()
    filterset = ConsolePortTemplateFilterSet


class ConsoleServerPortTemplateTestCase(ModularComponentTemplateTestMixin, FilterTestCases.FilterTestCase):
    queryset = ConsoleServerPortTemplate.objects.all()
    filterset = ConsoleServerPortTemplateFilterSet


class PowerPortTemplateTestCase(ModularComponentTemplateTestMixin, FilterTestCases.FilterTestCase):
    queryset = PowerPortTemplate.objects.all()
    filterset = PowerPortTemplateFilterSet
    generic_filter_tests = [
        *ModularComponentTemplateTestMixin.generic_filter_tests,
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


class PowerOutletTemplateTestCase(ModularComponentTemplateTestMixin, FilterTestCases.FilterTestCase):
    queryset = PowerOutletTemplate.objects.all()
    filterset = PowerOutletTemplateFilterSet
    generic_filter_tests = [
        *ModularComponentTemplateTestMixin.generic_filter_tests,
        ("feed_leg",),
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


class InterfaceTemplateTestCase(ModularComponentTemplateTestMixin, FilterTestCases.FilterTestCase):
    queryset = InterfaceTemplate.objects.all()
    filterset = InterfaceTemplateFilterSet
    generic_filter_tests = [
        *ModularComponentTemplateTestMixin.generic_filter_tests,
        ("type",),
    ]

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


class FrontPortTemplateTestCase(ModularComponentTemplateTestMixin, FilterTestCases.FilterTestCase):
    queryset = FrontPortTemplate.objects.all()
    filterset = FrontPortTemplateFilterSet
    generic_filter_tests = [
        *ModularComponentTemplateTestMixin.generic_filter_tests,
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


class RearPortTemplateTestCase(ModularComponentTemplateTestMixin, FilterTestCases.FilterTestCase):
    queryset = RearPortTemplate.objects.all()
    filterset = RearPortTemplateFilterSet
    generic_filter_tests = [
        *ModularComponentTemplateTestMixin.generic_filter_tests,
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


class DeviceBayTemplateTestCase(ComponentTemplateTestMixin, FilterTestCases.FilterTestCase):
    queryset = DeviceBayTemplate.objects.all()
    filterset = DeviceBayTemplateFilterSet


class PlatformTestCase(FilterTestCases.FilterTestCase):
    queryset = Platform.objects.all()
    filterset = PlatformFilterSet
    generic_filter_tests = [
        ("description",),
        ("devices", "devices__id"),
        ("manufacturer", "manufacturer__id"),
        ("manufacturer", "manufacturer__name"),
        ("name",),
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
        devices = Device.objects.filter(platform__isnull=False)[:2]
        params = {"devices": [devices[0].pk, devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(devices))

    def test_virtual_machines(self):
        virtual_machines = [VirtualMachine.objects.first(), VirtualMachine.objects.last()]
        params = {"virtual_machines": [virtual_machines[0].pk, virtual_machines[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(virtual_machines))


class DeviceTestCase(
    ModuleDeviceCommonTestsMixin,
    FilterTestCases.FilterTestCase,
    FilterTestCases.TenancyFilterTestCaseMixin,
):
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
        ("device_family", "device_type__device_family__id"),
        ("device_family", "device_type__device_family__name"),
        ("device_redundancy_group", "device_redundancy_group__id"),
        ("device_redundancy_group", "device_redundancy_group__name"),
        ("device_redundancy_group_priority",),
        ("controller_managed_device_group", "controller_managed_device_group__id"),
        ("controller_managed_device_group", "controller_managed_device_group__name"),
        ("device_type", "device_type__id"),
        ("device_type", "device_type__model"),
        ("front_ports", "front_ports__id"),
        ("interfaces", "interfaces__id"),
        ("interfaces", "interfaces__name"),
        ("ip_addresses", "interfaces__ip_addresses__id"),
        ("mac_address", "interfaces__mac_address"),
        ("manufacturer", "device_type__manufacturer__id"),
        ("manufacturer", "device_type__manufacturer__name"),
        ("module_bays", "module_bays__id"),
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
        ("radio_profiles", "controller_managed_device_group__radio_profiles__id"),
        ("radio_profiles", "controller_managed_device_group__radio_profiles__name"),
        ("rear_ports", "rear_ports__id"),
        ("role", "role__id"),
        ("role", "role__name"),
        ("secrets_group", "secrets_group__id"),
        ("secrets_group", "secrets_group__name"),
        ("software_image_files", "software_image_files__id"),
        ("software_image_files", "software_image_files__image_file_name"),
        ("software_version", "software_version__id"),
        ("software_version", "software_version__version"),
        ("status", "status__id"),
        ("status", "status__name"),
        ("vc_position",),
        ("vc_priority",),
        ("virtual_chassis", "virtual_chassis__id"),
        ("virtual_chassis", "virtual_chassis__name"),
        ("wireless_networks", "controller_managed_device_group__wireless_networks__id"),
        ("wireless_networks", "controller_managed_device_group__wireless_networks__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        devices = Device.objects.all()

        device_types_with_software_image_files = DeviceType.objects.filter(
            software_image_files__isnull=False, devices__isnull=False
        ).distinct()[:2]
        for device_type in device_types_with_software_image_files:
            device = device_type.devices.first()
            device.software_image_files.set([device_type.software_image_files.first()])

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
        InventoryItem.objects.create(device=devices[0], name="Inventory Item 1", serial="abc")
        InventoryItem.objects.create(device=devices[1], name="Inventory Item 2", serial="xyz")
        Service.objects.create(device=devices[0], name="ssh", protocol="tcp", ports=[22])
        Service.objects.create(device=devices[1], name="dns", protocol="udp", ports=[53])

        cls.controller_managed_device_groups = list(ControllerManagedDeviceGroup.objects.all()[:2])
        cls.controller_managed_device_groups[0].radio_profiles.set(RadioProfile.objects.all()[:2])
        cls.controller_managed_device_groups[0].wireless_networks.set(
            WirelessNetwork.objects.filter(controller_managed_device_groups__isnull=True)[:2]
        )
        cls.controller_managed_device_groups[1].radio_profiles.set(RadioProfile.objects.all()[2:4])
        cls.controller_managed_device_groups[1].wireless_networks.set(
            WirelessNetwork.objects.filter(controller_managed_device_groups__isnull=True)[2:4]
        )
        cls.device_redundancy_groups = list(DeviceRedundancyGroup.objects.all()[:2])
        Device.objects.filter(pk=devices[0].pk).update(
            controller_managed_device_group=cls.controller_managed_device_groups[0],
            device_redundancy_group=cls.device_redundancy_groups[0],
        )
        Device.objects.filter(pk=devices[1].pk).update(
            controller_managed_device_group=cls.controller_managed_device_groups[0],
            device_redundancy_group=cls.device_redundancy_groups[0],
            device_redundancy_group_priority=1,
        )
        Device.objects.filter(pk=devices[2].pk).update(
            controller_managed_device_group=cls.controller_managed_device_groups[1],
            device_redundancy_group=cls.device_redundancy_groups[1],
            device_redundancy_group_priority=100,
        )

        # Assign primary IPs for filtering
        interfaces = Interface.objects.filter(device__isnull=False)
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

    def test_ip_addresses(self):
        addresses = list(IPAddress.objects.filter(interfaces__isnull=False)[:2])
        params = {"ip_addresses": [addresses[0].address, addresses[1].id]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(interfaces__ip_addresses__in=addresses).distinct(),
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


class ConsolePortTestCase(PathEndpointModelTestMixin, ModularDeviceComponentTestMixin, FilterTestCases.FilterTestCase):
    queryset = ConsolePort.objects.all()
    filterset = ConsolePortFilterSet
    generic_filter_tests = [
        *ModularDeviceComponentTestMixin.generic_filter_tests,
        ("cable", "cable__id"),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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


class ConsoleServerPortTestCase(
    PathEndpointModelTestMixin, ModularDeviceComponentTestMixin, FilterTestCases.FilterTestCase
):
    queryset = ConsoleServerPort.objects.all()
    filterset = ConsoleServerPortFilterSet
    generic_filter_tests = [
        *ModularDeviceComponentTestMixin.generic_filter_tests,
        ("cable", "cable__id"),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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


class PowerPortTestCase(PathEndpointModelTestMixin, ModularDeviceComponentTestMixin, FilterTestCases.FilterTestCase):
    queryset = PowerPort.objects.all()
    filterset = PowerPortFilterSet
    generic_filter_tests = [
        *ModularDeviceComponentTestMixin.generic_filter_tests,
        ("allocated_draw",),
        ("cable", "cable__id"),
        ("maximum_draw",),
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


class PowerOutletTestCase(PathEndpointModelTestMixin, ModularDeviceComponentTestMixin, FilterTestCases.FilterTestCase):
    queryset = PowerOutlet.objects.all()
    filterset = PowerOutletFilterSet
    generic_filter_tests = [
        *ModularDeviceComponentTestMixin.generic_filter_tests,
        ("cable", "cable__id"),
        ("feed_leg",),
        ("power_port", "power_port__id"),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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


class InterfaceTestCase(PathEndpointModelTestMixin, ModularDeviceComponentTestMixin, FilterTestCases.FilterTestCase):
    queryset = Interface.objects.all()
    filterset = InterfaceFilterSet
    generic_filter_tests = [
        # parent class generic_filter_tests intentionally excluded
        ("bridge", "bridge__id"),
        ("bridge", "bridge__name"),
        ("bridged_interfaces", "bridged_interfaces__id"),
        ("bridged_interfaces", "bridged_interfaces__name"),
        ("cable", "cable__id"),
        ("child_interfaces", "child_interfaces__id"),
        ("child_interfaces", "child_interfaces__name"),
        ("description",),
        # ("device", "device__id"),  # TODO - InterfaceFilterSet overrides device as a MultiValueCharFilter on name only
        ("ip_addresses", "ip_addresses__id"),
        ("label",),
        ("lag", "lag__id"),
        ("lag", "lag__name"),
        ("mac_address",),
        ("member_interfaces", "member_interfaces__id"),
        ("member_interfaces", "member_interfaces__name"),
        ("module", "module__id"),
        ("module", "module__module_type__model"),
        ("mtu",),
        ("name",),
        ("parent_interface", "parent_interface__id"),
        ("parent_interface", "parent_interface__name"),
        ("role", "role__id"),
        ("role", "role__name"),
        ("status", "status__id"),
        ("status", "status__name"),
        ("type",),
        ("tagged_vlans", "tagged_vlans__id"),
        ("tagged_vlans", "tagged_vlans__vid"),
        ("untagged_vlan", "untagged_vlan__id"),
        ("untagged_vlan", "untagged_vlan__vid"),
        ("virtual_device_contexts", "virtual_device_contexts__id"),
        ("virtual_device_contexts", "virtual_device_contexts__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )
        vlans = VLAN.objects.all()[:3]

        interface_statuses = Status.objects.get_for_model(Interface)
        interface_roles = Role.objects.get_for_model(Interface)

        # Cabled interfaces
        cabled_interfaces = (
            Interface.objects.get(name="Test Interface 1"),
            Interface.objects.get(name="Test Interface 2"),
            Interface.objects.get(name="Test Interface 3"),
            Interface.objects.create(
                device=devices[2],
                name="Parent Interface 1",
                role=interface_roles[0],
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
                role=interface_roles[1],
                type=InterfaceTypeChoices.TYPE_OTHER,
                mode=InterfaceModeChoices.MODE_TAGGED,
                enabled=False,
                mgmt_only=True,
                status=interface_statuses[0],
            ),
        )
        interface_taggable_vlan_1 = VLAN.objects.filter(locations__in=[devices[2].location]).first()
        interface_taggable_vlan_2 = VLAN.objects.filter(locations__in=[devices[2].location]).last()

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
            role=interface_roles[2],
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
            role=interface_roles[0],
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
                role=interface_roles[1],
                status=interface_statuses[3],
                type=InterfaceTypeChoices.TYPE_BRIDGE,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Bridge 3",
                role=interface_roles[2],
                status=interface_statuses[3],
                type=InterfaceTypeChoices.TYPE_BRIDGE,
            ),
        )
        Interface.objects.create(
            device=bridge_interfaces[0].device,
            name="Bridged 1",
            role=interface_roles[0],
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
            role=interface_roles[1],
            bridge=bridge_interfaces[2],
            status=interface_statuses[3],
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
        )

        # LAG interfaces
        lag_interfaces = (
            Interface.objects.create(
                device=devices[2],
                name="LAG 1",
                role=interface_roles[0],
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
                role=interface_roles[1],
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
            role=interface_roles[2],
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

        cabled_interfaces[0].add_ip_addresses([ipaddresses[0], ipaddresses[2]])
        cabled_interfaces[1].add_ip_addresses([ipaddresses[1], ipaddresses[3]])
        # Virtual Device Context
        vdc_status = Status.objects.get_for_model(VirtualDeviceContext).first()
        vdcs = [
            VirtualDeviceContext.objects.create(
                device=devices[2], status=vdc_status, identifier=200 + idx, name=f"Test VDC {idx}"
            )
            for idx in range(3)
        ]
        vdcs[0].interfaces.set(lag_interfaces)
        vdcs[1].interfaces.set(lag_interfaces)
        vdcs[2].interfaces.set(lag_interfaces)

    def test_enabled(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"enabled": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(**params),
            )
        with self.subTest():
            params = {"enabled": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(**params),
            )

    def test_mgmt_only(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"mgmt_only": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(**params),
            )
        with self.subTest():
            params = {"mgmt_only": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(**params),
            )

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

    def test_device(self):
        """
        Test that the device filter returns all components for a device and its
        modules, including virtual chassis member devices and their modules.
        """
        status = Status.objects.get_for_model(Interface).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="Test Device Filter for Interface Device Type"
        )
        device_vc_master = Device.objects.create(
            device_type=device_type,
            name="Test Device Filter for Interface Device VC Master",
            location=self.loc0,
            role=self.device_roles[0],
            status=Status.objects.get_for_model(Device).first(),
        )
        vc = VirtualChassis.objects.create(
            name="Test Device Filter for Interface Virtual Chassis", master=device_vc_master
        )
        device_vc_master.virtual_chassis = vc
        device_vc_master.save()
        parent_module_bay = ModuleBay.objects.create(
            name="Parent module bay", position="1", parent_device=device_vc_master
        )
        module_type = ModuleType.objects.create(
            manufacturer=manufacturer, model="Test Device Filter for Interface Module Type", comments="Module Type test"
        )
        module = Module.objects.create(
            module_type=module_type, parent_module_bay=parent_module_bay, status=self.module_statuses[0]
        )
        child_module_bay = ModuleBay.objects.create(name="Child module bay", position="1", parent_module=module)
        child_module = Module.objects.create(
            module_type=module_type, parent_module_bay=child_module_bay, status=self.module_statuses[0]
        )
        top_level_interface = self.queryset.create(
            device=device_vc_master,
            name="Top level Interface VC Master",
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=status,
        )
        second_level_interface = self.queryset.create(
            module=module,
            name="Second level Interface VC Master",
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=status,
        )
        third_level_interface = self.queryset.create(
            module=child_module,
            name="Third level Interface VC Master",
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=status,
        )
        device_vc_member = Device.objects.create(
            device_type=device_type,
            name="Test Device Filter for Interface Device VC Member",
            location=self.loc0,
            role=self.device_roles[0],
            status=Status.objects.get_for_model(Device).first(),
            virtual_chassis=vc,
        )
        parent_module_bay_vc_member = ModuleBay.objects.create(
            name="Parent module bay", position="1", parent_device=device_vc_member
        )
        module_vc_member = Module.objects.create(
            module_type=module_type, parent_module_bay=parent_module_bay_vc_member, status=self.module_statuses[0]
        )
        child_module_bay_vc_member = ModuleBay.objects.create(
            name="Child module bay", position="1", parent_module=module_vc_member
        )
        child_module_vc_member = Module.objects.create(
            module_type=module_type, parent_module_bay=child_module_bay_vc_member, status=self.module_statuses[0]
        )
        top_level_interface_vc_member = self.queryset.create(
            device=device_vc_member,
            name="Top level Interface VC Member",
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=status,
        )
        second_level_interface_vc_member = self.queryset.create(
            module=module_vc_member,
            name="Second level Interface VC Member",
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=status,
        )
        third_level_interface_vc_member = self.queryset.create(
            module=child_module_vc_member,
            name="Third level Interface VC Member",
            type=InterfaceTypeChoices.TYPE_1GE_SFP,
            status=status,
        )

        with self.subTest("device filter on pk"):
            self.assertQuerySetEqual(
                self.filterset({"device": [device_vc_master.pk]}, self.queryset).qs,
                [
                    top_level_interface,
                    second_level_interface,
                    third_level_interface,
                    top_level_interface_vc_member,
                    second_level_interface_vc_member,
                    third_level_interface_vc_member,
                ],
                ordered=False,
            )

        with self.subTest("device filter on name"):
            self.assertQuerySetEqual(
                self.filterset({"device": [device_vc_master.name]}, self.queryset).qs,
                [
                    top_level_interface,
                    second_level_interface,
                    third_level_interface,
                    top_level_interface_vc_member,
                    second_level_interface_vc_member,
                    third_level_interface_vc_member,
                ],
                ordered=False,
            )

        with self.subTest("device_id filter"):
            self.assertQuerySetEqual(
                self.filterset({"device_id": [device_vc_master.pk]}, self.queryset).qs,
                [
                    top_level_interface,
                    second_level_interface,
                    third_level_interface,
                    top_level_interface_vc_member,
                    second_level_interface_vc_member,
                    third_level_interface_vc_member,
                ],
                ordered=False,
            )

        with self.subTest("device_id filter with an invalid uuid"):
            self.assertFalse(self.filterset({"device_id": [uuid.uuid4()]}, self.queryset).is_valid())

        with self.subTest("device (pk) filter with an invalid uuid"):
            self.assertFalse(self.filterset({"device": [uuid.uuid4()]}, self.queryset).is_valid())

    def test_ip_addresses(self):
        addresses = list(IPAddress.objects.filter(interfaces__isnull=False)[:2])
        params = {"ip_addresses": [addresses[0].address, addresses[1].id]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(ip_addresses__in=addresses).distinct(),
        )

    def test_kind(self):
        # TODO: Not a generic_filter_test because this is a single-value filter
        # 2.0 TODO: Support filtering for multiple values
        with self.subTest():
            params = {"kind": "physical"}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.exclude(type__in=NONCONNECTABLE_IFACE_TYPES),
            )
        with self.subTest():
            params = {"kind": "virtual"}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(type__in=VIRTUAL_IFACE_TYPES),
            )

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


class FrontPortTestCase(ModularDeviceComponentTestMixin, FilterTestCases.FilterTestCase):
    queryset = FrontPort.objects.all()
    filterset = FrontPortFilterSet
    generic_filter_tests = [
        *ModularDeviceComponentTestMixin.generic_filter_tests,
        ("cable", "cable__id"),
        ("rear_port", "rear_port__id"),
        ("rear_port", "rear_port__name"),
        ("rear_port_position",),
        ("type",),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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

    def test_device(self):
        """Test that the device filter returns all components for a device and its modules."""
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="Test Device Filter for FrontPort Device Type"
        )
        device = Device.objects.create(
            device_type=device_type,
            name="Test Device Filter for FrontPort Device",
            location=self.loc0,
            role=self.device_roles[0],
            status=Status.objects.get_for_model(Device).first(),
        )
        parent_module_bay = ModuleBay.objects.create(name="Parent module bay", position="1", parent_device=device)
        module_type = ModuleType.objects.create(
            manufacturer=manufacturer, model="Test Device Filter for FrontPort Module Type", comments="Module Type test"
        )
        module = Module.objects.create(
            module_type=module_type, parent_module_bay=parent_module_bay, status=self.module_statuses[0]
        )
        child_module_bay = ModuleBay.objects.create(name="Child module bay", position="1", parent_module=module)
        child_module = Module.objects.create(
            module_type=module_type, parent_module_bay=child_module_bay, status=self.module_statuses[0]
        )
        top_level_rearport = RearPort.objects.create(
            device=device,
            name="Top level Rear Port",
            type=PortTypeChoices.TYPE_8P8C,
            positions=6,
        )
        second_level_rearport = RearPort.objects.create(
            module=module,
            name="Second level Rear Port",
            type=PortTypeChoices.TYPE_8P8C,
            positions=6,
        )
        third_level_rearport = RearPort.objects.create(
            module=child_module,
            name="Third level Rear Port",
            type=PortTypeChoices.TYPE_8P8C,
            positions=6,
        )
        top_level_frontport = self.queryset.create(
            device=device,
            name="Top level Front Port",
            rear_port=top_level_rearport,
            rear_port_position=1,
        )
        second_level_frontport = self.queryset.create(
            module=module,
            name="Second level Front Port",
            rear_port=second_level_rearport,
            rear_port_position=1,
        )
        third_level_frontport = self.queryset.create(
            module=child_module,
            name="Third level Front Port",
            rear_port=third_level_rearport,
            rear_port_position=1,
        )
        self.assertQuerySetEqual(
            self.filterset({"device": [device.pk]}, self.queryset).qs,
            [top_level_frontport, second_level_frontport, third_level_frontport],
            ordered=False,
        )
        self.assertQuerySetEqual(
            self.filterset({"device": [device.name]}, self.queryset).qs,
            [top_level_frontport, second_level_frontport, third_level_frontport],
            ordered=False,
        )


class RearPortTestCase(ModularDeviceComponentTestMixin, FilterTestCases.FilterTestCase):
    queryset = RearPort.objects.all()
    filterset = RearPortFilterSet
    generic_filter_tests = [
        *ModularDeviceComponentTestMixin.generic_filter_tests,
        ("cable", "cable__id"),
        ("front_ports", "front_ports__id"),
        ("front_ports", "front_ports__name"),
        ("positions",),
        ("type",),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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


class DeviceBayTestCase(DeviceComponentTestMixin, FilterTestCases.FilterTestCase):
    queryset = DeviceBay.objects.all()
    filterset = DeviceBayFilterSet
    generic_filter_tests = [
        *DeviceComponentTestMixin.generic_filter_tests,
        ("installed_device", "installed_device__id"),
        ("installed_device", "installed_device__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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


class InventoryItemTestCase(DeviceComponentTestMixin, FilterTestCases.FilterTestCase):
    queryset = InventoryItem.objects.all()
    filterset = InventoryItemFilterSet
    generic_filter_tests = [
        *DeviceComponentTestMixin.generic_filter_tests,
        ("asset_tag",),
        ("children", "children__id"),
        ("manufacturer", "manufacturer__id"),
        ("manufacturer", "manufacturer__name"),
        ("parent", "parent__id"),
        ("parent", "parent__name"),
        ("part_id",),
        ("software_image_files", "software_image_files__id"),
        ("software_image_files", "software_image_files__image_file_name"),
        ("software_version", "software_version__id"),
        ("software_version", "software_version__version"),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        devices = (
            Device.objects.get(name="Device 1"),
            Device.objects.get(name="Device 2"),
            Device.objects.get(name="Device 3"),
        )

        software_versions = SoftwareVersion.objects.filter(software_image_files__isnull=False).distinct()[:3]

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
                software_version=software_versions[0],
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
                software_version=software_versions[1],
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
                software_version=software_versions[2],
            ),
        )
        inventory_items[0].tags.set(Tag.objects.get_for_model(InventoryItem))
        inventory_items[1].tags.set(Tag.objects.get_for_model(InventoryItem)[:3])
        inventory_items[0].software_image_files.set(software_versions[1].software_image_files.all())
        inventory_items[1].software_image_files.set(software_versions[0].software_image_files.all())

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


class CableTestCase(FilterTestCases.FilterTestCase):
    queryset = Cable.objects.all()
    filterset = CableFilterSet
    generic_filter_tests = [
        ("color",),
        ("label",),
        ("length",),
        ("status", "status__id"),
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
                name="Test Interface 7",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Test Interface 8",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Test Interface 9",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[3],
                name="Test Interface 10",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[4],
                name="Test Interface 11",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[5],
                name="Test Interface 12",
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
        """Test that the device filter returns all cables for a device and its modules."""
        interfaces = list(Interface.objects.filter(cable__isnull=True)[:3])
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="Test Device Filter for Cable Device Type"
        )
        device = Device.objects.create(
            device_type=device_type,
            name="Test Device Filter for Cable Device",
            location=self.loc0,
            role=self.device_roles[0],
            status=Status.objects.get_for_model(Device).first(),
        )
        parent_module_bay = ModuleBay.objects.create(name="Parent module bay", position="1", parent_device=device)
        module_type = ModuleType.objects.create(
            manufacturer=manufacturer, model="Test Device Filter for Cable Module Type", comments="Module Type test"
        )
        module = Module.objects.create(
            module_type=module_type, parent_module_bay=parent_module_bay, status=self.module_statuses[0]
        )
        child_module_bay = ModuleBay.objects.create(name="Child module bay", position="1", parent_module=module)
        child_module = Module.objects.create(
            module_type=module_type, parent_module_bay=child_module_bay, status=self.module_statuses[0]
        )
        interface_status = Status.objects.get_for_model(Interface).first()
        top_level_interface = Interface.objects.create(
            device=device,
            name="Top level Interface",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=interface_status,
        )
        Interface.objects.create(
            module=module,
            name="Second level Interface",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=interface_status,
        )
        third_level_interface = Interface.objects.create(
            module=child_module,
            name="Third level Interface",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=interface_status,
        )

        top_level_cable = Cable.objects.create(
            termination_a=top_level_interface,
            termination_b=interfaces[0],
            label="Test Device Filter Cable 1",
            type=CableTypeChoices.TYPE_CAT5E,
            status=self.status_connected,
            color="f44336",
            length=30,
            length_unit=CableLengthUnitChoices.UNIT_FOOT,
        )
        third_level_cable = Cable.objects.create(
            termination_a=interfaces[1],
            termination_b=third_level_interface,
            label="Test Device Filter Cable 2",
            type=CableTypeChoices.TYPE_CAT5E,
            status=self.status_connected,
            color="f44336",
            length=30,
            length_unit=CableLengthUnitChoices.UNIT_FOOT,
        )

        with self.subTest("device_id filter"):
            self.assertQuerySetEqual(
                self.filterset({"device_id": [device.pk]}, self.queryset).qs,
                [top_level_cable, third_level_cable],
                ordered=False,
            )

        with self.subTest("device filter"):
            self.assertQuerySetEqual(
                self.filterset({"device": [device.name]}, self.queryset).qs,
                [top_level_cable, third_level_cable],
                ordered=False,
            )

        with self.subTest("device_id filter with an invalid uuid"):
            self.assertFalse(self.filterset({"device_id": [uuid.uuid4()]}, self.queryset).is_valid())

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


class PowerFeedTestCase(PathEndpointModelTestMixin, FilterTestCases.FilterTestCase):
    queryset = PowerFeed.objects.all()
    filterset = PowerFeedFilterSet
    generic_filter_tests = [
        ("amperage",),
        ("available_power",),
        ("breaker_pole_count",),
        ("breaker_position",),
        ("cable", "cable__id"),
        ("comments",),
        ("destination_panel", "destination_panel__id"),
        ("destination_panel", "destination_panel__name"),
        ("max_utilization",),
        ("name",),
        ("power_panel", "power_panel__id"),
        ("power_panel", "power_panel__name"),
        ("rack", "rack__id"),
        ("rack", "rack__name"),
        ("status", "status__id"),
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
            PowerFeed.objects.get(name="Power Feed 4"),
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
            power_path=PowerPathChoices.PATH_A,
            breaker_position=1,
            breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_1,
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
            power_path=PowerPathChoices.PATH_B,
            breaker_position=4,
            breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_2,
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
            power_path=PowerPathChoices.PATH_A,
            breaker_position=9,
            breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_3,
        )
        PowerFeed.objects.filter(pk=power_feeds[3].pk).update(
            status=pf_statuses[0],
            type=PowerFeedTypeChoices.TYPE_REDUNDANT,
            supply=PowerFeedSupplyChoices.SUPPLY_AC,
            phase=PowerFeedPhaseChoices.PHASE_3PHASE,
            voltage=400,
            amperage=400,
            max_utilization=40,
            comments="PFD",
            power_path=PowerPathChoices.PATH_B,
            breaker_position=15,
            breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_2,
        )

        power_feeds[0].refresh_from_db()
        power_feeds[1].refresh_from_db()
        power_feeds[2].refresh_from_db()
        power_feeds[3].refresh_from_db()
        power_feeds[0].validated_save()
        power_feeds[1].validated_save()
        power_feeds[2].validated_save()
        power_feeds[3].validated_save()

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
        # TODO: Not a generic_filter_test because this field only has 2 valid choices
        params = {"type": [PowerFeedTypeChoices.TYPE_PRIMARY]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(type=PowerFeedTypeChoices.TYPE_PRIMARY),
        )

    def test_supply(self):
        # TODO: Not a generic_filter_test because this field only has 2 valid choices
        params = {"supply": [PowerFeedSupplyChoices.SUPPLY_AC]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(supply=PowerFeedSupplyChoices.SUPPLY_AC),
        )

    def test_phase(self):
        # TODO: Not a generic_filter_test because this field only has 2 valid choices
        params = {"phase": [PowerFeedPhaseChoices.PHASE_3PHASE]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(phase=PowerFeedPhaseChoices.PHASE_3PHASE),
        )

    def test_power_path(self):
        params = {"power_path": [PowerPathChoices.PATH_A]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(power_path=PowerPathChoices.PATH_A),
        )


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
        cls.interfaces = Interface.objects.all()[:8]

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

        for i, group in enumerate(interface_redundancy_groups):
            group.add_interface(cls.interfaces[i], 100 * i)
            group.add_interface(cls.interfaces[i + 4], 100 * (i + 4))


class SoftwareImageFileFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = SoftwareImageFile.objects.all()
    filterset = SoftwareImageFileFilterSet
    generic_filter_tests = (
        ["device_types", "device_types__id"],
        ["device_types", "device_types__model"],
        ["devices", "devices__id"],
        ["devices", "devices__name"],
        ["hashing_algorithm"],
        ["image_file_checksum"],
        ["image_file_name"],
        ["image_file_size"],
        ["software_version", "software_version__id"],
        ["software_version", "software_version__version"],
        ["status", "status__id"],
        ["status", "status__name"],
        ["external_integration", "external_integration__id"],
        ["external_integration", "external_integration__name"],
    )

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        device0, device1 = cls.devices[:2]
        device0.software_image_files.set(SoftwareImageFile.objects.all()[:2])
        device1.software_image_files.set(SoftwareImageFile.objects.all()[2:4])

        virtual_machine0, virtual_machine1 = VirtualMachine.objects.all()[:2]
        virtual_machine0.software_image_file = SoftwareImageFile.objects.first()
        virtual_machine0.save()
        virtual_machine1.software_image_file = SoftwareImageFile.objects.last()
        virtual_machine1.save()

    def test_default_image(self):
        params = {"default_image": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, SoftwareImageFile.objects.filter(default_image=True)
        )
        params = {"default_image": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, SoftwareImageFile.objects.filter(default_image=False)
        )


class SoftwareVersionFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = SoftwareVersion.objects.all()
    filterset = SoftwareVersionFilterSet
    generic_filter_tests = (
        ["alias"],
        ["devices", "devices__id"],
        ["devices", "devices__name"],
        ["documentation_url"],
        ["end_of_support_date"],
        ["platform", "platform__id"],
        ["platform", "platform__name"],
        ["release_date"],
        ["software_image_files", "software_image_files__id"],
        ["software_image_files", "software_image_files__image_file_name"],
        ["status", "status__id"],
        ["status", "status__name"],
        ["version"],
    )

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        InventoryItem.objects.create(
            device=cls.devices[0],
            name="Inventory Item 1",
            manufacturer=cls.manufacturers[0],
            software_version=cls.software_versions[0],
        )
        InventoryItem.objects.create(
            device=cls.devices[1],
            name="Inventory Item 2",
            manufacturer=cls.manufacturers[1],
            software_version=cls.software_versions[1],
        )
        InventoryItem.objects.create(
            device=cls.devices[2],
            name="Inventory Item 3",
            manufacturer=cls.manufacturers[2],
            software_version=cls.software_versions[2],
        )

    def test_long_term_support(self):
        params = {"long_term_support": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            SoftwareVersion.objects.filter(long_term_support=True),
        )
        params = {"long_term_support": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            SoftwareVersion.objects.filter(long_term_support=False),
        )

    def test_pre_release(self):
        params = {"pre_release": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            SoftwareVersion.objects.filter(pre_release=True),
        )
        params = {"pre_release": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            SoftwareVersion.objects.filter(pre_release=False),
        )


class DeviceTypeToSoftwareImageFileFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = DeviceTypeToSoftwareImageFile.objects.all()
    filterset = DeviceTypeToSoftwareImageFileFilterSet
    generic_filter_tests = (
        ["software_image_file", "software_image_file__id"],
        ["software_image_file", "software_image_file__image_file_name"],
        ["device_type", "device_type__id"],
        ["device_type", "device_type__model"],
    )


class ControllerFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = Controller.objects.all()
    filterset = ControllerFilterSet
    generic_filter_tests = (
        ("name",),
        ("description",),
        ("platform", "platform__id"),
        ("platform", "platform__name"),
        ("external_integration", "external_integration__id"),
        ("external_integration", "external_integration__name"),
        ("controller_device", "controller_device__id"),
        ("controller_device", "controller_device__name"),
        ("controller_device_redundancy_group", "controller_device_redundancy_group__id"),
        ("controller_device_redundancy_group", "controller_device_redundancy_group__name"),
        ("wireless_networks", "controller_managed_device_groups__wireless_networks__id"),
        ("wireless_networks", "controller_managed_device_groups__wireless_networks__name"),
    )

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)


class ControllerManagedDeviceGroupFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = ControllerManagedDeviceGroup.objects.all()
    filterset = ControllerManagedDeviceGroupFilterSet
    generic_filter_tests = (
        ("name",),
        ("weight",),
        ("controller", "controller__id"),
        ("controller", "controller__name"),
        ("parent", "parent__id"),
        ("parent", "parent__name"),
    )

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)


class ModuleTestCase(
    ModuleDeviceCommonTestsMixin,
    FilterTestCases.TenancyFilterTestCaseMixin,
    FilterTestCases.FilterTestCase,
):
    queryset = Module.objects.all()
    filterset = ModuleFilterSet
    tenancy_related_name = "modules"
    generic_filter_tests = [
        ("asset_tag",),
        ("console_ports", "console_ports__id"),
        ("console_ports", "console_ports__name"),
        ("console_server_ports", "console_server_ports__id"),
        ("console_server_ports", "console_server_ports__name"),
        ("front_ports", "front_ports__id"),
        ("front_ports", "front_ports__name"),
        ("interfaces", "interfaces__id"),
        ("interfaces", "interfaces__name"),
        ("mac_address", "interfaces__mac_address"),
        ("manufacturer", "module_type__manufacturer__id"),
        ("manufacturer", "module_type__manufacturer__name"),
        ("module_bays", "module_bays__id"),
        ("module_type", "module_type__id"),
        ("module_type", "module_type__model"),
        ("parent_module_bay", "parent_module_bay__id"),
        ("power_outlets", "power_outlets__id"),
        ("power_outlets", "power_outlets__name"),
        ("power_ports", "power_ports__id"),
        ("power_ports", "power_ports__name"),
        ("rear_ports", "rear_ports__id"),
        ("rear_ports", "rear_ports__name"),
        ("role", "role__id"),
        ("role", "role__name"),
        ("serial",),
        ("status", "status__id"),
        ("status", "status__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

        # Update existing interface objects with mac addresses for filtering
        interfaces = Interface.objects.filter(module__isnull=False)[:3]
        Interface.objects.filter(pk=interfaces[0].pk).update(mac_address="00-00-00-00-00-01")
        Interface.objects.filter(pk=interfaces[1].pk).update(mac_address="00-00-00-00-00-02")

    def test_compatible_with_module_bay(self):
        """Test filtering modules that are compatible with a specific module bay based on module family."""
        module_bay = ModuleBay.objects.filter(module_family__isnull=False).first()
        compatible_modules = Module.objects.filter(module_type__module_family=module_bay.module_family)
        params = {"compatible_with_module_bay": module_bay.pk}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params).qs, compatible_modules)

        # Test with module bay that has no module family - should return ALL modules
        module_bay_no_family = ModuleBay.objects.filter(module_family__isnull=True).first()
        params = {"compatible_with_module_bay": module_bay_no_family.pk}
        self.assertQuerysetEqual(self.filterset(params).qs, self.queryset, ordered=False)


class ModuleTypeTestCase(FilterTestCases.FilterTestCase):
    queryset = ModuleType.objects.all()
    filterset = ModuleTypeFilterSet
    generic_filter_tests = [
        ("comments",),
        ("manufacturer", "manufacturer__id"),
        ("manufacturer", "manufacturer__name"),
        ("model",),
        ("part_number",),
        ("console_port_templates", "console_port_templates__id"),
        ("console_port_templates", "console_port_templates__name"),
        ("console_server_port_templates", "console_server_port_templates__id"),
        ("console_server_port_templates", "console_server_port_templates__name"),
        ("power_port_templates", "power_port_templates__id"),
        ("power_port_templates", "power_port_templates__name"),
        ("power_outlet_templates", "power_outlet_templates__id"),
        ("power_outlet_templates", "power_outlet_templates__name"),
        ("interface_templates", "interface_templates__id"),
        ("interface_templates", "interface_templates__name"),
        ("front_port_templates", "front_port_templates__id"),
        ("front_port_templates", "front_port_templates__name"),
        ("rear_port_templates", "rear_port_templates__id"),
        ("rear_port_templates", "rear_port_templates__name"),
        ("module_bay_templates", "module_bay_templates__id"),
        ("module_family", "module_family__id"),
        ("module_family", "module_family__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

    def test_compatible_with_module_bay(self):
        """Test filtering module types that are compatible with a specific module bay based on module family."""
        module_bay = ModuleBay.objects.filter(module_family__isnull=False).first()
        compatible_module_types = ModuleType.objects.filter(module_family=module_bay.module_family)
        params = {"compatible_with_module_bay": module_bay.pk}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params).qs, compatible_module_types)

        # Test with module bay that has no module family - should return ALL module types
        module_bay_no_family = ModuleBay.objects.filter(module_family__isnull=True).first()
        params = {"compatible_with_module_bay": module_bay_no_family.pk}
        self.assertQuerysetEqual(self.filterset(params).qs, self.queryset, ordered=False)


class ModuleBayTemplateTestCase(FilterTestCases.FilterTestCase):
    queryset = ModuleBayTemplate.objects.all()
    filterset = ModuleBayTemplateFilterSet
    generic_filter_tests = [
        ("description",),
        ("device_type", "device_type__id"),
        ("device_type", "device_type__model"),
        ("label",),
        ("module_type", "module_type__id"),
        ("module_type", "module_type__model"),
        ("module_family", "module_family__id"),
        ("module_family", "module_family__name"),
        ("name",),
        ("position",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)

    def test_requires_first_party_modules(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"requires_first_party_modules": True}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(requires_first_party_modules=True),
            )
        with self.subTest():
            params = {"requires_first_party_modules": False}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(requires_first_party_modules=False),
            )


class ModuleBayTestCase(FilterTestCases.FilterTestCase):
    queryset = ModuleBay.objects.all()
    filterset = ModuleBayFilterSet
    generic_filter_tests = [
        ("description",),
        ("label",),
        ("parent_device", "parent_device__id"),
        ("parent_device", "parent_device__name"),
        ("parent_module", "parent_module__id"),
        ("installed_module", "installed_module__id"),
        ("name",),
        ("position",),
    ]

    @classmethod
    def setUpTestData(cls):
        common_test_data(cls)
        module_bays = ModuleBay.objects.all()[:2]
        module_bays[0].tags.set(Tag.objects.get_for_model(ModuleBay))
        module_bays[1].tags.set(Tag.objects.get_for_model(ModuleBay)[:3])


class VirtualDeviceContextTestCase(FilterTestCases.FilterTestCase, FilterTestCases):
    queryset = VirtualDeviceContext.objects.all()
    filterset = VirtualDeviceContextFilterSet
    generic_filter_tests = [
        ("description",),
        ("device", "device__name"),
        ("device", "device__id"),
        ("tenant", "tenant__name"),
        ("tenant", "tenant__id"),
        ("interfaces", "interfaces__id"),
        ("interfaces", "interfaces__name"),
        ("name",),
        ("role", "role__name"),
        ("status", "status__name"),
        ("role", "role__id"),
        ("status", "status__id"),
    ]

    @classmethod
    def setUpTestData(cls):
        device = Device.objects.first()
        intf_status = Status.objects.get_for_model(Interface).first()
        vdc_status = Status.objects.get_for_model(VirtualDeviceContext).first()
        intf_role = Role.objects.get_for_model(Interface).first()
        interface = Interface.objects.create(
            name="Int1", device=device, status=intf_status, role=intf_role, type=InterfaceTypeChoices.TYPE_100GE_CFP
        )
        cls.ips_v4 = IPAddress.objects.filter(ip_version=4)[:3]
        cls.ips_v6 = IPAddress.objects.filter(ip_version=6)[:3]
        interface.add_ip_addresses([*cls.ips_v4, *cls.ips_v6])
        vdcs = [
            VirtualDeviceContext.objects.create(
                device=device,
                status=vdc_status,
                identifier=200 + idx,
                name=f"Test VDC {idx}",
                primary_ip4=cls.ips_v4[idx],
                primary_ip6=cls.ips_v6[idx],
            )
            for idx in range(3)
        ]
        vdcs[0].tags.set(Tag.objects.get_for_model(VirtualDeviceContext))
        vdcs[1].tags.set(Tag.objects.get_for_model(VirtualDeviceContext)[:3])

        interfaces = [
            Interface.objects.create(
                device=device,
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                name=f"Interface 00{idx}",
                status=intf_status,
            )
            for idx in range(3)
        ]
        InterfaceVDCAssignment.objects.create(virtual_device_context=vdcs[0], interface=interfaces[0])
        InterfaceVDCAssignment.objects.create(virtual_device_context=vdcs[1], interface=interfaces[0])
        InterfaceVDCAssignment.objects.create(virtual_device_context=vdcs[1], interface=interfaces[1])
        InterfaceVDCAssignment.objects.create(virtual_device_context=vdcs[2], interface=interfaces[2])

    def test_has_primary_ip(self):
        # TODO: Not a generic_filter_test because this is a boolean filter but not a RelatedMembershipBooleanFilter
        with self.subTest():
            params = {"has_primary_ip": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                VirtualDeviceContext.objects.filter(Q(primary_ip4__isnull=False) | Q(primary_ip6__isnull=False)),
            )
        with self.subTest():
            params = {"has_primary_ip": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                VirtualDeviceContext.objects.filter(primary_ip4__isnull=True, primary_ip6__isnull=True),
            )

    def test_primary_ip4(self):
        params = {"primary_ip4": ["192.0.2.1/24", self.ips_v4[0].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, VirtualDeviceContext.objects.filter(primary_ip4=self.ips_v4[0])
        )

    def test_primary_ip6(self):
        params = {"primary_ip6": ["fe80::8ef:3eff:fe4c:3895/24", self.ips_v6[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, VirtualDeviceContext.objects.filter(primary_ip6=self.ips_v6[1])
        )


class InterfaceVDCAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = InterfaceVDCAssignment.objects.all()
    filterset = InterfaceVDCAssignmentFilterSet
    generic_filter_tests = [
        ("virtual_device_context", "virtual_device_context__id"),
        ("virtual_device_context", "virtual_device_context__name"),
        ("interface", "interface__id"),
        ("interface", "interface__name"),
        ("device", "interface__device__id"),
        ("device", "interface__device__name"),
    ]

    @classmethod
    def setUpTestData(cls):
        device_1 = Device.objects.first()
        device_2 = Device.objects.last()
        vdc_status = Status.objects.get_for_model(VirtualDeviceContext)[0]
        interface_status = Status.objects.get_for_model(Interface)[0]
        interfaces = [
            Interface.objects.create(
                device=device_1,
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                name=f"Interface 00{idx}",
                status=interface_status,
            )
            for idx in range(3)
        ]
        vdcs = [
            VirtualDeviceContext.objects.create(
                device=device_1,
                status=vdc_status,
                identifier=200 + idx,
                name=f"Test VDC {idx}",
            )
            for idx in range(3)
        ]
        InterfaceVDCAssignment.objects.create(virtual_device_context=vdcs[0], interface=interfaces[0])
        InterfaceVDCAssignment.objects.create(virtual_device_context=vdcs[1], interface=interfaces[0])
        InterfaceVDCAssignment.objects.create(virtual_device_context=vdcs[1], interface=interfaces[1])
        InterfaceVDCAssignment.objects.create(virtual_device_context=vdcs[2], interface=interfaces[2])
        InterfaceVDCAssignment.objects.create(
            virtual_device_context=VirtualDeviceContext.objects.create(
                device=device_2,
                status=vdc_status,
                identifier=200,
                name="Test VDC 0",
            ),
            interface=Interface.objects.create(
                device=device_2,
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                name="Interface 000",
                status=interface_status,
            ),
        )


class ModuleFamilyTestCase(FilterTestCases.FilterTestCase):
    """Test cases for the ModuleFamilyFilterSet."""

    queryset = ModuleFamily.objects.all()
    filterset = ModuleFamilyFilterSet
    generic_filter_tests = [
        ("name",),
        ("description",),
        ("module_types", "module_types__id"),
        ("module_types", "module_types__model"),
    ]

    @classmethod
    def setUpTestData(cls):
        """Create test data for filter tests."""
        manufacturers = (
            Manufacturer.objects.create(name="Manufacturer 1"),
            Manufacturer.objects.create(name="Manufacturer 2"),
        )

        cls.module_families = (
            ModuleFamily.objects.create(name="Module Family 1", description="First family"),
            ModuleFamily.objects.create(name="Module Family 2", description="Second family"),
            ModuleFamily.objects.create(name="Module Family 3", description="Third family"),
        )

        cls.module_types = (
            ModuleType.objects.create(
                manufacturer=manufacturers[0], model="Model 1", module_family=cls.module_families[0]
            ),
            ModuleType.objects.create(
                manufacturer=manufacturers[1], model="Model 2", module_family=cls.module_families[1]
            ),
        )
