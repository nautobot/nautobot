from django.db.models import Q
import django_filters

from nautobot.core.filters import (
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
from nautobot.dcim.constants import MODULE_RECURSION_DEPTH_LIMIT
from nautobot.dcim.models import (
    Cable,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Device,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    Location,
    Manufacturer,
    Module,
    ModuleBay,
    ModuleBayTemplate,
    ModuleType,
    PowerOutlet,
    PowerOutletTemplate,
    PowerPort,
    PowerPortTemplate,
    RearPort,
    RearPortTemplate,
)
from nautobot.extras.filters import CustomFieldModelFilterSetMixin
from nautobot.extras.filters.mixins import RelationshipModelFilterSetMixin


class CableTerminationModelFilterSetMixin(django_filters.FilterSet):
    has_cable = RelatedMembershipBooleanFilter(
        field_name="cable",
        label="Has cable",
    )
    cable = django_filters.ModelMultipleChoiceFilter(
        queryset=Cable.objects.all(),
        label="Cable",
    )


class DeviceComponentTemplateModelFilterSetMixin(NameSearchFilterSet, CustomFieldModelFilterSetMixin):
    device_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        label="Device type (model or ID)",
    )
    label = MultiValueCharFilter(label="Label")
    description = MultiValueCharFilter(label="Description")
    id = MultiValueUUIDFilter(label="ID")
    name = MultiValueCharFilter(label="Name")


class ModularDeviceComponentTemplateModelFilterSetMixin(DeviceComponentTemplateModelFilterSetMixin):
    has_device_type = RelatedMembershipBooleanFilter(
        field_name="device_type",
        label="Has device type",
    )
    module_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ModuleType.objects.all(),
        to_field_name="model",
        label="Module type (model or ID)",
    )
    has_module_type = RelatedMembershipBooleanFilter(
        field_name="module_type",
        label="Has module type",
    )


class DeviceComponentModelFilterSetMixin(CustomFieldModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "label": "icontains",
            "description": "icontains",
        },
    )
    location = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device__location",
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
    )


class ModularDeviceComponentModelFilterSetMixin(DeviceComponentModelFilterSetMixin, RelationshipModelFilterSetMixin):
    module = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Module.objects.all(),
        to_field_name="module_type__model",
        label="Module (model or ID)",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
        method="filter_device",
    )

    def _construct_device_filter_recursively(self, field_name, value):
        recursion_depth = MODULE_RECURSION_DEPTH_LIMIT - 1
        query = Q(**{f"device__{field_name}__in": value})
        for level in range(recursion_depth):
            recursive_query = "module__parent_module_bay__" + "parent_module__parent_module_bay__" * level
            query = query | Q(**{f"{recursive_query}parent_device__{field_name}__in": value})
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


class LocatableModelFilterSetMixin(django_filters.FilterSet):
    """Mixin to add `location` filter fields to a FilterSet.

    The expectation is that the linked model has `location` FK fields.
    """

    location = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )


class PathEndpointModelFilterSetMixin(django_filters.FilterSet):
    connected = django_filters.BooleanFilter(method="filter_connected", label="Connected status (bool)")

    def filter_connected(self, queryset, name, value):
        if value:
            return queryset.filter(_path__is_active=True)
        else:
            return queryset.filter(Q(_path__isnull=True) | Q(_path__is_active=False))


class DeviceModuleCommonFiltersMixin(django_filters.FilterSet):
    mac_address = MultiValueMACAddressFilter(
        field_name="interfaces__mac_address",
        label="MAC address",
    )
    has_console_ports = RelatedMembershipBooleanFilter(
        field_name="console_ports",
        label="Has console ports",
    )
    console_ports = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ConsolePort.objects.all(),
        to_field_name="name",
        label="Console Ports (name or ID)",
    )
    has_console_server_ports = RelatedMembershipBooleanFilter(
        field_name="console_server_ports",
        label="Has console server ports",
    )
    console_server_ports = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ConsoleServerPort.objects.all(),
        to_field_name="name",
        label="Console Server Ports (name or ID)",
    )
    has_power_ports = RelatedMembershipBooleanFilter(
        field_name="power_ports",
        label="Has power ports",
    )
    power_ports = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=PowerPort.objects.all(),
        to_field_name="name",
        label="Power Ports (name or ID)",
    )
    has_power_outlets = RelatedMembershipBooleanFilter(
        field_name="power_outlets",
        label="Has power outlets",
    )
    power_outlets = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=PowerOutlet.objects.all(),
        to_field_name="name",
        label="Power Outlets (name or ID)",
    )
    has_interfaces = RelatedMembershipBooleanFilter(
        field_name="interfaces",
        label="Has interfaces",
    )
    interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Interfaces (name or ID)",
    )
    has_front_ports = RelatedMembershipBooleanFilter(
        field_name="front_ports",
        label="Has front ports",
    )
    front_ports = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=FrontPort.objects.all(),
        to_field_name="name",
        label="Front Ports (name or ID)",
    )
    has_rear_ports = RelatedMembershipBooleanFilter(
        field_name="rear_ports",
        label="Has rear ports",
    )
    rear_ports = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RearPort.objects.all(),
        to_field_name="name",
        label="Rear Ports (name or ID)",
    )
    has_module_bays = RelatedMembershipBooleanFilter(
        field_name="module_bays",
        label="Has module bays",
    )
    has_empty_module_bays = django_filters.BooleanFilter(
        method="filter_has_empty_module_bays",
        label="Has empty module bays",
    )
    module_bays = django_filters.ModelMultipleChoiceFilter(
        queryset=ModuleBay.objects.all(),
        label="Module Bays",
    )
    has_modules = RelatedMembershipBooleanFilter(
        field_name="module_bays__installed_module",
        label="Has modules",
    )

    def generate_query_filter_has_empty_module_bays(self, value):
        if value is True:
            query = Q(module_bays__isnull=False, module_bays__installed_module__isnull=True)
        else:
            query = Q(module_bays__isnull=True) | ~Q(module_bays__installed_module__isnull=True)
        return query

    def filter_has_empty_module_bays(self, queryset, name, value):
        if value is None:
            return queryset.none
        params = self.generate_query_filter_has_empty_module_bays(value)
        return queryset.filter(params)


class DeviceTypeModuleTypeCommonFiltersMixin(django_filters.FilterSet):
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
        label="Manufacturer (name or ID)",
    )
    # TODO: solve https://github.com/nautobot/nautobot/issues/2875 to use this filter correctly
    console_port_templates = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
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
        prefers_id=True,
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
        prefers_id=True,
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
        prefers_id=True,
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
        prefers_id=True,
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
        prefers_id=True,
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
        prefers_id=True,
        to_field_name="name",
        queryset=RearPortTemplate.objects.all(),
        label="Rear port templates (name or ID)",
    )
    has_rear_port_templates = RelatedMembershipBooleanFilter(
        field_name="rear_port_templates",
        label="Has rear port templates",
    )
    module_bay_templates = django_filters.ModelMultipleChoiceFilter(
        queryset=ModuleBayTemplate.objects.all(),
    )
    has_module_bay_templates = RelatedMembershipBooleanFilter(
        field_name="module_bay_templates",
        label="Has module bay templates",
    )
