import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Q
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
    InterfaceTypeChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    RackTypeChoices,
    RackWidthChoices,
)
from nautobot.dcim.constants import NONCONNECTABLE_IFACE_TYPES, VIRTUAL_IFACE_TYPES, WIRELESS_IFACE_TYPES
from nautobot.dcim.filters.mixins import (
    CableTerminationModelFilterSetMixin,
    DeviceComponentModelFilterSetMixin,
    DeviceComponentTemplateModelFilterSetMixin,
    LocatableModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
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
    VirtualChassis,
)
from nautobot.extras.filters import (
    NautobotFilterSet,
    LocalContextModelFilterSetMixin,
    RoleModelFilterSetMixin,
    StatusModelFilterSetMixin,
)
from nautobot.extras.models import SecretsGroup
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.models import IPAddress, VLAN, VLANGroup
from nautobot.tenancy.filters import TenancyModelFilterSetMixin
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster


__all__ = (
    "CableFilterSet",
    "CableTerminationFilterSet",
    "CableTerminationModelFilterSetMixin",
    "ConsoleConnectionFilterSet",
    "ConsolePortFilterSet",
    "ConsolePortTemplateFilterSet",
    "ConsoleServerPortFilterSet",
    "ConsoleServerPortTemplateFilterSet",
    "DeviceBayFilterSet",
    "DeviceBayTemplateFilterSet",
    "DeviceFilterSet",
    "DeviceRedundancyGroupFilterSet",
    "DeviceTypeFilterSet",
    "FrontPortFilterSet",
    "FrontPortTemplateFilterSet",
    "InterfaceConnectionFilterSet",
    "InterfaceFilterSet",
    "InterfaceRedundancyGroupFilterSet",
    "InterfaceRedundancyGroupAssociationFilterSet",
    "InterfaceTemplateFilterSet",
    "InventoryItemFilterSet",
    "LocationFilterSet",
    "LocationTypeFilterSet",
    "ManufacturerFilterSet",
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
        params = self.generate_query__subtree(value)
        return queryset.filter(params)


class RackGroupFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin, NameSearchFilterSet):
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        to_field_name="name",
        label="Parent (name or ID)",
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


class RackReservationFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "rack__name": "icontains",
            "rack__facility_id": "icontains",
            "user__username": "icontains",
            "description": "icontains",
        },
    )
    rack_group = TreeNodeMultipleChoiceFilter(
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


class DeviceTypeFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "manufacturer__name": "icontains",
            "model": "icontains",
            "part_number": "icontains",
            "comments": "icontains",
        },
    )
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Manufacturer.objects.all(), to_field_name="name", label="Manufacturer (name or ID)"
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
    pass_through_ports = django_filters.BooleanFilter(
        method="_pass_through_ports",
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
    console_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=ConsolePortTemplate.objects.all(),
        label="Console port templates (name or ID)",
    )
    has_console_port_templates = RelatedMembershipBooleanFilter(
        field_name="console_port_templates",
        label="Has console port templates",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    console_server_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=ConsoleServerPortTemplate.objects.all(),
        label="Console server port templates (name or ID)",
    )
    has_console_server_port_templates = RelatedMembershipBooleanFilter(
        field_name="console_server_port_templates",
        label="Has console server port templates",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=PowerPortTemplate.objects.all(),
        label="Power port templates (name or ID)",
    )
    has_power_port_templates = RelatedMembershipBooleanFilter(
        field_name="power_port_templates",
        label="Has power port templates",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_outlet_templates = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=PowerOutletTemplate.objects.all(),
        label="Power outlet templates (name or ID)",
    )
    has_power_outlet_templates = RelatedMembershipBooleanFilter(
        field_name="power_outlet_templates",
        label="Has power outlet templates",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    interface_templates = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=InterfaceTemplate.objects.all(),
        label="Interface templates (name or ID)",
    )
    has_interface_templates = RelatedMembershipBooleanFilter(
        field_name="interface_templates",
        label="Has interface templates",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    front_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=FrontPortTemplate.objects.all(),
        label="Front port templates (name or ID)",
    )
    has_front_port_templates = RelatedMembershipBooleanFilter(
        field_name="front_port_templates",
        label="Has front port templates",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    rear_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=RearPortTemplate.objects.all(),
        label="Rear port templates (name or ID)",
    )
    has_rear_port_templates = RelatedMembershipBooleanFilter(
        field_name="rear_port_templates",
        label="Has rear port templates",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    device_bay_templates = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=DeviceBayTemplate.objects.all(),
        label="Device bay templates (name or ID)",
    )
    has_device_bay_templates = RelatedMembershipBooleanFilter(
        field_name="device_bay_templates",
        label="Has device bay templates",
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

    def _pass_through_ports(self, queryset, name, value):
        return queryset.exclude(front_port_templates__isnull=value, rear_port_templates__isnull=value)

    def _device_bays(self, queryset, name, value):
        return queryset.exclude(device_bay_templates__isnull=value)


# TODO: remove in 2.2
@class_deprecated_in_favor_of(DeviceComponentTemplateModelFilterSetMixin)
class DeviceTypeComponentFilterSet(DeviceComponentTemplateModelFilterSetMixin):
    pass


class ConsolePortTemplateFilterSet(BaseFilterSet, DeviceComponentTemplateModelFilterSetMixin):
    class Meta:
        model = ConsolePortTemplate
        fields = ["type"]


class ConsoleServerPortTemplateFilterSet(BaseFilterSet, DeviceComponentTemplateModelFilterSetMixin):
    class Meta:
        model = ConsoleServerPortTemplate
        fields = ["type"]


class PowerPortTemplateFilterSet(BaseFilterSet, DeviceComponentTemplateModelFilterSetMixin):
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_outlet_templates = NaturalKeyOrPKMultipleChoiceFilter(
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


class PowerOutletTemplateFilterSet(BaseFilterSet, DeviceComponentTemplateModelFilterSetMixin):
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_port_template = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=PowerPortTemplate.objects.all(),
        label="Power port template (name or ID)",
    )

    class Meta:
        model = PowerOutletTemplate
        fields = ["type", "feed_leg"]


class InterfaceTemplateFilterSet(BaseFilterSet, DeviceComponentTemplateModelFilterSetMixin):
    class Meta:
        model = InterfaceTemplate
        fields = ["type", "mgmt_only"]


class FrontPortTemplateFilterSet(BaseFilterSet, DeviceComponentTemplateModelFilterSetMixin):
    rear_port_template = django_filters.ModelMultipleChoiceFilter(
        queryset=RearPortTemplate.objects.all(),
        label="Rear port template",
    )

    class Meta:
        model = FrontPortTemplate
        fields = ["type", "rear_port_position"]


class RearPortTemplateFilterSet(BaseFilterSet, DeviceComponentTemplateModelFilterSetMixin):
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


class DeviceBayTemplateFilterSet(BaseFilterSet, DeviceComponentTemplateModelFilterSetMixin):
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
            "comments": "icontains",
        },
    )
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_type__manufacturer",
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
        label="Manufacturer (name or ID)",
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
        queryset=RackGroup.objects.all(),
        field_name="rack__rack_group",
        to_field_name="name",
        label="Rack group (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    rack = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Rack.objects.all(),
        to_field_name="name",
        label="Rack (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    cluster = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        to_field_name="name",
        label="VM cluster (name or ID)",
    )
    is_full_depth = django_filters.BooleanFilter(
        field_name="device_type__is_full_depth",
        label="Is full depth",
    )
    mac_address = MultiValueMACAddressFilter(
        field_name="interfaces__mac_address",
        label="MAC address",
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
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
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
    virtual_chassis_member = is_virtual_chassis_member
    has_console_ports = RelatedMembershipBooleanFilter(
        field_name="console_ports",
        label="Has console ports",
    )
    console_ports = django_filters.ModelMultipleChoiceFilter(
        queryset=ConsolePort.objects.all(),
        label="Console Ports",
    )
    has_console_server_ports = RelatedMembershipBooleanFilter(
        field_name="console_server_ports",
        label="Has console server ports",
    )
    console_server_ports = django_filters.ModelMultipleChoiceFilter(
        queryset=ConsoleServerPort.objects.all(),
        label="Console Server Ports",
    )
    has_power_ports = RelatedMembershipBooleanFilter(
        field_name="power_ports",
        label="Has power ports",
    )
    power_ports = django_filters.ModelMultipleChoiceFilter(
        queryset=PowerPort.objects.all(),
        label="Power Ports",
    )
    has_power_outlets = RelatedMembershipBooleanFilter(
        field_name="power_outlets",
        label="Has power outlets",
    )
    power_outlets = django_filters.ModelMultipleChoiceFilter(
        queryset=PowerOutlet.objects.all(),
        label="Power Outlets",
    )
    has_interfaces = RelatedMembershipBooleanFilter(
        field_name="interfaces",
        label="Has interfaces",
    )
    has_front_ports = RelatedMembershipBooleanFilter(
        field_name="front_ports",
        label="Has front ports",
    )
    front_ports = django_filters.ModelMultipleChoiceFilter(
        queryset=FrontPort.objects.all(),
        label="Front Port",
    )
    has_rear_ports = RelatedMembershipBooleanFilter(
        field_name="rear_ports",
        label="Has rear ports",
    )
    rear_ports = django_filters.ModelMultipleChoiceFilter(
        queryset=RearPort.objects.all(),
        label="Rear Port",
    )
    has_device_bays = RelatedMembershipBooleanFilter(
        field_name="device_bays",
        label="Has device bays",
    )
    device_bays = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceBay.objects.all(),
        label="Device Bays",
    )

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
    BaseFilterSet,
    DeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
):
    type = django_filters.MultipleChoiceFilter(choices=ConsolePortTypeChoices, null_value=None)

    class Meta:
        model = ConsolePort
        fields = ["id", "name", "description", "label", "tags"]


class ConsoleServerPortFilterSet(
    BaseFilterSet,
    DeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
):
    type = django_filters.MultipleChoiceFilter(choices=ConsolePortTypeChoices, null_value=None)

    class Meta:
        model = ConsoleServerPort
        fields = ["id", "name", "description", "label", "tags"]


class PowerPortFilterSet(
    BaseFilterSet,
    DeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
):
    type = django_filters.MultipleChoiceFilter(choices=PowerPortTypeChoices, null_value=None)
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_outlets = NaturalKeyOrPKMultipleChoiceFilter(
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
    BaseFilterSet,
    DeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
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
    DeviceComponentModelFilterSetMixin,
    CableTerminationModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
    StatusModelFilterSetMixin,
):
    # Override device and device_id filters from DeviceComponentModelFilterSetMixin to
    # match against any peer virtual chassis members
    device = MultiValueCharFilter(
        method="filter_device",
        field_name="name",
        label="Device (name)",
    )
    device_id = MultiValueUUIDFilter(
        method="filter_device_id",
        field_name="pk",
        label="Device (ID)",
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
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Parent interface (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    bridge = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Bridge interface (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    lag = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Interface.objects.filter(type=InterfaceTypeChoices.TYPE_LAG),
        label="LAG interface (name or ID)",
    )
    untagged_vlan = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="vid",
        queryset=VLAN.objects.all(),
        label="Untagged VLAN (VID or ID)",
    )
    tagged_vlans = NaturalKeyOrPKMultipleChoiceFilter(
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
            "interface_redundancy_groups",
        ]

    def filter_device(self, queryset, name, value):
        try:
            devices = Device.objects.filter(**{f"{name}__in": value})
            vc_interface_ids = []
            for device in devices:
                vc_interface_ids.extend(device.vc_interfaces.values_list("id", flat=True))
            return queryset.filter(pk__in=vc_interface_ids)
        except Device.DoesNotExist:
            return queryset.none()

    def filter_device_id(self, queryset, name, id_list):
        # Include interfaces belonging to peer virtual chassis members
        vc_interface_ids = []
        try:
            devices = Device.objects.filter(pk__in=id_list)
            for device in devices:
                vc_interface_ids += device.vc_interfaces.values_list("id", flat=True)
            return queryset.filter(pk__in=vc_interface_ids)
        except Device.DoesNotExist:
            return queryset.none()

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


class FrontPortFilterSet(BaseFilterSet, DeviceComponentModelFilterSetMixin, CableTerminationModelFilterSetMixin):
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    rear_port = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=RearPort.objects.all(),
        label="Rear port (name or ID)",
    )

    class Meta:
        model = FrontPort
        fields = ["id", "name", "type", "description", "label", "rear_port_position", "tags"]


class RearPortFilterSet(BaseFilterSet, DeviceComponentModelFilterSetMixin, CableTerminationModelFilterSetMixin):
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


class DeviceBayFilterSet(BaseFilterSet, DeviceComponentModelFilterSetMixin):
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    installed_device = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="installed_device",
        to_field_name="name",
        queryset=Device.objects.all(),
        label="Installed device (name or ID)",
    )

    class Meta:
        model = DeviceBay
        fields = ["id", "name", "description", "label", "tags"]


class InventoryItemFilterSet(BaseFilterSet, DeviceComponentModelFilterSetMixin):
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
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    parent = NaturalKeyOrPKMultipleChoiceFilter(
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
        queryset=InventoryItem.objects.all(),
        to_field_name="name",
        label="Child items (name or ID)",
    )
    has_children = RelatedMembershipBooleanFilter(
        field_name="children",
        label="Has child items",
    )
    serial = MultiValueCharFilter(lookup_expr="iexact")

    class Meta:
        model = InventoryItem
        fields = ["id", "name", "part_id", "asset_tag", "discovered", "description", "label", "tags"]


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
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Master (name or ID)",
    )
    location = NaturalKeyOrPKMultipleChoiceFilter(
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
    device_id = MultiValueUUIDFilter(method="filter_device", label="Device (ID)")
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


class PowerPanelFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin):
    q = SearchFilter(filter_predicates={"name": "icontains"})
    rack_group = TreeNodeMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        to_field_name="name",
        label="Rack group (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_feeds = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=PowerFeed.objects.all(),
        label="Power feeds (name or ID)",
    )
    has_power_feeds = RelatedMembershipBooleanFilter(
        field_name="power_feeds",
        label="Has power feeds",
    )

    class Meta:
        model = PowerPanel
        fields = ["id", "name", "tags"]


class PowerFeedFilterSet(
    NautobotFilterSet, CableTerminationModelFilterSetMixin, PathEndpointModelFilterSetMixin, StatusModelFilterSetMixin
):
    q = SearchFilter(filter_predicates={"name": "icontains", "comments": "icontains"})
    location = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="power_panel__location",
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    power_panel = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=PowerPanel.objects.all(),
        to_field_name="name",
        label="Power panel (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    rack = NaturalKeyOrPKMultipleChoiceFilter(
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
            "supply",
            "phase",
            "voltage",
            "amperage",
            "max_utilization",
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


class InterfaceRedundancyGroupFilterSet(BaseFilterSet, NameSearchFilterSet):
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


class InterfaceRedundancyGroupAssociationFilterSet(BaseFilterSet, NameSearchFilterSet):
    """Filter for InterfaceRedundancyGroupAssociation."""

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
