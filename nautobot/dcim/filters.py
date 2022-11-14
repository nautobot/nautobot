import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.utils import extend_schema_field
from timezone_field import TimeZoneField

from nautobot.dcim.filter_mixins import LocatableModelFilterSetMixin
from nautobot.extras.filters import (
    CustomFieldModelFilterSet,
    LocalContextFilterSet,
    NautobotFilterSet,
    StatusModelFilterSetMixin,
)
from nautobot.extras.models import SecretsGroup
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.models import VLAN, VLANGroup
from nautobot.tenancy.filters import TenancyFilterSet
from nautobot.tenancy.models import Tenant
from nautobot.utilities.filters import (
    BaseFilterSet,
    ContentTypeMultipleChoiceFilter,
    MultiValueCharFilter,
    MultiValueMACAddressFilter,
    MultiValueUUIDFilter,
    NameSlugSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.virtualization.models import Cluster
from .choices import (
    CableTypeChoices,
    ConsolePortTypeChoices,
    InterfaceTypeChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    RackTypeChoices,
    RackWidthChoices,
)
from .constants import NONCONNECTABLE_IFACE_TYPES, VIRTUAL_IFACE_TYPES, WIRELESS_IFACE_TYPES
from .models import (
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
    PowerOutlet,
    PowerOutletTemplate,
    PowerPanel,
    PowerPort,
    PowerPortTemplate,
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


__all__ = (
    "CableFilterSet",
    "CableTerminationFilterSet",
    "ConsoleConnectionFilterSet",
    "ConsolePortFilterSet",
    "ConsolePortTemplateFilterSet",
    "ConsoleServerPortFilterSet",
    "ConsoleServerPortTemplateFilterSet",
    "DeviceBayFilterSet",
    "DeviceBayTemplateFilterSet",
    "DeviceFilterSet",
    "DeviceRedundancyGroupFilterSet",
    "DeviceRoleFilterSet",
    "DeviceTypeFilterSet",
    "FrontPortFilterSet",
    "FrontPortTemplateFilterSet",
    "InterfaceConnectionFilterSet",
    "InterfaceFilterSet",
    "InterfaceTemplateFilterSet",
    "InventoryItemFilterSet",
    "LocationFilterSet",
    "LocationTypeFilterSet",
    "ManufacturerFilterSet",
    "PathEndpointFilterSet",
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
    "RackRoleFilterSet",
    "RearPortFilterSet",
    "RearPortTemplateFilterSet",
    "RegionFilterSet",
    "SiteFilterSet",
    "VirtualChassisFilterSet",
)


class RegionFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    parent_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Region.objects.all(),
        label="Parent region (ID)",
    )
    parent = django_filters.ModelMultipleChoiceFilter(
        field_name="parent__slug",
        queryset=Region.objects.all(),
        to_field_name="slug",
        label="Parent region (slug)",
    )
    children = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Region.objects.all(),
        label="Children (slug or ID)",
    )
    has_children = RelatedMembershipBooleanFilter(
        field_name="children",
        label="Has children",
    )
    sites = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Sites (slug or ID)",
    )
    has_sites = RelatedMembershipBooleanFilter(
        field_name="sites",
        label="Has sites",
    )

    class Meta:
        model = Region
        fields = ["id", "name", "slug", "description"]


class SiteFilterSet(NautobotFilterSet, TenancyFilterSet, StatusModelFilterSetMixin):
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
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="region",
        label="Region (slug)",
    )
    locations = TreeNodeMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Locations within this Site (slugs or IDs)",
    )
    has_locations = RelatedMembershipBooleanFilter(
        field_name="locations",
        label="Has locations",
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
    # The reverse relation here is misnamed as `powerpanel`, but fixing it would be a breaking API change.
    # 2.0 TODO: fix the reverse relation name, at which point this filter can be deleted here and added to Meta.fields.
    power_panels = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="powerpanel",
        to_field_name="name",
        queryset=PowerPanel.objects.all(),
        label="Power panels (name or ID)",
    )
    has_power_panels = RelatedMembershipBooleanFilter(
        field_name="powerpanel",
        label="Has power panels",
    )
    rack_groups = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        label="Rack groups (slug or ID)",
    )
    has_rack_groups = RelatedMembershipBooleanFilter(
        field_name="rack_groups",
        label="Has rack groups",
    )
    has_racks = RelatedMembershipBooleanFilter(
        field_name="racks",
        label="Has racks",
    )
    has_prefixes = RelatedMembershipBooleanFilter(
        field_name="prefixes",
        label="Has prefixes",
    )
    vlan_groups = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VLANGroup.objects.all(),
        label="Vlan groups (slug or ID)",
    )
    has_vlan_groups = RelatedMembershipBooleanFilter(
        field_name="vlan_groups",
        label="Has vlan groups",
    )
    has_vlans = RelatedMembershipBooleanFilter(
        field_name="vlans",
        label="Has vlans",
    )
    has_clusters = RelatedMembershipBooleanFilter(
        field_name="clusters",
        label="Has clusters",
    )
    time_zone = django_filters.MultipleChoiceFilter(
        choices=[(str(obj), name) for obj, name in TimeZoneField().choices],
        label="Time zone",
        null_value="",
    )
    tag = TagFilter()

    class Meta:
        model = Site
        fields = [
            "asn",
            "circuit_terminations",
            "clusters",
            "comments",
            "contact_email",
            "contact_name",
            "contact_phone",
            "description",
            "facility",
            "id",
            "latitude",
            "longitude",
            "name",
            "physical_address",
            "prefixes",
            "racks",
            "shipping_address",
            "slug",
            "vlans",
        ]


class LocationTypeFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=LocationType.objects.all(),
        label="Parent location type (slug or ID)",
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("locations").get_choices,
    )

    class Meta:
        model = LocationType
        fields = ["id", "name", "slug", "description", "nestable"]


class LocationFilterSet(NautobotFilterSet, StatusModelFilterSetMixin, TenancyFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )
    location_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=LocationType.objects.all(),
        label="Location type (slug or ID)",
    )
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Parent location (slug or ID)",
    )
    subtree = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Location(s) and descendants thereof (slug or ID)",
        method="_subtree",
    )
    child_location_type = NaturalKeyOrPKMultipleChoiceFilter(
        method="_child_location_type",
        queryset=LocationType.objects.all(),
        label="Child location type (slug or ID)",
    )
    site = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Site (slug or ID)",
    )
    base_site = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Base location's site (slug or ID)",
        method="_base_site",
    )
    content_type = ContentTypeMultipleChoiceFilter(
        field_name="location_type__content_types",
        choices=FeatureQuery("locations").get_choices,
    )
    tag = TagFilter()

    class Meta:
        model = Location
        fields = ["id", "name", "slug", "description"]

    def generate_query__base_site(self, value):
        """Helper method used by DynamicGroups and by _base_site() method."""
        if value:
            max_depth = Location.objects.with_tree_fields().extra(order_by=["-__tree.tree_depth"]).first().tree_depth
            filter_name = "site__in"
            params = Q(**{filter_name: value})
            for _i in range(max_depth):
                filter_name = f"parent__{filter_name}"
                params |= Q(**{filter_name: value})
            return params
        return Q()

    @extend_schema_field({"type": "string"})
    def _base_site(self, queryset, name, value):
        """FilterSet method for getting Locations that are assigned to a given Site(s) or descended from one that is."""
        params = self.generate_query__base_site(value)
        return queryset.filter(params)

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


class RackGroupFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin, NameSlugSearchFilterSet):
    parent_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        label="Parent (ID)",
    )
    parent = django_filters.ModelMultipleChoiceFilter(
        field_name="parent__slug",
        queryset=RackGroup.objects.all(),
        to_field_name="slug",
        label="Parent (slug)",
    )
    children = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        label="Children (slug or ID)",
    )
    has_children = RelatedMembershipBooleanFilter(
        field_name="children",
        label="Has children",
    )
    power_panels = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="powerpanel",
        to_field_name="name",
        queryset=PowerPanel.objects.all(),
        label="Power panels (name or ID)",
    )
    has_power_panels = RelatedMembershipBooleanFilter(
        field_name="powerpanel",
        label="Has power panels",
    )
    has_racks = RelatedMembershipBooleanFilter(
        field_name="racks",
        label="Has racks",
    )

    class Meta:
        model = RackGroup
        fields = ["id", "name", "slug", "description", "racks"]


class RackRoleFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    has_racks = RelatedMembershipBooleanFilter(
        field_name="racks",
        label="Has racks",
    )

    class Meta:
        model = RackRole
        fields = ["id", "name", "slug", "color", "description", "racks"]


class RackFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin, TenancyFilterSet, StatusModelFilterSetMixin):
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
    group_id = TreeNodeMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        field_name="group",
        label="Rack group (ID)",
    )
    group = TreeNodeMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        field_name="group",
        label="Rack group (slug)",
    )
    type = django_filters.MultipleChoiceFilter(choices=RackTypeChoices)
    width = django_filters.MultipleChoiceFilter(choices=RackWidthChoices)
    role_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RackRole.objects.all(),
        label="Role (ID)",
    )
    role = django_filters.ModelMultipleChoiceFilter(
        field_name="role__slug",
        queryset=RackRole.objects.all(),
        to_field_name="slug",
        label="Role (slug)",
    )
    serial = django_filters.CharFilter(lookup_expr="iexact")
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has devices",
    )
    # The reverse relation here is misnamed as `powerfeed`, but fixing it would be a breaking API change.
    # 2.0 TODO: fix the reverse relation name, at which point this filter can be deleted here and added to Meta.fields.
    power_feeds = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="powerfeed",
        to_field_name="name",
        queryset=PowerFeed.objects.all(),
        label="Power feeds (name or ID)",
    )
    has_power_feeds = RelatedMembershipBooleanFilter(
        field_name="powerfeed",
        label="Has power feeds",
    )
    has_reservations = RelatedMembershipBooleanFilter(
        field_name="reservations",
        label="Has reservations",
    )
    tag = TagFilter()

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
            "reservations",
        ]


class RackReservationFilterSet(NautobotFilterSet, TenancyFilterSet):
    q = SearchFilter(
        filter_predicates={
            "rack__name": "icontains",
            "rack__facility_id": "icontains",
            "user__username": "icontains",
            "description": "icontains",
        },
    )
    rack_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Rack.objects.all(),
        label="Rack (ID)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="rack__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="rack__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )
    group_id = TreeNodeMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        field_name="rack__group",
        label="Rack group (ID)",
    )
    group = TreeNodeMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        field_name="rack__group",
        label="Rack group (slug)",
    )
    user_id = django_filters.ModelMultipleChoiceFilter(
        queryset=get_user_model().objects.all(),
        label="User (ID)",
    )
    user = django_filters.ModelMultipleChoiceFilter(
        field_name="user__username",
        queryset=get_user_model().objects.all(),
        to_field_name="username",
        label="User (name)",
    )
    rack = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Rack.objects.all(),
        to_field_name="name",
        label="Rack (name or ID)",
    )
    tag = TagFilter()

    class Meta:
        model = RackReservation
        fields = ["id", "created", "description"]


class ManufacturerFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
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
        label="Device types (slug or ID)",
    )
    has_device_types = RelatedMembershipBooleanFilter(
        field_name="device_types",
        label="Has device types",
    )
    platforms = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Platform.objects.all(),
        label="Platforms (slug or ID)",
    )
    has_platforms = RelatedMembershipBooleanFilter(
        field_name="platforms",
        label="Has platforms",
    )

    class Meta:
        model = Manufacturer
        fields = ["id", "name", "slug", "description"]


class DeviceTypeFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "manufacturer__name": "icontains",
            "model": "icontains",
            "part_number": "icontains",
            "comments": "icontains",
        },
    )
    manufacturer_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Manufacturer.objects.all(),
        label="Manufacturer (ID)",
    )
    manufacturer = django_filters.ModelMultipleChoiceFilter(
        field_name="manufacturer__slug",
        queryset=Manufacturer.objects.all(),
        to_field_name="slug",
        label="Manufacturer (slug)",
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
    has_instances = RelatedMembershipBooleanFilter(
        field_name="instances",
        label="Has instances",
    )
    console_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="consoleporttemplates",
        to_field_name="name",
        queryset=ConsolePortTemplate.objects.all(),
        label="Console port templates (name or ID)",
    )
    has_console_port_templates = RelatedMembershipBooleanFilter(
        field_name="consoleporttemplates",
        label="Has console port templates",
    )
    console_server_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="consoleserverporttemplates",
        to_field_name="name",
        queryset=ConsoleServerPortTemplate.objects.all(),
        label="Console server port templates (name or ID)",
    )
    has_console_server_port_templates = RelatedMembershipBooleanFilter(
        field_name="consoleserverporttemplates",
        label="Has console server port templates",
    )
    power_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="powerporttemplates",
        to_field_name="name",
        queryset=PowerPortTemplate.objects.all(),
        label="Power port templates (name or ID)",
    )
    has_power_port_templates = RelatedMembershipBooleanFilter(
        field_name="powerporttemplates",
        label="Has power port templates",
    )
    power_outlet_templates = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="poweroutlettemplates",
        to_field_name="name",
        queryset=PowerOutletTemplate.objects.all(),
        label="Power outlet templates (name or ID)",
    )
    has_power_outlet_templates = RelatedMembershipBooleanFilter(
        field_name="poweroutlettemplates",
        label="Has power outlet templates",
    )
    interface_templates = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="interfacetemplates",
        to_field_name="name",
        queryset=InterfaceTemplate.objects.all(),
        label="Interface templates (name or ID)",
    )
    has_interface_templates = RelatedMembershipBooleanFilter(
        field_name="interfacetemplates",
        label="Has interface templates",
    )
    front_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="frontporttemplates",
        to_field_name="name",
        queryset=FrontPortTemplate.objects.all(),
        label="Front port templates (name or ID)",
    )
    has_front_port_templates = RelatedMembershipBooleanFilter(
        field_name="frontporttemplates",
        label="Has front port templates",
    )
    rear_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="rearporttemplates",
        to_field_name="name",
        queryset=RearPortTemplate.objects.all(),
        label="Rear port templates (name or ID)",
    )
    has_rear_port_templates = RelatedMembershipBooleanFilter(
        field_name="rearporttemplates",
        label="Has rear port templates",
    )
    device_bay_templates = django_filters.ModelMultipleChoiceFilter(
        field_name="devicebaytemplates",
        queryset=DeviceBayTemplate.objects.all(),
        label="Device bay templates",
    )
    has_device_bay_templates = RelatedMembershipBooleanFilter(
        field_name="devicebaytemplates",
        label="Has device bay templates",
    )
    tag = TagFilter()

    class Meta:
        model = DeviceType
        fields = [
            "id",
            "model",
            "slug",
            "part_number",
            "u_height",
            "is_full_depth",
            "subdevice_role",
            "comments",
            "instances",
        ]

    def _console_ports(self, queryset, name, value):
        return queryset.exclude(consoleporttemplates__isnull=value)

    def _console_server_ports(self, queryset, name, value):
        return queryset.exclude(consoleserverporttemplates__isnull=value)

    def _power_ports(self, queryset, name, value):
        return queryset.exclude(powerporttemplates__isnull=value)

    def _power_outlets(self, queryset, name, value):
        return queryset.exclude(poweroutlettemplates__isnull=value)

    def _interfaces(self, queryset, name, value):
        return queryset.exclude(interfacetemplates__isnull=value)

    def _pass_through_ports(self, queryset, name, value):
        return queryset.exclude(frontporttemplates__isnull=value, rearporttemplates__isnull=value)

    def _device_bays(self, queryset, name, value):
        return queryset.exclude(devicebaytemplates__isnull=value)


# TODO: should be DeviceTypeComponentFilterSetMixin
class DeviceTypeComponentFilterSet(NameSlugSearchFilterSet, CustomFieldModelFilterSet):
    devicetype_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        field_name="device_type_id",
        label="Device type (ID)",
    )
    device_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        label="Device type (slug or ID)",
    )
    label = MultiValueCharFilter(label="Label")
    description = MultiValueCharFilter(label="Description")
    id = MultiValueUUIDFilter(label="ID")
    name = MultiValueCharFilter(label="Name")


class ConsolePortTemplateFilterSet(BaseFilterSet, DeviceTypeComponentFilterSet):
    class Meta:
        model = ConsolePortTemplate
        fields = ["type"]


class ConsoleServerPortTemplateFilterSet(BaseFilterSet, DeviceTypeComponentFilterSet):
    class Meta:
        model = ConsoleServerPortTemplate
        fields = ["type"]


class PowerPortTemplateFilterSet(BaseFilterSet, DeviceTypeComponentFilterSet):
    power_outlet_templates = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="poweroutlet_templates",
        to_field_name="name",
        queryset=PowerOutletTemplate.objects.all(),
        label="Power outlet templates (name or ID)",
    )
    has_power_outlet_templates = RelatedMembershipBooleanFilter(
        field_name="poweroutlet_templates",
        label="Has power outlet templates",
    )

    class Meta:
        model = PowerPortTemplate
        fields = [
            "type",
            "maximum_draw",
            "allocated_draw",
        ]


class PowerOutletTemplateFilterSet(BaseFilterSet, DeviceTypeComponentFilterSet):
    power_port_template = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="power_port",
        to_field_name="name",
        queryset=PowerPortTemplate.objects.all(),
        label="Power port template (name or ID)",
    )

    class Meta:
        model = PowerOutletTemplate
        fields = ["type", "feed_leg"]


class InterfaceTemplateFilterSet(BaseFilterSet, DeviceTypeComponentFilterSet):
    class Meta:
        model = InterfaceTemplate
        fields = ["type", "mgmt_only"]


class FrontPortTemplateFilterSet(BaseFilterSet, DeviceTypeComponentFilterSet):
    rear_port_template = django_filters.ModelMultipleChoiceFilter(
        field_name="rear_port",
        queryset=RearPortTemplate.objects.all(),
        label="Rear port template",
    )

    class Meta:
        model = FrontPortTemplate
        fields = ["type", "rear_port_position"]


class RearPortTemplateFilterSet(BaseFilterSet, DeviceTypeComponentFilterSet):
    front_port_templates = django_filters.ModelMultipleChoiceFilter(
        field_name="frontport_templates",
        queryset=FrontPortTemplate.objects.all(),
        label="Front port templates",
    )
    has_front_port_templates = RelatedMembershipBooleanFilter(
        field_name="frontport_templates",
        label="Has front port templates",
    )

    class Meta:
        model = RearPortTemplate
        fields = ["type", "positions"]


class DeviceBayTemplateFilterSet(BaseFilterSet, DeviceTypeComponentFilterSet):
    class Meta:
        model = DeviceBayTemplate
        fields = []


class DeviceRoleFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has devices",
    )
    has_virtual_machines = RelatedMembershipBooleanFilter(
        field_name="virtual_machines",
        label="Has virtual machines",
    )

    class Meta:
        model = DeviceRole
        fields = ["id", "name", "slug", "color", "vm_role", "description", "devices", "virtual_machines"]


class PlatformFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    manufacturer_id = django_filters.ModelMultipleChoiceFilter(
        field_name="manufacturer",
        queryset=Manufacturer.objects.all(),
        label="Manufacturer (ID)",
    )
    manufacturer = django_filters.ModelMultipleChoiceFilter(
        field_name="manufacturer__slug",
        queryset=Manufacturer.objects.all(),
        to_field_name="slug",
        label="Manufacturer (slug)",
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
            "slug",
            "napalm_driver",
            "description",
            "napalm_args",
            "devices",
            "virtual_machines",
        ]


class DeviceFilterSet(
    NautobotFilterSet,
    LocatableModelFilterSetMixin,
    TenancyFilterSet,
    LocalContextFilterSet,
    StatusModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "serial": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "inventoryitems__serial": {
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
    manufacturer_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device_type__manufacturer",
        queryset=Manufacturer.objects.all(),
        label="Manufacturer (ID)",
    )
    manufacturer = django_filters.ModelMultipleChoiceFilter(
        field_name="device_type__manufacturer__slug",
        queryset=Manufacturer.objects.all(),
        to_field_name="slug",
        label="Manufacturer (slug)",
    )
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        label="Device type (ID)",
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device_role_id",
        queryset=DeviceRole.objects.all(),
        label="Role (ID)",
    )
    role = django_filters.ModelMultipleChoiceFilter(
        field_name="device_role__slug",
        queryset=DeviceRole.objects.all(),
        to_field_name="slug",
        label="Role (slug)",
    )
    platform_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Platform.objects.all(),
        label="Platform (ID)",
    )
    platform = django_filters.ModelMultipleChoiceFilter(
        field_name="platform__slug",
        queryset=Platform.objects.all(),
        to_field_name="slug",
        label="Platform (slug)",
    )
    rack_group_id = TreeNodeMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        field_name="rack__group",
        label="Rack group (ID)",
    )
    rack_id = django_filters.ModelMultipleChoiceFilter(
        field_name="rack",
        queryset=Rack.objects.all(),
        label="Rack (ID)",
    )
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        label="VM cluster (ID)",
    )
    model = django_filters.ModelMultipleChoiceFilter(
        field_name="device_type__slug",
        queryset=DeviceType.objects.all(),
        to_field_name="slug",
        label="Device model (slug)",
    )
    is_full_depth = django_filters.BooleanFilter(
        field_name="device_type__is_full_depth",
        label="Is full depth",
    )
    mac_address = MultiValueMACAddressFilter(
        field_name="interfaces__mac_address",
        label="MAC address",
    )
    serial = django_filters.CharFilter(lookup_expr="iexact")
    has_primary_ip = django_filters.BooleanFilter(
        method="_has_primary_ip",
        label="Has a primary IP",
    )
    secrets_group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="secrets_group",
        queryset=SecretsGroup.objects.all(),
        label="Secrets group (ID)",
    )
    secrets_group = django_filters.ModelMultipleChoiceFilter(
        field_name="secrets_group__slug",
        queryset=SecretsGroup.objects.all(),
        to_field_name="slug",
        label="Secrets group (slug)",
    )
    virtual_chassis_id = django_filters.ModelMultipleChoiceFilter(
        field_name="virtual_chassis",
        queryset=VirtualChassis.objects.all(),
        label="Virtual chassis (ID)",
    )
    is_virtual_chassis_member = RelatedMembershipBooleanFilter(
        field_name="virtual_chassis",
        label="Is a virtual chassis member",
    )
    device_redundancy_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_redundancy_group",
        queryset=DeviceRedundancyGroup.objects.all(),
        label="Device Redundancy Groups (slug or ID)",
    )
    virtual_chassis_member = is_virtual_chassis_member
    has_console_ports = RelatedMembershipBooleanFilter(
        field_name="consoleports",
        label="Has console ports",
    )
    console_ports = has_console_ports
    has_console_server_ports = RelatedMembershipBooleanFilter(
        field_name="consoleserverports",
        label="Has console server ports",
    )
    console_server_ports = has_console_server_ports
    has_power_ports = RelatedMembershipBooleanFilter(
        field_name="powerports",
        label="Has power ports",
    )
    power_ports = has_power_ports
    has_power_outlets = RelatedMembershipBooleanFilter(
        field_name="poweroutlets",
        label="Has power outlets",
    )
    power_outlets = has_power_outlets
    has_interfaces = RelatedMembershipBooleanFilter(
        field_name="interfaces",
        label="Has interfaces",
    )
    interfaces = has_interfaces
    pass_through_ports = django_filters.BooleanFilter(
        method="_pass_through_ports",
        label="Has pass-through ports",
    )
    has_front_ports = RelatedMembershipBooleanFilter(
        field_name="frontports",
        label="Has front ports",
    )
    has_rear_ports = RelatedMembershipBooleanFilter(
        field_name="rearports",
        label="Has rear ports",
    )
    has_device_bays = RelatedMembershipBooleanFilter(
        field_name="devicebays",
        label="Has device bays",
    )
    device_bays = has_device_bays
    tag = TagFilter()

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
        ]

    def generate_query__has_primary_ip(self, value):
        query = Q(primary_ip4__isnull=False) | Q(primary_ip6__isnull=False)
        if not value:
            return ~query
        return query

    def _has_primary_ip(self, queryset, name, value):
        params = self.generate_query__has_primary_ip(value)
        return queryset.filter(params)

    # 2.0 TODO: Remove me and `pass_through_ports` in exchange for `has_(front|rear)_ports`.
    def generate_query__pass_through_ports(self, value):
        query = Q(frontports__isnull=False, rearports__isnull=False)
        if not value:
            return ~query
        return query

    def _pass_through_ports(self, queryset, name, value):
        params = self.generate_query__pass_through_ports(value)
        return queryset.filter(params)


# TODO: should be DeviceComponentFilterSetMixin
class DeviceComponentFilterSet(CustomFieldModelFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "label": "icontains",
            "description": "icontains",
        },
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="device__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="device__site__region",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="device__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site name (slug)",
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label="Device (ID)",
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name="device__name",
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name)",
    )
    tag = TagFilter()


# TODO: should be CableTerminationFilterSetMixin
class CableTerminationFilterSet(django_filters.FilterSet):
    cabled = django_filters.BooleanFilter(field_name="cable", lookup_expr="isnull", exclude=True)
    cable = django_filters.ModelMultipleChoiceFilter(
        queryset=Cable.objects.all(),
        label="Cable",
    )


# TODO: should be PathEndpointFilterSetMixin
class PathEndpointFilterSet(django_filters.FilterSet):
    connected = django_filters.BooleanFilter(method="filter_connected", label="Connected status (bool)")

    def filter_connected(self, queryset, name, value):
        if value:
            return queryset.filter(_path__is_active=True)
        else:
            return queryset.filter(Q(_path__isnull=True) | Q(_path__is_active=False))


class ConsolePortFilterSet(
    BaseFilterSet,
    DeviceComponentFilterSet,
    CableTerminationFilterSet,
    PathEndpointFilterSet,
):
    type = django_filters.MultipleChoiceFilter(choices=ConsolePortTypeChoices, null_value=None)

    class Meta:
        model = ConsolePort
        fields = ["id", "name", "description", "label"]


class ConsoleServerPortFilterSet(
    BaseFilterSet,
    DeviceComponentFilterSet,
    CableTerminationFilterSet,
    PathEndpointFilterSet,
):
    type = django_filters.MultipleChoiceFilter(choices=ConsolePortTypeChoices, null_value=None)

    class Meta:
        model = ConsoleServerPort
        fields = ["id", "name", "description", "label"]


class PowerPortFilterSet(
    BaseFilterSet,
    DeviceComponentFilterSet,
    CableTerminationFilterSet,
    PathEndpointFilterSet,
):
    type = django_filters.MultipleChoiceFilter(choices=PowerPortTypeChoices, null_value=None)
    power_outlets = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="poweroutlets",
        to_field_name="name",
        queryset=PowerOutlet.objects.all(),
        label="Power outlets (name or ID)",
    )
    has_power_outlets = RelatedMembershipBooleanFilter(
        field_name="poweroutlets",
        label="Has power outlets",
    )

    class Meta:
        model = PowerPort
        fields = ["id", "name", "maximum_draw", "allocated_draw", "description", "label"]


class PowerOutletFilterSet(
    BaseFilterSet,
    DeviceComponentFilterSet,
    CableTerminationFilterSet,
    PathEndpointFilterSet,
):
    type = django_filters.MultipleChoiceFilter(choices=PowerOutletTypeChoices, null_value=None)
    power_port = django_filters.ModelMultipleChoiceFilter(
        field_name="power_port",
        queryset=PowerPort.objects.all(),
        label="Power port",
    )

    class Meta:
        model = PowerOutlet
        fields = ["id", "name", "feed_leg", "description", "label"]


class InterfaceFilterSet(
    BaseFilterSet,
    DeviceComponentFilterSet,
    CableTerminationFilterSet,
    PathEndpointFilterSet,
    StatusModelFilterSetMixin,
):
    # Override device and device_id filters from DeviceComponentFilterSet to match against any peer virtual chassis
    # members
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
    parent_interface = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Interface.objects.all(),
        label="Parent interface (name or ID)",
    )
    bridge = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Interface.objects.all(),
        label="Bridge interface (name or ID)",
    )
    lag_id = django_filters.ModelMultipleChoiceFilter(
        field_name="lag",
        queryset=Interface.objects.filter(type=InterfaceTypeChoices.TYPE_LAG),
        label="LAG interface (ID)",
    )
    lag = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Interface.objects.all(),
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
    child_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Interface.objects.all(),
        label="Child interfaces (name or ID)",
    )
    has_child_interfaces = RelatedMembershipBooleanFilter(
        field_name="child_interfaces",
        label="Has child interfaces",
    )
    bridged_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Interface.objects.all(),
        label="Bridged interfaces (name or ID)",
    )
    has_bridged_interfaces = RelatedMembershipBooleanFilter(
        field_name="bridged_interfaces",
        label="Has bridged interfaces",
    )
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
    tag = TagFilter()
    vlan_id = django_filters.CharFilter(method="filter_vlan_id", label="Assigned VLAN")
    vlan = django_filters.NumberFilter(method="filter_vlan", label="Assigned VID")
    type = django_filters.MultipleChoiceFilter(choices=InterfaceTypeChoices, null_value=None)

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


class FrontPortFilterSet(BaseFilterSet, DeviceComponentFilterSet, CableTerminationFilterSet):
    rear_port = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="rear_port",
        to_field_name="name",
        queryset=RearPort.objects.all(),
        label="Rear port (name or ID)",
    )

    class Meta:
        model = FrontPort
        fields = ["id", "name", "type", "description", "label", "rear_port_position"]


class RearPortFilterSet(BaseFilterSet, DeviceComponentFilterSet, CableTerminationFilterSet):
    front_ports = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="frontports",
        to_field_name="name",
        queryset=FrontPort.objects.all(),
        label="Front ports (name or ID)",
    )
    has_front_ports = RelatedMembershipBooleanFilter(
        field_name="frontports",
        label="Has front ports",
    )

    class Meta:
        model = RearPort
        fields = ["id", "name", "type", "positions", "description", "label"]


class DeviceBayFilterSet(BaseFilterSet, DeviceComponentFilterSet):
    installed_device = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="installed_device",
        to_field_name="name",
        queryset=Device.objects.all(),
        label="Installed device (name or ID)",
    )

    class Meta:
        model = DeviceBay
        fields = ["id", "name", "description", "label"]


class InventoryItemFilterSet(BaseFilterSet, DeviceComponentFilterSet):
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
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="device__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="device__site__region",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="device__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site name (slug)",
    )
    device_id = django_filters.ModelChoiceFilter(
        queryset=Device.objects.all(),
        label="Device (ID)",
    )
    device = django_filters.ModelChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name)",
    )
    parent_id = django_filters.ModelMultipleChoiceFilter(
        queryset=InventoryItem.objects.all(),
        label="Parent inventory item (ID)",
    )
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=InventoryItem.objects.all(),
        to_field_name="name",
        label="Parent (name or ID)",
    )
    manufacturer_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Manufacturer.objects.all(),
        label="Manufacturer (ID)",
    )
    manufacturer = django_filters.ModelMultipleChoiceFilter(
        field_name="manufacturer__slug",
        queryset=Manufacturer.objects.all(),
        to_field_name="slug",
        label="Manufacturer (slug)",
    )
    child_items = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=InventoryItem.objects.all(),
        to_field_name="name",
        label="Child items (name or ID)",
    )
    has_child_items = RelatedMembershipBooleanFilter(
        field_name="child_items",
        label="Has child items",
    )
    serial = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = InventoryItem
        fields = ["id", "name", "part_id", "asset_tag", "discovered", "description", "label"]


class VirtualChassisFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "members__name": "icontains",
            "domain": "icontains",
        },
    )
    master_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label="Master (ID)",
    )
    master = django_filters.ModelMultipleChoiceFilter(
        field_name="master__name",
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Master (name)",
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="master__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="master__site__region",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="master__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="master__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site name (slug)",
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        field_name="master__tenant",
        queryset=Tenant.objects.all(),
        label="Tenant (ID)",
    )
    tenant = django_filters.ModelMultipleChoiceFilter(
        field_name="master__tenant__slug",
        queryset=Tenant.objects.all(),
        to_field_name="slug",
        label="Tenant (slug)",
    )
    members = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Device.objects.all(),
        label="Device members (name or ID)",
    )
    has_members = RelatedMembershipBooleanFilter(
        field_name="members",
        label="Has device members",
    )
    tag = TagFilter()

    class Meta:
        model = VirtualChassis
        fields = ["id", "domain", "name"]


class CableFilterSet(NautobotFilterSet, StatusModelFilterSetMixin):
    q = SearchFilter(filter_predicates={"label": "icontains"})
    type = django_filters.MultipleChoiceFilter(choices=CableTypeChoices)
    color = MultiValueCharFilter()
    device_id = MultiValueUUIDFilter(method="filter_device", label="Device (ID)")
    device = MultiValueCharFilter(method="filter_device", field_name="device__name", label="Device (name)")
    rack_id = MultiValueUUIDFilter(method="filter_device", field_name="device__rack_id", label="Rack (ID)")
    rack = MultiValueCharFilter(method="filter_device", field_name="device__rack__name", label="Rack (name)")
    site_id = MultiValueUUIDFilter(method="filter_device", field_name="device__site_id", label="Site (ID)")
    site = MultiValueCharFilter(method="filter_device", field_name="device__site__slug", label="Site (name)")
    region_id = MultiValueUUIDFilter(method="filter_device", field_name="device__site__region_id", label="Region (ID)")
    region = MultiValueCharFilter(
        method="filter_device", field_name="device__site__region__slug", label="Region (name)"
    )
    tenant_id = MultiValueUUIDFilter(method="filter_device", field_name="device__tenant_id", label="Tenant (ID)")
    tenant = MultiValueCharFilter(method="filter_device", field_name="device__tenant__slug", label="Tenant (name)")
    termination_a_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("cable_terminations").get_choices,
        conjoined=False,
    )
    termination_b_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("cable_terminations").get_choices,
        conjoined=False,
    )
    tag = TagFilter()

    class Meta:
        model = Cable
        fields = [
            "id",
            "label",
            "length",
            "length_unit",
            "termination_a_id",
            "termination_b_id",
        ]

    def filter_device(self, queryset, name, value):
        queryset = queryset.filter(
            Q(**{f"_termination_a_{name}__in": value}) | Q(**{f"_termination_b_{name}__in": value})
        )
        return queryset


# TODO: should be ConnectionFilterSetMixin
class ConnectionFilterSet:
    def filter_site(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(device__site__slug=value)

    def filter_device(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(**{f"{name}__in": value})


class ConsoleConnectionFilterSet(ConnectionFilterSet, BaseFilterSet):
    site = django_filters.CharFilter(
        method="filter_site",
        label="Site (slug)",
    )
    device_id = MultiValueUUIDFilter(method="filter_device", label="Device (ID)")
    device = MultiValueCharFilter(method="filter_device", field_name="device__name", label="Device (name)")

    class Meta:
        model = ConsolePort
        fields = ["name"]


class PowerConnectionFilterSet(ConnectionFilterSet, BaseFilterSet):
    site = django_filters.CharFilter(
        method="filter_site",
        label="Site (slug)",
    )
    device_id = MultiValueUUIDFilter(method="filter_device", label="Device (ID)")
    device = MultiValueCharFilter(method="filter_device", field_name="device__name", label="Device (name)")

    class Meta:
        model = PowerPort
        fields = ["name"]


class InterfaceConnectionFilterSet(ConnectionFilterSet, BaseFilterSet):
    site = django_filters.CharFilter(
        method="filter_site",
        label="Site (slug)",
    )
    device_id = MultiValueUUIDFilter(method="filter_device", label="Device (ID)")
    device = MultiValueCharFilter(method="filter_device", field_name="device__name", label="Device (name)")

    class Meta:
        model = Interface
        fields = []


class PowerPanelFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin):
    q = SearchFilter(filter_predicates={"name": "icontains"})
    rack_group_id = TreeNodeMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        field_name="rack_group",
        label="Rack group (ID)",
    )
    rack_group = TreeNodeMultipleChoiceFilter(
        queryset=RackGroup.objects.all(),
        label="Rack group (slug or ID)",
    )
    power_feeds = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="powerfeeds",
        to_field_name="name",
        queryset=PowerFeed.objects.all(),
        label="Power feeds (name or ID)",
    )
    has_power_feeds = RelatedMembershipBooleanFilter(
        field_name="powerfeeds",
        label="Has power feeds",
    )
    tag = TagFilter()

    class Meta:
        model = PowerPanel
        fields = ["id", "name"]


class PowerFeedFilterSet(
    NautobotFilterSet, CableTerminationFilterSet, PathEndpointFilterSet, StatusModelFilterSetMixin
):
    q = SearchFilter(filter_predicates={"name": "icontains", "comments": "icontains"})
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="power_panel__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="power_panel__site__region",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="power_panel__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="power_panel__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site name (slug)",
    )
    power_panel_id = django_filters.ModelMultipleChoiceFilter(
        queryset=PowerPanel.objects.all(),
        label="Power panel (ID)",
    )
    power_panel = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=PowerPanel.objects.all(),
        to_field_name="name",
        label="Power panel (name or ID)",
    )
    rack_id = django_filters.ModelMultipleChoiceFilter(
        field_name="rack",
        queryset=Rack.objects.all(),
        label="Rack (ID)",
    )
    rack = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Rack.objects.all(),
        to_field_name="name",
        label="Rack (name or ID)",
    )
    tag = TagFilter()

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
        ]


class DeviceRedundancyGroupFilterSet(NautobotFilterSet, StatusModelFilterSetMixin, NameSlugSearchFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "comments": "icontains"})
    tag = TagFilter()
    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="secrets_group",
        queryset=SecretsGroup.objects.all(),
        to_field_name="slug",
        label="Secrets group",
    )

    class Meta:
        model = DeviceRedundancyGroup
        fields = ["id", "name", "slug", "failover_strategy"]
