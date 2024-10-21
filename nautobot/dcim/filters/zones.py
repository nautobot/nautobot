import django_filters
from nautobot.core.filters import NaturalKeyOrPKMultipleChoiceFilter, SearchFilter
from nautobot.dcim.filters.mixins import LocatableModelFilterSetMixin
from nautobot.dcim.models import Device, Interface, Zone, ZoneType, ZoneDeviceAssignment, ZoneInterfaceAssignment, ZonePrefixAssignment, ZoneVLANAssignment, ZoneVRFAssignment
from nautobot.extras.filters import NautobotFilterSet
from nautobot.extras.filters.mixins import RoleModelFilterSetMixin, StatusModelFilterSetMixin
from nautobot.ipam.models import VRF, Prefix, VLAN
from nautobot.tenancy.filters.mixins import TenancyModelFilterSetMixin


class ZoneTypeFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )

    class Meta:
        model = ZoneType
        fields = [
            "id",
            "name",
            "description",
            "tags",
        ]


class ZoneFilterSet(
    NautobotFilterSet,
    LocatableModelFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )
    type = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=ZoneType.objects.all(),
        label="Zone type (name or ID)",
    )
    # Prefix doesn't have an appropriate natural key for NaturalKeyOrPKMultipleChoiceFilter
    prefixes = django_filters.ModelMultipleChoiceFilter(queryset=Prefix.objects.all())
    devices = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=Device.objects.all(),
        label="Device (name or ID)",
    )
    interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="name",
        queryset=Interface.objects.all(),
        label="Interface (name or ID)",
    )
    vlans = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VLAN.objects.all(),
        label="VLAN (name or ID)",
    )
    vrfs = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VLAN.objects.all(),
        label="VLAN (name or ID)",
    )

    class Meta:
        model = Zone
        fields = [
            "id",
            "name",
            "description",
            "type",
            "status",
            "role",
            "prefixes",
            "interfaces",
            "vlans",
            "vrfs",
            "tags",
        ]


class ZonePrefixAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "prefix": {
                "lookup_expr": "net_contains",
                "preprocessor": str.strip,
            },
            "zone__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    # Prefix doesn't have an appropriate natural key for NaturalKeyOrPKMultipleChoiceFilter
    prefix = django_filters.ModelMultipleChoiceFilter(queryset=Prefix.objects.all())
    zone = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Zone.objects.all(),
        to_field_name="name",
        label="Zone (name or ID)",
    )

    class Meta:
        model = ZonePrefixAssignment
        fields = [
            "prefix",
            "zone",
        ]


class ZoneDeviceAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "device__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "zone__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device",
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
    )
    zone = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Zone.objects.all(),
        to_field_name="name",
        label="Zone (name or ID)",
    )

    class Meta:
        model = ZoneDeviceAssignment
        fields = [
            "device",
            "zone",
        ]


class ZoneInterfaceAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "interface__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "zone__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    interface = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Interface (name or ID)",
    )
    zone = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Zone.objects.all(),
        to_field_name="name",
        label="Zone (name or ID)",
    )

    class Meta:
        model = ZoneInterfaceAssignment
        fields = [
            "interface",
            "zone",
        ]


class ZoneVLANAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "vlan__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "vlan__vid": {
                "lookup_expr": "exact",
                "preprocessor": str.strip,
            },
            "zone__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    vlan = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=VLAN.objects.all(),
        to_field_name="name",
        label="VLAN (name or ID)",
    )
    zone = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Zone.objects.all(),
        to_field_name="name",
        label="Zone (name or ID)",
    )

    class Meta:
        model = ZoneVLANAssignment
        fields = [
            "vlan",
            "zone",
        ]


class ZoneVRFAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "vrf__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "zone__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
        }
    )
    vrf = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=VRF.objects.all(),
        to_field_name="name",
        label="VRF (name or ID)",
    )
    zone = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Zone.objects.all(),
        to_field_name="name",
        label="Zone (name or ID)",
    )

    class Meta:
        model = ZoneVRFAssignment
        fields = [
            "vrf",
            "zone",
        ]
