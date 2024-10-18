from nautobot.core.filters import NaturalKeyOrPKMultipleChoiceFilter, SearchFilter
from nautobot.dcim.filters.mixins import LocatableModelFilterSetMixin
from nautobot.dcim.models import Device, Interface, Zone, ZoneType
from nautobot.extras.filters import NautobotFilterSet
from nautobot.extras.filters.mixins import RoleModelFilterSetMixin, StatusModelFilterSetMixin
from nautobot.ipam.models import Prefix, VLAN
from nautobot.tenancy.filters.mixins import TenancyModelFilterSetMixin


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
    prefixes = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        queryset=Prefix.objects.all(),
        label="Prefix (ID)",
    )
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
            
            "tags",
        ]
