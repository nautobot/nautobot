from django.contrib.auth import get_user_model
from django.db.models import Q
import django_filters
from drf_spectacular.utils import extend_schema_field
from timezone_field import TimeZoneField

from nautobot.core.filters import (
    BaseFilterSet,
    ContentTypeMultipleChoiceFilter,
    MultiValueCharFilter,
    MultiValueMACAddressFilter,
    MultiValueUUIDFilter,
    NameSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.core.utils.data import is_uuid
from nautobot.core.utils.deprecation import class_deprecated_in_favor_of
from nautobot.dcim.choices import (
    CableTypeChoices,
    ConsolePortTypeChoices,
    ControllerCapabilitiesChoices,
    InterfaceTypeChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    RackTypeChoices,
    RackWidthChoices,
)
from nautobot.dcim.constants import (
    MODULE_RECURSION_DEPTH_LIMIT,
    NONCONNECTABLE_IFACE_TYPES,
    VIRTUAL_IFACE_TYPES,
    WIRELESS_IFACE_TYPES,
)
from nautobot.dcim.filters.mixins import (
    CableTerminationModelFilterSetMixin,
    DeviceComponentModelFilterSetMixin,
    DeviceComponentTemplateModelFilterSetMixin,
    DeviceModuleCommonFiltersMixin,
    DeviceTypeModuleTypeCommonFiltersMixin,
    LocatableModelFilterSetMixin,
    ModularDeviceComponentModelFilterSetMixin,
    ModularDeviceComponentTemplateModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
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
from nautobot.extras.filters import (
    LocalContextModelFilterSetMixin,
    NautobotFilterSet,
    RoleModelFilterSetMixin,
    StatusModelFilterSetMixin,
)
from nautobot.extras.models import ExternalIntegration, SecretsGroup
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.models import IPAddress, VLAN, VLANGroup
from nautobot.tenancy.filters.mixins import TenancyModelFilterSetMixin
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, VirtualMachine
from nautobot.wireless.models import RadioProfile, WirelessNetwork

__all__ = (
    "CableFilterSet",
    "CableTerminationFilterSet",
    "CableTerminationModelFilterSetMixin",
    "ConsoleConnectionFilterSet",
    "ConsolePortFilterSet",
    "ConsolePortTemplateFilterSet",
    "ConsoleServerPortFilterSet",
    "ConsoleServerPortTemplateFilterSet",
    "ControllerFilterSet",
    "ControllerManagedDeviceGroupFilterSet",
    "DeviceBayFilterSet",
    "DeviceBayTemplateFilterSet",
    "DeviceFamilyFilterSet",
    "DeviceFilterSet",
    "DeviceRedundancyGroupFilterSet",
    "DeviceTypeFilterSet",
    "DeviceTypeToSoftwareImageFileFilterSet",
    "FrontPortFilterSet",
    "FrontPortTemplateFilterSet",
    "InterfaceConnectionFilterSet",
    "InterfaceFilterSet",
    "InterfaceRedundancyGroupAssociationFilterSet",
    "InterfaceRedundancyGroupFilterSet",
    "InterfaceTemplateFilterSet",
    "InventoryItemFilterSet",
    "LocationFilterSet",
    "LocationTypeFilterSet",
    "ManufacturerFilterSet",
    "ModuleBayFilterSet",
    "ModuleBayTemplateFilterSet",
    "ModuleFamilyFilterSet",
    "ModuleFilterSet",
    "ModuleTypeFilterSet",
    "PathEndpointFilterSet",
    "PathEndpointModelFilterSetMixin",
    "PlatformFilterSet",
    "PowerConnectionFilterSet",
    "PowerFeedFilterSet",
    "PowerOutletFilterSet",
    "PowerOutletTemplateFilterSet",
    "PowerPanelFilterSet",
    "PowerPortFilterSet",
    "PowerPortTemplateFilterSet",
    "RackFilterSet",
    "RackGroupFilterSet",
    "RackReservationFilterSet",
    "RearPortFilterSet",
    "RearPortTemplateFilterSet",
    "SoftwareImageFileFilterSet",
    "SoftwareVersionFilterSet",
    "VirtualChassisFilterSet",
)


class LocationTypeFilterSet(NautobotFilterSet, NameSearchFilterSet):
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=LocationType.objects.all(),
        to_field_name="name",
        label="Parent location type (name or ID)",
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("locations").get_choices,
    )

    class Meta:
        model = LocationType
        fields = ["id", "name", "description", "nestable"]


class LocationFilterSet(NautobotFilterSet, StatusModelFilterSetMixin, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "facility": "icontains",
            "description": "icontains",
            "physical_address": "icontains",
            "shipping_address": "icontains",
            "contact_name": "icontains",
            "contact_phone": "icontains",
            "contact_email": "icontains",
            "comments": "icontains",
            "asn": {
                "lookup_expr": "exact",
                "preprocessor": int,  # asn expects an int
            },
        },
    )
    location_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=LocationType.objects.all(),
        to_field_name="name",
        label="Location type (name or ID)",
    )
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Parent location (name or ID)",
    )
    subtree = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location(s) and descendants thereof (name or ID)",
        method="_subtree",
    )
    child_location_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=LocationType.objects.all(),
        to_field_name="name",
        label="Child location type (name or ID)",
        method="_child_location_type",
    )
    content_type = ContentTypeMultipleChoiceFilter(
        field_name="location_type__content_types",
        choices=FeatureQuery("locations").get_choices,
        label="Object types allowed to be associated with this Location Type",
    )
    has_circuit_terminations = RelatedMembershipBooleanFilter(
        field_name="circuit_terminations",
        label="Has circuit terminations",
    )
    devices = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Devices (name or ID)",
    )
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has devices",
    )
    power_panels = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=PowerPanel.objects.all(),
        label="Power panels (name or ID)",
    )
    has_power_panels = RelatedMembershipBooleanFilter(
        field_name="power_panels",
        label="Has power panels",
    )
    rack_groups = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=RackGroup.objects.all(),
        to_field_name="name",
        label="Rack groups (name or ID)",
    )
    has_rack_groups = RelatedMembershipBooleanFilter(
        field_name="rack_groups",
        label="Has rack groups",
    )
    has_racks = RelatedMembershipBooleanFilter(
        field_name="racks",
        label="Has racks",
    )
    racks = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Rack.objects.all(),
        to_field_name="name",
        label="Rack (name or ID)",
    )
    has_prefixes = RelatedMembershipBooleanFilter(
        field_name="prefixes",
        label="Has prefixes",
    )
    vlan_groups = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VLANGroup.objects.all(),
        to_field_name="name",
        label="VLAN groups (name or ID)",
    )
    has_vlan_groups = RelatedMembershipBooleanFilter(
        field_name="vlan_groups",
        label="Has VLAN groups",
    )
    has_vlans = RelatedMembershipBooleanFilter(
        field_name="vlans",
        label="Has VLANs",
    )
    vlans = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="vid",
        queryset=VLAN.objects.all(),
        label="Tagged VLANs (VID or ID)",
    )
    has_clusters = RelatedMembershipBooleanFilter(
        field_name="clusters",
        label="Has clusters",
    )
    clusters = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        to_field_name="name",
        label="Clusters (name or ID)",
    )
    time_zone = django_filters.MultipleChoiceFilter(
        choices=[(str(obj), name) for obj, name in TimeZoneField().choices],
        label="Time zone",
        null_value="",
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "description",
            "asn",
            "circuit_terminations",
            "comments",
            "contact_email",
            "contact_name",
            "contact_phone",
            "facility",
            "latitude",
            "longitude",
            "physical_address",
            "prefixes",
            "shipping_address",
            "tags",
        ]

    def generate_query__child_location_type(self, value):
        """Helper method used by DynamicGroups and by _child_location_type() method."""
        if value:
            # Locations whose location type is a parent of value, or whose location type *is* value but can be nested
            return Q(location_type__children__in=value) | Q(location_type__in=value, location_type__nestable=True)
        return Q()

    @extend_schema_field({"type": "string"})
    def _child_location_type(self, queryset, name, value):
        """FilterSet method for getting Locations that can have a child of the given LocationType(s)."""
        params = self.generate_query__child_location_type(value)
        return queryset.filter(params)

    def generate_query__subtree(self, value):
        """Helper method used by DynamicGroups and by _subtree() method."""
        if value:
            max_depth = Location.objects.with_tree_fields().extra(order_by=["-__tree.tree_depth"]).first().tree_depth
            params = Q(pk__in=[v.pk for v in value])
            filter_name = "in"
            for _i in range(max_depth):
                filter_name = f"parent__{filter_name}"
                params |= Q(**{filter_name: value})
            return params
        return Q()

    @extend_schema_field({"type": "string"})
    def _subtree(self, queryset, name, value):
        """FilterSet method for getting Locations that are or are descended from a given Location(s)."""
        if value:
            params = self.generate_query__subtree(value)
            return queryset.with_tree_fields().filter(params)
        return queryset


class RackGroupFilterSet(LocatableModelFilterSetMixin, NautobotFilterSet, NameSearchFilterSet):
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        to_field_name="name",
        label="Parent (name or ID)",
    )
    ancestors = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location(s) and ancestors thereof (name or ID)",
        method="_ancestors",
    )
    children = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        to_field_name="name",
        label="Children (name or ID)",
    )
    has_children = RelatedMembershipBooleanFilter(
        field_name="children",
        label="Has children",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_panels = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        field_name="power_panels",
        to_field_name="name",
        queryset=PowerPanel.objects.all(),
        label="Power panels (name or ID)",
    )
    has_power_panels = RelatedMembershipBooleanFilter(
        field_name="power_panels",
        label="Has power panels",
    )
    has_racks = RelatedMembershipBooleanFilter(
        field_name="racks",
        label="Has racks",
    )

    class Meta:
        model = RackGroup
        fields = ["id", "name", "description", "racks"]

    def generate_query__ancestors(self, value):
        """Helper method used by _ancestors() method."""
        if value:
            locations = Location.objects.filter(pk__in=[v.pk for v in value])
            pk_list = []
            for location in locations:
                parent_locations = location.ancestors(include_self=True)
                pk_list.extend([v.pk for v in parent_locations])
            params = Q(location__pk__in=pk_list)
            return params
        return Q()

    @extend_schema_field({"type": "string"})
    def _ancestors(self, queryset, name, value):
        """FilterSet method for, given a location, getting RackGroups that exist with in the parent Location(s) and the location itself."""
        if value:
            params = self.generate_query__ancestors(value)
            return queryset.filter(params)
        return queryset


class RackFilterSet(
    NautobotFilterSet,
    LocatableModelFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "facility_id": "icontains",
            "serial": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "asset_tag": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "comments": "icontains",
        },
    )
    rack_group = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=RackGroup.objects.all(),
        field_name="rack_group",
        to_field_name="name",
        label="Rack group (name or ID)",
    )
    type = django_filters.MultipleChoiceFilter(choices=RackTypeChoices)
    width = django_filters.MultipleChoiceFilter(choices=RackWidthChoices)
    serial = MultiValueCharFilter(lookup_expr="iexact", label="Serial Number")
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has devices",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_feeds = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        field_name="power_feeds",
        to_field_name="name",
        queryset=PowerFeed.objects.all(),
        label="Power feeds (name or ID)",
    )
    has_power_feeds = RelatedMembershipBooleanFilter(
        field_name="power_feeds",
        label="Has power feeds",
    )
    has_rack_reservations = RelatedMembershipBooleanFilter(
        field_name="rack_reservations",
        label="Has rack reservations",
    )

    class Meta:
        model = Rack
        fields = [
            "id",
            "name",
            "facility_id",
            "asset_tag",
            "u_height",
            "desc_units",
            "outer_width",
            "outer_depth",
            "outer_unit",
            "comments",
            "devices",
            "rack_reservations",
            "tags",
        ]


class RackReservationFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "rack__name": "icontains",
            "rack__facility_id": "icontains",
            "user__username": "icontains",
            "description": "icontains",
        },
    )
    rack_group = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=RackGroup.objects.all(),
        field_name="rack__rack_group",
        to_field_name="name",
        label="Rack group (name or ID)",
    )
    user = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=get_user_model().objects.all(),
        to_field_name="username",
        label="User (username or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    rack = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Rack.objects.all(),
        to_field_name="name",
        label="Rack (name or ID)",
    )

    class Meta:
        model = RackReservation
        fields = ["id", "created", "description", "tags"]


class ManufacturerFilterSet(NautobotFilterSet, NameSearchFilterSet):
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    inventory_items = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=InventoryItem.objects.all(),
        to_field_name="name",
        label="Inventory items (name or ID)",
    )
    has_inventory_items = RelatedMembershipBooleanFilter(
        field_name="inventory_items",
        label="Has inventory items",
    )
    device_types = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        label="Device types (model or ID)",
    )
    has_device_types = RelatedMembershipBooleanFilter(
        field_name="device_types",
        label="Has device types",
    )
    platforms = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Platform.objects.all(),
        to_field_name="name",
        label="Platforms (name or ID)",
    )
    has_platforms = RelatedMembershipBooleanFilter(
        field_name="platforms",
        label="Has platforms",
    )

    class Meta:
        model = Manufacturer
        fields = ["id", "name", "description"]


class DeviceFamilyFilterSet(NautobotFilterSet, NameSearchFilterSet):
    device_types = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        label="Device types (model or ID)",
    )
    has_device_types = RelatedMembershipBooleanFilter(
        field_name="device_types",
        label="Has device types",
    )

    class Meta:
        model = DeviceFamily
        fields = ["id", "name", "description", "tags"]


class DeviceTypeFilterSet(DeviceTypeModuleTypeCommonFiltersMixin, NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "manufacturer__name": "icontains",
            "device_family__name": "icontains",
            "model": "icontains",
            "part_number": "icontains",
            "comments": "icontains",
        },
    )
    device_family = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceFamily.objects.all(), to_field_name="name", label="Device family (name or ID)"
    )
    console_ports = django_filters.BooleanFilter(
        method="_console_ports",
        label="Has console ports",
    )
    console_server_ports = django_filters.BooleanFilter(
        method="_console_server_ports",
        label="Has console server ports",
    )
    power_ports = django_filters.BooleanFilter(
        method="_power_ports",
        label="Has power ports",
    )
    power_outlets = django_filters.BooleanFilter(
        method="_power_outlets",
        label="Has power outlets",
    )
    interfaces = django_filters.BooleanFilter(
        method="_interfaces",
        label="Has interfaces",
    )
    pass_through_ports = RelatedMembershipBooleanFilter(
        field_name="front_port_templates",
        label="Has pass-through ports",
    )
    device_bays = django_filters.BooleanFilter(
        method="_device_bays",
        label="Has device bays",
    )
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has device instances",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    device_bay_templates = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=DeviceBayTemplate.objects.all(),
        label="Device bay templates (name or ID)",
    )
    has_device_bay_templates = RelatedMembershipBooleanFilter(
        field_name="device_bay_templates",
        label="Has device bay templates",
    )
    has_software_image_files = RelatedMembershipBooleanFilter(
        field_name="software_image_files",
        label="Has software image files",
    )
    software_image_files = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareImageFile.objects.all(),
        to_field_name="image_file_name",
        label="Software image files (image file name or ID)",
    )

    class Meta:
        model = DeviceType
        fields = [
            "id",
            "model",
            "part_number",
            "u_height",
            "is_full_depth",
            "subdevice_role",
            "comments",
            "devices",
            "tags",
            "has_software_image_files",
            "software_image_files",
        ]

    def _console_ports(self, queryset, name, value):
        return queryset.exclude(console_port_templates__isnull=value)

    def _console_server_ports(self, queryset, name, value):
        return queryset.exclude(console_server_port_templates__isnull=value)

    def _power_ports(self, queryset, name, value):
        return queryset.exclude(power_port_templates__isnull=value)

    def _power_outlets(self, queryset, name, value):
        return queryset.exclude(power_outlet_templates__isnull=value)

    def _interfaces(self, queryset, name, value):
        return queryset.exclude(interface_templates__isnull=value)

    def _device_bays(self, queryset, name, value):
        return queryset.exclude(device_bay_templates__isnull=value)


# TODO: remove in 2.2
@class_deprecated_in_favor_of(DeviceComponentTemplateModelFilterSetMixin)
class DeviceTypeComponentFilterSet(DeviceComponentTemplateModelFilterSetMixin):
    pass


class ConsolePortTemplateFilterSet(ModularDeviceComponentTemplateModelFilterSetMixin, BaseFilterSet):
    class Meta:
        model = ConsolePortTemplate
        fields = ["type"]


class ConsoleServerPortTemplateFilterSet(ModularDeviceComponentTemplateModelFilterSetMixin, BaseFilterSet):
    class Meta:
        model = ConsoleServerPortTemplate
        fields = ["type"]


class PowerPortTemplateFilterSet(ModularDeviceComponentTemplateModelFilterSetMixin, BaseFilterSet):
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_outlet_templates = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=PowerOutletTemplate.objects.all(),
        label="Power outlet templates (name or ID)",
    )
    has_power_outlet_templates = RelatedMembershipBooleanFilter(
        field_name="power_outlet_templates",
        label="Has power outlet templates",
    )

    class Meta:
        model = PowerPortTemplate
        fields = [
            "type",
            "maximum_draw",
            "allocated_draw",
        ]


class PowerOutletTemplateFilterSet(ModularDeviceComponentTemplateModelFilterSetMixin, BaseFilterSet):
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_port_template = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=PowerPortTemplate.objects.all(),
        label="Power port template (name or ID)",
    )

    class Meta:
        model = PowerOutletTemplate
        fields = ["type", "feed_leg"]


class InterfaceTemplateFilterSet(ModularDeviceComponentTemplateModelFilterSetMixin, BaseFilterSet):
    class Meta:
        model = InterfaceTemplate
        fields = ["type", "mgmt_only"]


class FrontPortTemplateFilterSet(ModularDeviceComponentTemplateModelFilterSetMixin, BaseFilterSet):
    rear_port_template = django_filters.ModelMultipleChoiceFilter(
        queryset=RearPortTemplate.objects.all(),
        label="Rear port template",
    )

    class Meta:
        model = FrontPortTemplate
        fields = ["type", "rear_port_position"]


class RearPortTemplateFilterSet(ModularDeviceComponentTemplateModelFilterSetMixin, BaseFilterSet):
    front_port_templates = django_filters.ModelMultipleChoiceFilter(
        queryset=FrontPortTemplate.objects.all(),
        label="Front port templates",
    )
    has_front_port_templates = RelatedMembershipBooleanFilter(
        field_name="front_port_templates",
        label="Has front port templates",
    )

    class Meta:
        model = RearPortTemplate
        fields = ["type", "positions"]


class DeviceBayTemplateFilterSet(DeviceComponentTemplateModelFilterSetMixin, BaseFilterSet):
    class Meta:
        model = DeviceBayTemplate
        fields = []


class PlatformFilterSet(NautobotFilterSet, NameSearchFilterSet):
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Manufacturer.objects.all(), to_field_name="name", label="Manufacturer (name or ID)"
    )
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has devices",
    )
    has_virtual_machines = RelatedMembershipBooleanFilter(
        field_name="virtual_machines",
        label="Has virtual machines",
    )

    class Meta:
        model = Platform
        fields = [
            "id",
            "name",
            "napalm_driver",
            "napalm_args",
            "network_driver",
            "description",
            "devices",
            "virtual_machines",
        ]


class DeviceFilterSet(
    NautobotFilterSet,
    DeviceModuleCommonFiltersMixin,
    LocatableModelFilterSetMixin,
    TenancyModelFilterSetMixin,
    LocalContextModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "serial": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "inventory_items__serial": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "asset_tag": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "device_type__manufacturer__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "device_type__device_family__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "comments": "icontains",
        },
    )
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_type__manufacturer",
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
        label="Manufacturer (name or ID)",
    )
    device_family = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_type__device_family",
        queryset=DeviceFamily.objects.all(),
        to_field_name="name",
        label="Device family (name or ID)",
    )
    device_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        label="Device type (model or ID)",
    )
    platform = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Platform.objects.all(), to_field_name="name", label="Platform (name or ID)"
    )
    rack_group = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=RackGroup.objects.all(),
        field_name="rack__rack_group",
        to_field_name="name",
        label="Rack group (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    rack = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Rack.objects.all(),
        to_field_name="name",
        label="Rack (name or ID)",
    )
    cluster = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        to_field_name="name",
        label="VM cluster (name or ID)",
    )
    is_full_depth = django_filters.BooleanFilter(
        field_name="device_type__is_full_depth",
        label="Is full depth",
    )
    serial = MultiValueCharFilter(lookup_expr="iexact")
    has_primary_ip = django_filters.BooleanFilter(
        method="_has_primary_ip",
        label="Has a primary IP",
    )
    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        to_field_name="name",
        label="Secrets group (name or ID)",
    )
    virtual_chassis = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualChassis.objects.all(),
        to_field_name="name",
        label="Virtual chassis (name or ID)",
    )
    is_virtual_chassis_member = RelatedMembershipBooleanFilter(
        field_name="virtual_chassis",
        label="Is a virtual chassis member",
    )
    device_redundancy_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_redundancy_group",
        queryset=DeviceRedundancyGroup.objects.all(),
        to_field_name="name",
        label="Device Redundancy Groups (name or ID)",
    )
    controller_managed_device_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="controller_managed_device_group",
        queryset=ControllerManagedDeviceGroup.objects.all(),
        to_field_name="name",
        label="Controller Managed Device Groups (name or ID)",
    )
    virtual_chassis_member = is_virtual_chassis_member
    has_device_bays = RelatedMembershipBooleanFilter(
        field_name="device_bays",
        label="Has device bays",
    )
    device_bays = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceBay.objects.all(),
        label="Device Bays",
    )
    has_software_image_files = RelatedMembershipBooleanFilter(
        field_name="software_image_files",
        label="Has software image files",
    )
    software_image_files = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareImageFile.objects.all(),
        to_field_name="image_file_name",
        label="Software image files (image file name or ID)",
    )
    has_software_version = RelatedMembershipBooleanFilter(
        field_name="software_version",
        label="Has software version",
    )
    software_version = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareVersion.objects.all(),
        to_field_name="version",
        label="Software version (version or ID)",
    )
    ip_addresses = MultiValueCharFilter(
        method="filter_ip_addresses",
        label="IP addresses (address or ID)",
        distinct=True,
    )
    has_ip_addresses = RelatedMembershipBooleanFilter(field_name="interfaces__ip_addresses", label="Has IP addresses")
    radio_profiles = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="controller_managed_device_group__radio_profiles",
        queryset=RadioProfile.objects.all(),
        to_field_name="name",
        label="Radio Profiles (name or ID)",
    )
    has_radio_profiles = RelatedMembershipBooleanFilter(
        field_name="controller_managed_device_group__radio_profiles",
        label="Has radio profiles",
    )
    wireless_networks = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="controller_managed_device_group__wireless_networks",
        queryset=WirelessNetwork.objects.all(),
        to_field_name="name",
        label="Wireless Networks (name or ID)",
    )
    has_wireless_networks = RelatedMembershipBooleanFilter(
        field_name="controller_managed_device_group__wireless_networks",
        label="Has wireless networks",
    )
    controller = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="controller_managed_device_group__controller",
        queryset=Controller.objects.all(),
        to_field_name="name",
        label="Controller (name or ID)",
    )

    def filter_ip_addresses(self, queryset, name, value):
        pk_values = set(item for item in value if is_uuid(item))
        addresses = set(item for item in value if item not in pk_values)

        ip_queryset = IPAddress.objects.filter_address_or_pk_in(addresses, pk_values)
        return queryset.filter(interfaces__ip_addresses__in=ip_queryset).distinct()

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "asset_tag",
            "face",
            "position",
            "vc_position",
            "vc_priority",
            "device_redundancy_group_priority",
            "tags",
            "interfaces",
            "has_software_image_files",
            "software_image_files",
            "has_software_version",
            "software_version",
        ]

    def generate_query__has_primary_ip(self, value):
        query = Q(primary_ip4__isnull=False) | Q(primary_ip6__isnull=False)
        if not value:
            return ~query
        return query

    def _has_primary_ip(self, queryset, name, value):
        params = self.generate_query__has_primary_ip(value)
        return queryset.filter(params)


# TODO: remove in 2.2
@class_deprecated_in_favor_of(DeviceComponentModelFilterSetMixin)
class DeviceComponentFilterSet(DeviceComponentModelFilterSetMixin):
    pass


# TODO: remove in 2.2
@class_deprecated_in_favor_of(CableTerminationModelFilterSetMixin)
class CableTerminationFilterSet(CableTerminationModelFilterSetMixin):
    pass


# TODO: remove in 2.2
@class_deprecated_in_favor_of(PathEndpointModelFilterSetMixin)
class PathEndpointFilterSet(PathEndpointModelFilterSetMixin):
    pass


class ConsolePortFilterSet(
    ModularDeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
    BaseFilterSet,
):
    type = django_filters.MultipleChoiceFilter(choices=ConsolePortTypeChoices, null_value=None)

    class Meta:
        model = ConsolePort
        fields = ["id", "name", "description", "label", "tags"]


class ConsoleServerPortFilterSet(
    ModularDeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
    BaseFilterSet,
):
    type = django_filters.MultipleChoiceFilter(choices=ConsolePortTypeChoices, null_value=None)

    class Meta:
        model = ConsoleServerPort
        fields = ["id", "name", "description", "label", "tags"]


class PowerPortFilterSet(
    ModularDeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
    BaseFilterSet,
):
    type = django_filters.MultipleChoiceFilter(choices=PowerPortTypeChoices, null_value=None)
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_outlets = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        field_name="power_outlets",
        to_field_name="name",
        queryset=PowerOutlet.objects.all(),
        label="Power outlets (name or ID)",
    )
    has_power_outlets = RelatedMembershipBooleanFilter(
        field_name="power_outlets",
        label="Has power outlets",
    )

    class Meta:
        model = PowerPort
        fields = ["id", "name", "maximum_draw", "allocated_draw", "description", "label", "tags"]


class PowerOutletFilterSet(
    ModularDeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
    BaseFilterSet,
):
    type = django_filters.MultipleChoiceFilter(choices=PowerOutletTypeChoices, null_value=None)
    power_port = django_filters.ModelMultipleChoiceFilter(
        queryset=PowerPort.objects.all(),
        label="Power port",
    )

    class Meta:
        model = PowerOutlet
        fields = ["id", "name", "feed_leg", "description", "label", "tags"]


class InterfaceFilterSet(
    BaseFilterSet,
    ModularDeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    # Override device and device_id filters from ModularDeviceComponentModelFilterSetMixin to
    # match against any peer virtual chassis members
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
        method="filter_device",
    )
    # TODO 3.0: Remove this filter. Deprecated in favor of above NaturalKeyOrPKMultipleChoiceFilter `device`
    device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        method="filter_device_id",
        field_name="device",
        label='Device (ID)  (deprecated, use "device" filter instead)',
    )
    device_with_common_vc = django_filters.UUIDFilter(
        method="filter_device_common_vc_id",
        field_name="pk",
        label="Virtual Chassis member Device (ID)",
    )
    kind = django_filters.CharFilter(
        method="filter_kind",
        label="Kind of interface",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    parent_interface = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Parent interface (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    bridge = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Bridge interface (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    lag = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=Interface.objects.filter(type=InterfaceTypeChoices.TYPE_LAG),
        label="LAG interface (name or ID)",
    )
    untagged_vlan = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="vid",
        queryset=VLAN.objects.all(),
        label="Untagged VLAN (VID or ID)",
    )
    tagged_vlans = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="vid",
        queryset=VLAN.objects.all(),
        label="Tagged VLANs (VID or ID)",
    )
    has_tagged_vlans = RelatedMembershipBooleanFilter(
        field_name="tagged_vlans",
        label="Has tagged VLANs",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    child_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Child interfaces (name or ID)",
    )
    has_child_interfaces = RelatedMembershipBooleanFilter(
        field_name="child_interfaces",
        label="Has child interfaces",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    bridged_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=Interface.objects.all(),
        label="Bridged interfaces (name or ID)",
    )
    has_bridged_interfaces = RelatedMembershipBooleanFilter(
        field_name="bridged_interfaces",
        label="Has bridged interfaces",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    member_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=Interface.objects.all(),
        label="Member interfaces (name or ID)",
    )
    has_member_interfaces = RelatedMembershipBooleanFilter(
        field_name="member_interfaces",
        label="Has member interfaces",
    )
    mac_address = MultiValueMACAddressFilter()
    vlan_id = django_filters.CharFilter(method="filter_vlan_id", label="Assigned VLAN")
    vlan = django_filters.NumberFilter(method="filter_vlan", label="Assigned VID")
    type = django_filters.MultipleChoiceFilter(choices=InterfaceTypeChoices, null_value=None)
    interface_redundancy_groups = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=InterfaceRedundancyGroup.objects.all(),
        to_field_name="name",
    )
    ip_addresses = MultiValueCharFilter(
        method="filter_ip_addresses",
        label="IP addresses (address or ID)",
        distinct=True,
    )
    has_ip_addresses = RelatedMembershipBooleanFilter(field_name="ip_addresses", label="Has IP addresses")
    virtual_device_contexts = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualDeviceContext.objects.all(),
        to_field_name="name",
        label="Virtual Device Context (name or ID)",
    )
    has_virtual_device_contexts = RelatedMembershipBooleanFilter(
        field_name="virtual_device_contexts",
        label="Has Virtual Device Context",
    )

    def filter_ip_addresses(self, queryset, name, value):
        pk_values = set(item for item in value if is_uuid(item))
        addresses = set(item for item in value if item not in pk_values)

        ip_queryset = IPAddress.objects.filter_address_or_pk_in(addresses, pk_values)
        return queryset.filter(ip_addresses__in=ip_queryset).distinct()

    class Meta:
        model = Interface
        fields = [
            "id",
            "name",
            "type",
            "enabled",
            "mtu",
            "mgmt_only",
            "mode",
            "description",
            "label",
            "tags",
            "virtual_device_contexts",
            "interface_redundancy_groups",
        ]

    def generate_query_filter_device(self, value):
        if not hasattr(value, "__iter__") or isinstance(value, str):
            value = [value]

        device_ids = set(str(item) for item in value if is_uuid(item))
        device_names = set(str(item) for item in value if not is_uuid(item))
        devices = Device.objects.filter(Q(name__in=device_names) | Q(pk__in=device_ids))
        all_interface_ids = []
        for device in devices:
            all_interface_ids.extend(device.vc_interfaces.values_list("id", flat=True))
        return Q(pk__in=all_interface_ids)

    def filter_device(self, queryset, name, value):
        if not value:
            return queryset
        params = self.generate_query_filter_device(value)
        return queryset.filter(params)

    def generate_query_filter_device_id(self, value):
        if not hasattr(value, "__iter__") or isinstance(value, str):
            value = [value]

        all_interface_ids = []
        for device in value:
            all_interface_ids.extend(device.vc_interfaces.values_list("id", flat=True))
        return Q(pk__in=all_interface_ids)

    def filter_device_id(self, queryset, name, value):
        if not value:
            return queryset
        params = self.generate_query_filter_device_id(value)
        return queryset.filter(params)

    def filter_device_common_vc_id(self, queryset, name, value):
        # Include interfaces that share common virtual chassis
        try:
            device = Device.objects.get(pk=value)
            return queryset.filter(pk__in=device.common_vc_interfaces.values_list("pk", flat=True))
        except Device.DoesNotExist:
            return queryset.none()

    def filter_vlan_id(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(Q(untagged_vlan_id=value) | Q(tagged_vlans=value))

    def filter_vlan(self, queryset, name, value):
        value = str(value).strip()
        if not value:
            return queryset
        return queryset.filter(Q(untagged_vlan_id__vid=value) | Q(tagged_vlans__vid=value))

    def filter_kind(self, queryset, name, value):
        value = value.strip().lower()
        return {
            "physical": queryset.exclude(type__in=NONCONNECTABLE_IFACE_TYPES),
            "virtual": queryset.filter(type__in=VIRTUAL_IFACE_TYPES),
            "wireless": queryset.filter(type__in=WIRELESS_IFACE_TYPES),
        }.get(value, queryset.none())


class FrontPortFilterSet(ModularDeviceComponentModelFilterSetMixin, CableTerminationModelFilterSetMixin, BaseFilterSet):
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    rear_port = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=RearPort.objects.all(),
        label="Rear port (name or ID)",
    )

    class Meta:
        model = FrontPort
        fields = ["id", "name", "type", "description", "label", "rear_port_position", "tags"]


class RearPortFilterSet(ModularDeviceComponentModelFilterSetMixin, CableTerminationModelFilterSetMixin, BaseFilterSet):
    front_ports = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=FrontPort.objects.all(),
        label="Front ports (name or ID)",
    )
    has_front_ports = RelatedMembershipBooleanFilter(
        field_name="front_ports",
        label="Has front ports",
    )

    class Meta:
        model = RearPort
        fields = ["id", "name", "type", "positions", "description", "label", "tags"]


class DeviceBayFilterSet(DeviceComponentModelFilterSetMixin, BaseFilterSet):
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    installed_device = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        field_name="installed_device",
        to_field_name="name",
        queryset=Device.objects.all(),
        label="Installed device (name or ID)",
    )

    class Meta:
        model = DeviceBay
        fields = ["id", "name", "description", "label", "tags"]


class InventoryItemFilterSet(DeviceComponentModelFilterSetMixin, BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "part_id": "icontains",
            "serial": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "asset_tag": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "description": "icontains",
        },
    )
    location = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Location.objects.all(),
        field_name="device__location",
        to_field_name="name",
        label="Location (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    device = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=InventoryItem.objects.all(),
        to_field_name="name",
        label="Parent items (name or ID)",
    )
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
        label="Manufacturer (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    children = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=InventoryItem.objects.all(),
        to_field_name="name",
        label="Child items (name or ID)",
    )
    has_children = RelatedMembershipBooleanFilter(
        field_name="children",
        label="Has child items",
    )
    serial = MultiValueCharFilter(lookup_expr="iexact")
    has_software_image_files = RelatedMembershipBooleanFilter(
        field_name="software_image_files",
        label="Has software image files",
    )
    software_image_files = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareImageFile.objects.all(),
        to_field_name="image_file_name",
        label="Software image files (image file name or ID)",
    )
    has_software_version = RelatedMembershipBooleanFilter(
        field_name="software_version",
        label="Has software version",
    )
    software_version = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareVersion.objects.all(),
        to_field_name="version",
        label="Software version (version or ID)",
    )

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "part_id",
            "asset_tag",
            "discovered",
            "description",
            "label",
            "has_software_image_files",
            "software_image_files",
            "has_software_version",
            "software_version",
            "tags",
        ]


class VirtualChassisFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "members__name": "icontains",
            "domain": "icontains",
        },
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    master = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Master (name or ID)",
    )
    # TODO Check this filter as it is not using TreeNode...
    location = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        field_name="master__location",
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )
    tenant = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="master__tenant",
        queryset=Tenant.objects.all(),
        to_field_name="name",
        label="Tenant (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    members = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=Device.objects.all(),
        label="Device members (name or ID)",
    )
    has_members = RelatedMembershipBooleanFilter(
        field_name="members",
        label="Has device members",
    )

    class Meta:
        model = VirtualChassis
        fields = ["id", "domain", "name", "tags"]


class CableFilterSet(NautobotFilterSet, StatusModelFilterSetMixin):
    q = SearchFilter(filter_predicates={"label": "icontains"})
    type = django_filters.MultipleChoiceFilter(choices=CableTypeChoices)
    color = MultiValueCharFilter()
    device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        method="filter_device_id",
        field_name="_termination_a_device_id",
        label="Device (ID)",
    )
    device = MultiValueCharFilter(method="filter_device", field_name="device__name", label="Device (name)")
    rack_id = MultiValueUUIDFilter(method="filter_device", field_name="device__rack_id", label="Rack (ID)")
    rack = MultiValueCharFilter(method="filter_device", field_name="device__rack__name", label="Rack (name)")
    location_id = MultiValueUUIDFilter(method="filter_device", field_name="device__location_id", label="Location (ID)")
    location = MultiValueCharFilter(
        method="filter_device", field_name="device__location__name", label="Location (name)"
    )
    tenant_id = MultiValueUUIDFilter(method="filter_device", field_name="device__tenant_id", label="Tenant (ID)")
    tenant = MultiValueCharFilter(method="filter_device", field_name="device__tenant__name", label="Tenant (name)")
    termination_a_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("cable_terminations").get_choices,
        conjoined=False,
    )
    termination_b_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("cable_terminations").get_choices,
        conjoined=False,
    )
    termination_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("cable_terminations").get_choices,
        conjoined=False,
        distinct=True,
        lookup_expr="in",
        method="_termination_type",
        label="Termination (either end) type",
    )

    class Meta:
        model = Cable
        fields = [
            "id",
            "label",
            "length",
            "length_unit",
            "termination_a_id",
            "termination_b_id",
            "tags",
        ]

    def filter_device(self, queryset, name, value):
        queryset = queryset.filter(
            Q(**{f"_termination_a_{name}__in": value}) | Q(**{f"_termination_b_{name}__in": value})
        )
        return queryset

    def generate_query_filter_device_id(self, value):
        if not hasattr(value, "__iter__") or isinstance(value, str):
            value = [value]
        return Q(_termination_a_device_id__in=value) | Q(_termination_b_device_id__in=value)

    def filter_device_id(self, queryset, name, value):
        if not value:
            return queryset
        params = self.generate_query_filter_device_id(value)
        return queryset.filter(params)

    def generate_query__termination_type(self, value):
        a_type_q = Q()
        b_type_q = Q()
        for label in value:
            app_label, model = label.split(".")
            a_type_q |= Q(termination_a_type__app_label=app_label, termination_a_type__model=model)
            b_type_q |= Q(termination_b_type__app_label=app_label, termination_b_type__model=model)
        return a_type_q | b_type_q

    @extend_schema_field({"type": "string"})
    def _termination_type(self, queryset, name, value):
        return queryset.filter(self.generate_query__termination_type(value)).distinct()


class ConnectionFilterSetMixin:
    def filter_location(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(device__location__name=value)

    def filter_device(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(**{f"{name}__in": value})


# TODO: remove in 2.2
@class_deprecated_in_favor_of(ConnectionFilterSetMixin)
class ConnectionFilterSet(ConnectionFilterSetMixin):
    pass


class ConsoleConnectionFilterSet(ConnectionFilterSetMixin, BaseFilterSet):
    location = django_filters.CharFilter(
        method="filter_location",
        label="Location (name)",
    )
    device_id = MultiValueUUIDFilter(method="filter_device", label="Device (ID)")
    device = MultiValueCharFilter(method="filter_device", field_name="device__name", label="Device (name)")

    class Meta:
        model = ConsolePort
        fields = ["name"]


class PowerConnectionFilterSet(ConnectionFilterSetMixin, BaseFilterSet):
    location = django_filters.CharFilter(
        method="filter_location",
        label="Location (name)",
    )
    device_id = MultiValueUUIDFilter(method="filter_device", label="Device (ID)")
    device = MultiValueCharFilter(method="filter_device", field_name="device__name", label="Device (name)")

    class Meta:
        model = PowerPort
        fields = ["name"]


class InterfaceConnectionFilterSet(ConnectionFilterSetMixin, BaseFilterSet):
    location = django_filters.CharFilter(
        method="filter_location",
        label="Location (name)",
    )
    device_id = MultiValueUUIDFilter(method="filter_device", label="Device (ID)")
    device = MultiValueCharFilter(method="filter_device", field_name="device__name", label="Device (name)")

    class Meta:
        model = Interface
        fields = []


class PowerPanelFilterSet(LocatableModelFilterSetMixin, NautobotFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains"})
    rack_group = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=RackGroup.objects.all(),
        to_field_name="name",
        label="Rack group (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_feeds = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=PowerFeed.objects.all(),
        label="Power feeds (name or ID)",
    )
    has_power_feeds = RelatedMembershipBooleanFilter(
        field_name="power_feeds",
        label="Has power feeds",
    )
    has_feeders = RelatedMembershipBooleanFilter(
        field_name="feeders",
        label="Has feeders",
    )

    class Meta:
        model = PowerPanel
        fields = ["id", "name", "panel_type", "power_path", "tags"]


class PowerFeedFilterSet(
    NautobotFilterSet,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
    StatusModelFilterSetMixin,
):
    q = SearchFilter(filter_predicates={"name": "icontains", "comments": "icontains"})
    location = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        field_name="power_panel__location",
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_panel = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=PowerPanel.objects.all(),
        to_field_name="name",
        label="Power panel (name or ID)",
    )
    destination_panel = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=PowerPanel.objects.all(),
        to_field_name="name",
        label="Destination panel (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    rack = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Rack.objects.all(),
        to_field_name="name",
        label="Rack (name or ID)",
    )

    class Meta:
        model = PowerFeed
        fields = [
            "id",
            "name",
            "status",
            "type",
            "power_path",
            "supply",
            "phase",
            "voltage",
            "amperage",
            "max_utilization",
            "breaker_position",
            "breaker_pole_count",
            "comments",
            "available_power",
            "tags",
        ]


class DeviceRedundancyGroupFilterSet(NautobotFilterSet, StatusModelFilterSetMixin, NameSearchFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "comments": "icontains"})
    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        to_field_name="name",
        label="Secrets group (name or ID)",
    )

    class Meta:
        model = DeviceRedundancyGroup
        fields = ["id", "name", "failover_strategy", "tags"]


class InterfaceRedundancyGroupFilterSet(NameSearchFilterSet, BaseFilterSet):
    """Filter for InterfaceRedundancyGroup."""

    q = SearchFilter(filter_predicates={"name": "icontains"})
    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="secrets_group",
        queryset=SecretsGroup.objects.all(),
        to_field_name="name",
        label="Secrets group",
    )
    virtual_ip = MultiValueCharFilter(
        method="filter_virtual_ip",
        label="Virtual IP Address (address or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = InterfaceRedundancyGroup
        fields = ["id", "name", "description", "secrets_group", "virtual_ip", "protocol", "protocol_group_id", "tags"]

    # 2.0 TODO(jathan): Eliminate these methods.
    def filter_virtual_ip(self, queryset, name, value):
        pk_values = set(item for item in value if is_uuid(item))
        addresses = set(item for item in value if item not in pk_values)

        ip_queryset = IPAddress.objects.filter_address_or_pk_in(addresses, pk_values)
        return queryset.filter(virtual_ip__in=ip_queryset)


class InterfaceRedundancyGroupAssociationFilterSet(BaseFilterSet):
    """Filter for InterfaceRedundancyGroupAssociation."""

    q = SearchFilter(
        filter_predicates={"interface_redundancy_group__name": "icontains", "interface__name": "icontains"}
    )

    interface_redundancy_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=InterfaceRedundancyGroup.objects.all(),
        to_field_name="name",
        label="Interface Redundancy Groups (name or ID)",
    )

    interface = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Interface (name or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = InterfaceRedundancyGroupAssociation

        fields = ["id", "interface_redundancy_group", "interface", "priority"]


class SoftwareImageFileFilterSet(NautobotFilterSet, StatusModelFilterSetMixin):
    """Filters for SoftwareImageFile model."""

    q = SearchFilter(
        filter_predicates={
            "image_file_name": "icontains",
            "software_version__version": "icontains",
            "software_version__alias": "icontains",
            "software_version__platform__name": "icontains",
        }
    )
    software_version = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareVersion.objects.all(),
        to_field_name="version",
        label="Software version (version or ID)",
    )
    device_types = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        label="Device types (model or ID)",
    )
    has_device_types = RelatedMembershipBooleanFilter(
        field_name="device_types",
        label="Has device types",
    )
    devices = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label="Devices (name or ID)",
    )
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has devices",
    )
    default_image = django_filters.BooleanFilter(
        label="Is default image for associated software version",
    )
    external_integration = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ExternalIntegration.objects.all(),
        to_field_name="name",
        label="External integration (name or ID)",
    )

    class Meta:
        model = SoftwareImageFile
        fields = "__all__"


class SoftwareVersionFilterSet(NautobotFilterSet, StatusModelFilterSetMixin):
    """Filters for SoftwareVersion model."""

    q = SearchFilter(
        filter_predicates={
            "version": "icontains",
            "alias": "icontains",
            "platform__name": "icontains",
        }
    )
    devices = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label="Devices (name or ID)",
    )
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has devices",
    )
    inventory_items = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=InventoryItem.objects.all(),
        label="Inventory items (name or ID)",
    )
    has_inventory_items = RelatedMembershipBooleanFilter(
        field_name="inventory_items",
        label="Has inventory items",
    )
    virtual_machines = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualMachine.objects.all(),
        label="Virtual machines (name or ID)",
    )
    has_virtual_machines = RelatedMembershipBooleanFilter(
        field_name="virtual_machines",
        label="Has virtual machines",
    )
    platform = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Platform.objects.all(),
        to_field_name="name",
        label="Platform (name or ID)",
    )
    device_types = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="software_image_files__device_types",
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        label="Device types (model or ID)",
    )
    has_software_image_files = RelatedMembershipBooleanFilter(
        field_name="software_image_files",
        label="Has software image files",
    )
    software_image_files = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareImageFile.objects.all(),
        to_field_name="image_file_name",
        label="Software image files (image file name or ID)",
    )

    class Meta:
        model = SoftwareVersion
        fields = "__all__"


class DeviceTypeToSoftwareImageFileFilterSet(BaseFilterSet):
    """Filters for DeviceTypeToSoftwareImageFile model."""

    q = SearchFilter(
        filter_predicates={
            "device_type__model": "icontains",
            "software_image_file__image_file_name": "icontains",
        }
    )

    device_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        label="Device type (model or ID)",
    )
    software_image_file = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareImageFile.objects.all(),
        to_field_name="image_file_name",
        label="Software image file (image file name or ID)",
    )

    class Meta:
        model = DeviceTypeToSoftwareImageFile
        fields = "__all__"


class ControllerFilterSet(
    NautobotFilterSet,
    LocatableModelFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    """Filters for Controller model."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        }
    )
    platform = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Platform.objects.all(),
        to_field_name="name",
        label="Platform (name or ID)",
    )
    external_integration = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ExternalIntegration.objects.all(),
        to_field_name="name",
        label="External integration (name or ID)",
    )
    capabilities = django_filters.MultipleChoiceFilter(
        choices=ControllerCapabilitiesChoices,
        null_value=None,
        lookup_expr="icontains",
        label="Capabilities",
    )
    controller_device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Controller device (name or ID)",
    )
    controller_device_redundancy_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceRedundancyGroup.objects.all(),
        to_field_name="name",
        label="Controller device redundancy group (name or ID)",
    )
    wireless_networks = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="controller_managed_device_groups__wireless_networks",
        queryset=WirelessNetwork.objects.all(),
        to_field_name="name",
        label="Wireless Networks (name or ID)",
    )

    class Meta:
        model = Controller
        fields = "__all__"


class ControllerManagedDeviceGroupFilterSet(
    NautobotFilterSet,
    TenancyModelFilterSetMixin,
):
    """Filters for ControllerManagedDeviceGroup model."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
        }
    )
    capabilities = django_filters.MultipleChoiceFilter(
        choices=ControllerCapabilitiesChoices,
        null_value=None,
        lookup_expr="icontains",
        label="Capabilities",
    )
    controller = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Controller.objects.all(),
        to_field_name="name",
        label="Controller (name or ID)",
    )
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ControllerManagedDeviceGroup.objects.all(),
        to_field_name="name",
        label="Parent group (name or ID)",
    )
    subtree = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Controller.objects.all(),
        to_field_name="name",
        label="Controlled device groups and descendants thereof (name or ID)",
        method="_subtree",
    )
    radio_profiles = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RadioProfile.objects.all(),
        label="Radio Profiles (name or ID)",
    )
    has_radio_profiles = RelatedMembershipBooleanFilter(
        field_name="radio_profiles",
        label="Has radio profiles",
    )
    wireless_networks = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=WirelessNetwork.objects.all(),
        label="Wireless Networks (name or ID)",
    )
    has_wireless_networks = RelatedMembershipBooleanFilter(
        field_name="wireless_networks",
        label="Has wireless networks",
    )

    class Meta:
        model = ControllerManagedDeviceGroup
        fields = "__all__"

    def generate_query__subtree(self, value):
        """Helper method used by DynamicGroups and by _subtree() method."""
        if value:
            params = Q(pk__in=[v.pk for v in value])
            filter_name = "in"
            for _ in range(ControllerManagedDeviceGroup.objects.max_depth + 1):
                filter_name = f"parent__{filter_name}"
                params |= Q(**{filter_name: value})
            return params
        return Q()

    @extend_schema_field({"type": "string"})
    def _subtree(self, queryset, name, value):
        """FilterSet method for getting Groups that are or are descended from a given ControllerManagedDeviceGroup(s)."""
        params = self.generate_query__subtree(value)
        return queryset.filter(params)


class ModuleFilterSet(
    NautobotFilterSet,
    DeviceModuleCommonFiltersMixin,
    LocatableModelFilterSetMixin,
    RoleModelFilterSetMixin,
    StatusModelFilterSetMixin,
    TenancyModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "asset_tag": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "serial": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "module_type__manufacturer__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "module_type__model": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "parent_module_bay__parent_device__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "parent_module_bay__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "parent_module_bay__position": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "parent_module_bay__parent_module__module_type__manufacturer__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    is_installed = RelatedMembershipBooleanFilter(
        field_name="parent_module_bay",
        label="Is installed in a module bay",
    )
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="module_type__manufacturer",
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
        label="Manufacturer (name or ID)",
    )
    module_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ModuleType.objects.all(),
        to_field_name="model",
        label="Module type (model or ID)",
    )
    module_family = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="module_type__module_family",
        queryset=ModuleFamily.objects.all(),
        to_field_name="name",
        label="Module family (name or ID)",
    )
    parent_module_bay = django_filters.ModelMultipleChoiceFilter(
        queryset=ModuleBay.objects.all(),
        label="Parent Module Bay",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
        method="filter_device",
    )
    compatible_with_module_bay = extend_schema_field({"type": "string", "format": "uuid"})(
        django_filters.ModelChoiceFilter(
            queryset=ModuleBay.objects.all(),
            method="filter_module_bay",
            label="Compatible with module bay (ID)",
        )
    )

    def _construct_device_filter_recursively(self, field_name, value):
        recursion_depth = MODULE_RECURSION_DEPTH_LIMIT
        query = Q()
        for level in range(recursion_depth):
            recursive_query = "parent_module_bay__parent_module__" * level
            query = query | Q(**{f"{recursive_query}parent_module_bay__parent_device__{field_name}__in": value})
        return query

    def generate_query_filter_device(self, value):
        if not hasattr(value, "__iter__") or isinstance(value, str):
            value = [value]

        device_ids = set(str(item) for item in value if is_uuid(item))
        device_names = set(str(item) for item in value if not is_uuid(item))
        query = self._construct_device_filter_recursively("name", device_names)
        query |= self._construct_device_filter_recursively("id", device_ids)
        return query

    def filter_device(self, queryset, name, value):
        if not value:
            return queryset
        params = self.generate_query_filter_device(value)
        return queryset.filter(params)

    def filter_module_bay(self, queryset, name, value):
        """Filter modules based on a module bay's module family."""
        if value and value.module_family:
            return queryset.filter(module_type__module_family=value.module_family)
        return queryset

    class Meta:
        model = Module
        fields = "__all__"


class ModuleTypeFilterSet(DeviceTypeModuleTypeCommonFiltersMixin, NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "manufacturer__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "model": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "part_number": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "comments": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        },
    )
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
        label="Manufacturer (name or ID)",
    )
    module_family = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ModuleFamily.objects.all(),
        to_field_name="name",
        label="Module family (name or ID)",
    )
    compatible_with_module_bay = extend_schema_field({"type": "string", "format": "uuid"})(
        django_filters.ModelChoiceFilter(
            queryset=ModuleBay.objects.all(),
            method="filter_module_bay",
            label="Installable in module bay (ID)",
        )
    )
    has_modules = RelatedMembershipBooleanFilter(
        field_name="modules",
        label="Has module instances",
    )

    class Meta:
        model = ModuleType
        fields = "__all__"

    def filter_module_bay(self, queryset, name, value):
        """Filter module types based on a module bay's module family."""
        if value and value.module_family:
            return queryset.filter(module_family=value.module_family)
        return queryset


class ModuleBayTemplateFilterSet(ModularDeviceComponentTemplateModelFilterSetMixin, NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "device_type__manufacturer__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "device_type__model": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "module_type__manufacturer__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "module_type__model": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "position": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    module_family = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ModuleFamily.objects.all(),
        to_field_name="name",
        label="Module family (name or ID)",
    )
    requires_first_party_modules = django_filters.BooleanFilter(
        label="Requires first-party modules",
    )

    class Meta:
        model = ModuleBayTemplate
        fields = "__all__"


class ModuleBayFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "device__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "parent_module__module_type__manufacturer__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "parent_module__module_type__model": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "position": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    parent_device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Parent device (name or ID)",
    )
    has_parent_device = RelatedMembershipBooleanFilter(
        field_name="parent_device",
        label="Has parent device",
    )
    parent_module = django_filters.ModelMultipleChoiceFilter(
        queryset=Module.objects.all(),
        label="Parent module (ID)",
    )
    has_parent_module = RelatedMembershipBooleanFilter(
        field_name="parent_module",
        label="Has parent module",
    )
    installed_module = django_filters.ModelMultipleChoiceFilter(
        queryset=Module.objects.all(),
        label="Installed module (ID)",
    )
    has_installed_module = RelatedMembershipBooleanFilter(
        field_name="installed_module",
        label="Has installed module",
    )
    module_family = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ModuleFamily.objects.all(),
        to_field_name="name",
        label="Module family (name or ID)",
    )
    requires_first_party_modules = django_filters.BooleanFilter(
        field_name="requires_first_party_modules",
        label="Requires first-party modules",
    )

    class Meta:
        model = ModuleBay
        fields = "__all__"


class VirtualDeviceContextFilterSet(
    NautobotFilterSet, TenancyModelFilterSetMixin, RoleModelFilterSetMixin, StatusModelFilterSetMixin
):
    q = SearchFilter(
        filter_predicates={
            "device__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "tenant__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    primary_ip4 = MultiValueCharFilter(
        method="filter_primary_ip4",
        label="Primary IPv4 Address (address or ID)",
    )
    primary_ip6 = MultiValueCharFilter(
        method="filter_primary_ip6",
        label="Primary IPv6 Address (address or ID)",
    )
    has_primary_ip = django_filters.BooleanFilter(
        method="_has_primary_ip",
        label="Has a primary IP",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
    )
    interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Interface (name or ID)",
    )
    has_interfaces = RelatedMembershipBooleanFilter(
        field_name="interfaces",
        label="Has Interfaces",
    )

    class Meta:
        model = VirtualDeviceContext
        fields = [
            "identifier",
            "name",
            "device",
            "tenant",
            "interfaces",
            "has_interfaces",
            "has_primary_ip",
            "primary_ip4",
            "primary_ip6",
            "role",
            "status",
            "tags",
            "description",
        ]

    # TODO(timizuo): Make a mixin for ip filterset fields to reduce code duplication
    # VirtualMachineFilterSet,
    def generate_query__has_primary_ip(self, value):
        query = Q(primary_ip4__isnull=False) | Q(primary_ip6__isnull=False)
        return ~query if not value else query

    def _has_primary_ip(self, queryset, name, value):
        params = self.generate_query__has_primary_ip(value)
        return queryset.filter(params)

    def get_ip_queryset(self, value):
        pk_values = {item for item in value if is_uuid(item)}
        addresses = {item for item in value if item not in pk_values}

        return IPAddress.objects.filter_address_or_pk_in(addresses, pk_values)

    def filter_primary_ip4(self, queryset, name, value):
        ip_queryset = self.get_ip_queryset(value)
        return queryset.filter(primary_ip4__in=ip_queryset)

    def filter_primary_ip6(self, queryset, name, value):
        ip_queryset = self.get_ip_queryset(value)
        return queryset.filter(primary_ip6__in=ip_queryset)


class InterfaceVDCAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "interface__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "virtual_device_context__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="interface__device",
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
    )
    virtual_device_context = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualDeviceContext.objects.all(),
        to_field_name="name",
        label="Virtual Device Context (name or ID)",
    )
    interface = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Interface (name or ID)",
    )

    class Meta:
        model = InterfaceVDCAssignment
        fields = [
            "device",
            "interface",
            "virtual_device_context",
        ]


class ModuleFamilyFilterSet(NautobotFilterSet):
    """FilterSet for ModuleFamily objects."""

    q = SearchFilter(
        filter_predicates={
            "name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "description": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "module_types__model": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "module_types__manufacturer__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )

    module_types = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ModuleType.objects.all(),
        to_field_name="model",
        label="Module types (model or ID)",
    )

    module_bay_id = extend_schema_field({"type": "array", "items": {"type": "string", "format": "uuid"}})(
        django_filters.ModelMultipleChoiceFilter(
            queryset=ModuleBay.objects.all(),
            label="Module bay (ID)",
        )
    )

    class Meta:
        model = ModuleFamily
        fields = [
            "id",
            "name",
            "description",
            "module_types",
            "module_bay_id",
            "tags",
        ]
