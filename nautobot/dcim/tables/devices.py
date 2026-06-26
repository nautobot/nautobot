from django.utils.html import format_html, format_html_join
import django_tables2 as tables
from django_tables2.utils import Accessor

from nautobot.core.tables import (
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    ColoredLabelColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.core.templatetags.helpers import HTML_NONE, humanize_speed
from nautobot.dcim.models import (
    ConsolePort,
    ConsoleServerPort,
    Controller,
    ControllerManagedDeviceGroup,
    Device,
    DeviceBay,
    DeviceRedundancyGroup,
    FrontPort,
    Interface,
    InterfaceRedundancyGroup,
    InterfaceRedundancyGroupAssociation,
    InventoryItem,
    Module,
    ModuleBay,
    ModuleFamily,
    Platform,
    PowerOutlet,
    PowerPort,
    RearPort,
    SoftwareImageFile,
    SoftwareVersion,
    VirtualChassis,
    VirtualDeviceContext,
)
from nautobot.dcim.utils import cable_status_color_css
from nautobot.extras.tables import RoleTableMixin, StatusTableMixin
from nautobot.tenancy.tables import TenantColumn

from .template_code import (
    CABLE_TERMINATION_BUTTONS,
    CABLETERMINATION,
    DEVICE_LINK,
    DEVICEBAY_BUTTONS,
    DeviceComponentNameColumn,
    INTERFACE_BUTTONS,
    INTERFACE_IPADDRESSES,
    INTERFACE_REDUNDANCY_GROUP_INTERFACES,
    INTERFACE_REDUNDANCY_GROUP_INTERFACES_IPADDRESSES,
    INTERFACE_REDUNDANCY_INTERFACE_PRIORITY,
    INTERFACE_TAGGED_VLANS,
    MODULEBAY_BUTTONS,
    PARENT_DEVICE,
    PATHENDPOINT,
    TREE_LINK,
)

__all__ = (
    "ConsolePortTable",
    "ConsoleServerPortTable",
    "ControllerManagedDeviceGroupTable",
    "ControllerTable",
    "DeviceBayTable",
    "DeviceDeviceBayTable",
    "DeviceImportTable",
    "DeviceInventoryItemTable",
    "DeviceModuleBayTable",
    "DeviceModuleConsolePortTable",
    "DeviceModuleConsoleServerPortTable",
    "DeviceModuleFrontPortTable",
    "DeviceModuleInterfaceTable",
    "DeviceModulePowerOutletTable",
    "DeviceModulePowerPortTable",
    "DeviceModuleRearPortTable",
    "DeviceRedundancyGroupTable",
    "DeviceTable",
    "FrontPortTable",
    "InterfaceRedundancyGroupAssociationTable",
    "InterfaceRedundancyGroupTable",
    "InterfaceTable",
    "InventoryItemTable",
    "ModuleBayTable",
    "ModuleFamilyTable",
    "ModuleModuleBayTable",
    "ModuleTable",
    "PlatformTable",
    "PowerOutletTable",
    "PowerPortTable",
    "RearPortTable",
    "SoftwareImageFileTable",
    "SoftwareVersionTable",
    "VirtualChassisTable",
    "VirtualDeviceContextTable",
)


#
# Platforms
#


class PlatformTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    manufacturer = tables.Column(linkify=True)
    device_count = LinkedCountColumn(
        viewname="dcim:device_list",
        url_params={"platform": "pk"},
        verbose_name="Devices",
    )
    virtual_machine_count = LinkedCountColumn(
        viewname="virtualization:virtualmachine_list",
        url_params={"platform": "pk"},
        verbose_name="VMs",
    )
    actions = ButtonsColumn(Platform)

    class Meta(BaseTable.Meta):
        model = Platform
        fields = (
            "pk",
            "name",
            "manufacturer",
            "device_count",
            "virtual_machine_count",
            "napalm_driver",
            "napalm_args",
            "network_driver",
            "description",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "manufacturer",
            "device_count",
            "virtual_machine_count",
            "napalm_driver",
            "network_driver",
            "description",
            "actions",
        )


#
# Devices
#


class VirtualChassisMembersTable(BaseTable):
    name = tables.TemplateColumn(order_by=("_name",), template_code=DEVICE_LINK, verbose_name="Device")
    vc_position = tables.TemplateColumn(
        verbose_name="Position", template_code='<span class="badge badge-default">{{ record.vc_position }}</span>'
    )
    master = BooleanColumn(accessor="is_vc_master", verbose_name="Master")
    vc_priority = tables.Column(verbose_name="Priority")

    class Meta(BaseTable.Meta):
        model = Device
        fields = (
            "name",
            "vc_position",
            "master",
            "vc_priority",
        )
        default_columns = (
            "name",
            "vc_position",
            "master",
            "vc_priority",
        )


class DeviceTable(StatusTableMixin, RoleTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(order_by=("_name",), template_code=DEVICE_LINK)
    tenant = TenantColumn()
    location = tables.Column(linkify=True)
    rack = tables.Column(linkify=True)
    device_type = tables.LinkColumn(  # used because tables.Column() doesn't support `text` lambda
        viewname="dcim:devicetype",
        args=[Accessor("device_type__pk")],
        verbose_name="Type",
        text=lambda record: record.device_type.display,
    )
    primary_ip = tables.Column(linkify=True, order_by=("primary_ip6", "primary_ip4"), verbose_name="IP Address")
    primary_ip4 = tables.Column(linkify=True, verbose_name="IPv4 Address")
    primary_ip6 = tables.Column(linkify=True, verbose_name="IPv6 Address")
    cluster_count = LinkedCountColumn(
        viewname="virtualization:cluster_list",
        url_params={"devices": "pk"},
        verbose_name="Clusters",
    )
    virtual_chassis = tables.Column(linkify=True)
    vc_position = tables.Column(verbose_name="VC Position")
    vc_priority = tables.Column(verbose_name="VC Priority")
    device_redundancy_group = tables.Column(linkify=True)
    device_redundancy_group_priority = tables.TemplateColumn(
        template_code="""{% if record.device_redundancy_group %}<span class="badge badge-default">{{ record.device_redundancy_group_priority|default:'None' }}</span>{% else %}<span class="text-secondary">—</span>{% endif %}"""
    )
    controller_managed_device_group = tables.Column(linkify=True, verbose_name="Device Group")
    software_version = tables.Column(linkify=True, verbose_name="Software Version")
    secrets_group = tables.Column(linkify=True)
    capabilities = tables.Column(orderable=False, accessor="controller_managed_device_group.capabilities")
    manufacturer = tables.Column(orderable=False, accessor="device_type.manufacturer")
    parent_device = tables.TemplateColumn(template_code=PARENT_DEVICE, orderable=False)
    parent_bay = tables.Column(orderable=False)
    tags = TagColumn(url_name="dcim:device_list")
    actions = ButtonsColumn(Device)

    class Meta(BaseTable.Meta):
        model = Device
        fields = (
            "pk",
            "name",
            "status",
            "tenant",
            "role",
            "device_type",
            "platform",
            "serial",
            "asset_tag",
            "location",
            "rack",
            "position",
            "face",
            "primary_ip",
            "primary_ip4",
            "primary_ip6",
            "cluster_count",
            "virtual_chassis",
            "vc_position",
            "vc_priority",
            "device_redundancy_group",
            "device_redundancy_group_priority",
            "software_version",
            "controller_managed_device_group",
            "secrets_group",
            "capabilities",
            "manufacturer",
            "parent_device",
            "parent_bay",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "status",
            "tenant",
            "location",
            "rack",
            "role",
            "device_type",
            "primary_ip",
            "actions",
        )

    def render_capabilities(self, value):
        """Render capabilities."""
        if not value:
            return HTML_NONE
        return format_html_join(" ", '<span class="badge bg-secondary">{}</span>', ((v,) for v in value))


class DeviceImportTable(StatusTableMixin, RoleTableMixin, BaseTable):
    name = tables.TemplateColumn(template_code=DEVICE_LINK)
    tenant = TenantColumn()
    location = tables.Column(linkify=True)
    rack = tables.Column(linkify=True)
    device_type = tables.Column(verbose_name="Type")

    class Meta(BaseTable.Meta):
        model = Device
        fields = (
            "name",
            "status",
            "tenant",
            "location",
            "rack",
            "position",
            "role",
            "device_type",
        )
        empty_text = False


#
# Modules
#


class ModuleTable(StatusTableMixin, RoleTableMixin, BaseTable):
    pk = ToggleColumn()
    id = tables.Column(linkify=True, verbose_name="ID")
    module_type = tables.Column(
        linkify=lambda record: record.module_type.get_absolute_url(),
        verbose_name="Type",
        accessor="module_type__display",
        order_by=["module_type"],
    )
    parent_module_bay = tables.Column(
        linkify=lambda record: record.parent_module_bay.get_absolute_url() if record else None,
        verbose_name="Parent Module Bay",
        accessor="parent_module_bay__display",
        order_by=["parent_module_bay"],
    )
    location = tables.Column(linkify=True)
    tenant = TenantColumn()
    module_family = tables.Column(linkify=True, verbose_name="Family", accessor="module_type__module_family")
    tags = TagColumn(url_name="dcim:module_list")
    actions = ButtonsColumn(Module)

    class Meta(BaseTable.Meta):
        model = Module
        fields = (
            "pk",
            "id",
            "module_type",
            "module_family",
            "parent_module_bay",
            "location",
            "serial",
            "asset_tag",
            "status",
            "role",
            "tenant",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "id",
            "module_type",
            "module_family",
            "parent_module_bay",
            "location",
            "serial",
            "asset_tag",
            "status",
            "role",
            "tenant",
            "actions",
        )


class ModuleFamilyTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    module_type_count = LinkedCountColumn(
        viewname="dcim:moduletype_list", url_params={"module_family": "pk"}, verbose_name="Module Types"
    )
    module_bay_count = LinkedCountColumn(
        viewname="dcim:modulebay_list", url_params={"module_family": "pk"}, verbose_name="Module Bays"
    )
    tags = TagColumn()
    actions = ButtonsColumn(ModuleFamily)

    class Meta(BaseTable.Meta):
        model = ModuleFamily
        fields = (
            "pk",
            "name",
            "description",
            "module_type_count",
            "module_bay_count",
            "tags",
            "created",
            "last_updated",
            "actions",
        )
        default_columns = (
            "name",
            "description",
            "module_type_count",
            "module_bay_count",
            "actions",
        )


#
# Device components
#


class DeviceComponentTable(BaseTable):
    pk = ToggleColumn()
    device = tables.Column(linkify=True)
    name = tables.Column(linkify=True, order_by=("_name",))


class ModularDeviceComponentTable(DeviceComponentTable):
    module = tables.Column()

    def __init__(self, *args, parent_module=None, **kwargs):
        self.parent_module = parent_module
        super().__init__(*args, **kwargs)

    def render_module(self, record, value, **kwargs):
        if value == self.parent_module or not value:
            return self.default
        return format_html('<a href="{}">{}</a>', value.get_absolute_url(), value)


class CableTerminationTable(BaseTable):
    # `cable` is a property on CableTermination subclasses (resolved via the cable_termination
    # join row), not a real model field, so the column is not DB-orderable.
    cable = tables.Column(linkify=True, orderable=False)
    cable_peer = tables.TemplateColumn(
        accessor="get_cable_peers",
        template_code=CABLETERMINATION,
        orderable=False,
        verbose_name="Cable Peer",
    )


class PathEndpointTable(CableTerminationTable):
    # The far-end of each CablePath originating from this endpoint (one per breakout lane).
    # Distinct from `cable_peer` on the parent CableTerminationTable, which shows the immediate
    # peer across the directly-connected cable rather than the resolved path destination.
    connection = tables.TemplateColumn(
        accessor="get_connected_endpoints",
        template_code=PATHENDPOINT,
        verbose_name="Connection",
        orderable=False,
    )


class ConsolePortTable(ModularDeviceComponentTable, PathEndpointTable):
    tags = TagColumn(url_name="dcim:consoleport_list")
    actions = ButtonsColumn(model=ConsolePort, prepend_template=CABLE_TERMINATION_BUTTONS)

    class Meta(ModularDeviceComponentTable.Meta):
        model = ConsolePort
        row_attrs = {"class": cable_status_color_css}
        fields = (
            "pk",
            "device",
            "module",
            "name",
            "label",
            "type",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "actions",
        )
        default_columns = ("pk", "device", "module", "name", "label", "type", "description", "actions")


class DeviceModuleConsolePortTable(ConsolePortTable):
    name = DeviceComponentNameColumn(modelname="consoleport")

    class Meta(ModularDeviceComponentTable.Meta):
        model = ConsolePort
        fields = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "description",
            "cable",
            "connection",
            "actions",
        )
        row_attrs = {
            "class": cable_status_color_css,
        }


class ConsoleServerPortTable(ModularDeviceComponentTable, PathEndpointTable):
    tags = TagColumn(url_name="dcim:consoleserverport_list")
    actions = ButtonsColumn(model=ConsoleServerPort, prepend_template=CABLE_TERMINATION_BUTTONS)

    class Meta(ModularDeviceComponentTable.Meta):
        model = ConsoleServerPort
        row_attrs = {"class": cable_status_color_css}
        fields = (
            "pk",
            "device",
            "module",
            "name",
            "label",
            "type",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "actions",
        )
        default_columns = ("pk", "device", "module", "name", "label", "type", "description", "actions")


class DeviceModuleConsoleServerPortTable(ConsoleServerPortTable):
    name = DeviceComponentNameColumn(modelname="consoleserverport")

    class Meta(ModularDeviceComponentTable.Meta):
        model = ConsoleServerPort
        fields = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "description",
            "cable",
            "connection",
            "actions",
        )
        row_attrs = {
            "class": cable_status_color_css,
        }


class PowerPortTable(ModularDeviceComponentTable, PathEndpointTable):
    tags = TagColumn(url_name="dcim:powerport_list")
    actions = ButtonsColumn(model=PowerPort, prepend_template=CABLE_TERMINATION_BUTTONS)

    class Meta(ModularDeviceComponentTable.Meta):
        model = PowerPort
        row_attrs = {"class": cable_status_color_css}
        fields = (
            "pk",
            "device",
            "module",
            "name",
            "label",
            "type",
            "description",
            "maximum_draw",
            "allocated_draw",
            "power_factor",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "device",
            "module",
            "name",
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
            "actions",
        )


class DeviceModulePowerPortTable(PowerPortTable):
    name = DeviceComponentNameColumn(modelname="powerport")

    class Meta(ModularDeviceComponentTable.Meta):
        model = PowerPort
        fields = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "maximum_draw",
            "allocated_draw",
            "power_factor",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
            "cable",
            "connection",
            "actions",
        )
        row_attrs = {"class": cable_status_color_css}


class PowerOutletTable(ModularDeviceComponentTable, PathEndpointTable):
    power_port = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:poweroutlet_list")
    actions = ButtonsColumn(model=PowerOutlet, prepend_template=CABLE_TERMINATION_BUTTONS)

    class Meta(ModularDeviceComponentTable.Meta):
        model = PowerOutlet
        row_attrs = {"class": cable_status_color_css}
        fields = (
            "pk",
            "device",
            "module",
            "name",
            "label",
            "type",
            "description",
            "power_port",
            "feed_leg",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "device",
            "module",
            "name",
            "label",
            "type",
            "power_port",
            "feed_leg",
            "description",
            "actions",
        )


class DeviceModulePowerOutletTable(PowerOutletTable):
    name = DeviceComponentNameColumn(modelname="poweroutlet")

    class Meta(ModularDeviceComponentTable.Meta):
        model = PowerOutlet
        fields = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "power_port",
            "feed_leg",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "power_port",
            "feed_leg",
            "description",
            "cable",
            "connection",
            "actions",
        )
        row_attrs = {"class": cable_status_color_css}


class BaseInterfaceTable(StatusTableMixin, RoleTableMixin, BaseTable):
    enabled = BooleanColumn()
    ip_addresses = tables.TemplateColumn(
        template_code=INTERFACE_IPADDRESSES,
        orderable=False,
        verbose_name="IP Addresses",
    )
    untagged_vlan = tables.Column(linkify=True)
    tagged_vlans = tables.TemplateColumn(
        template_code=INTERFACE_TAGGED_VLANS,
        orderable=False,
        verbose_name="Tagged VLANs",
    )
    vrf = tables.Column(linkify=True, verbose_name="VRF")


class InterfaceTable(ModularDeviceComponentTable, BaseInterfaceTable, PathEndpointTable):
    mgmt_only = BooleanColumn()
    tags = TagColumn(url_name="dcim:interface_list")
    virtual_device_context_count = LinkedCountColumn(
        viewname="dcim:virtualdevicecontext_list",
        url_params={"interfaces": "pk"},
        verbose_name="Virtual Device Contexts",
    )
    speed = tables.Column(verbose_name="Speed", accessor="speed")
    duplex = tables.Column(verbose_name="Duplex", accessor="duplex")
    actions = ButtonsColumn(model=Interface, prepend_template=INTERFACE_BUTTONS)

    class Meta(ModularDeviceComponentTable.Meta):
        model = Interface
        row_attrs = {"class": cable_status_color_css}
        fields = (
            "pk",
            "device",
            "module",
            "name",
            "status",
            "role",
            "label",
            "enabled",
            "type",
            "port_type",
            "speed",
            "duplex",
            "breakout_position",
            "mgmt_only",
            "mtu",
            "vrf",
            "mode",
            "mac_address",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "ip_addresses",
            "untagged_vlan",
            "virtual_device_context_count",
            "tagged_vlans",
            "actions",
        )
        default_columns = (
            "pk",
            "device",
            "module",
            "name",
            "status",
            "role",
            "label",
            "enabled",
            "type",
            "port_type",
            "speed",
            "breakout_position",
            "connection",
            "description",
            "actions",
        )

    def render_speed(self, record):
        return humanize_speed(record.speed)


class DeviceModuleInterfaceTable(InterfaceTable):
    name = DeviceComponentNameColumn(
        modelname="interface",
        template_code=(
            '<span class="mdi mdi-'
            "{% if record.mgmt_only %}wrench"
            "{% elif record.is_lag %}drag-horizontal-variant"
            "{% elif record.is_virtual %}circle"
            "{% elif record.is_wireless %}wifi"
            '{% else %}ethernet{% endif %}"></span> '
            '<a href="{{ record.get_absolute_url }}">{{ value }}</a>'
        ),
    )
    parent_interface = tables.Column(linkify=True, verbose_name="Parent")
    bridge = tables.Column(linkify=True)
    lag = tables.Column(linkify=True, verbose_name="LAG")

    class Meta(ModularDeviceComponentTable.Meta):
        model = Interface
        fields = (
            "pk",
            "name",
            "status",
            "role",
            "device",
            "label",
            "module",
            "enabled",
            "type",
            "port_type",
            "speed",
            "duplex",
            "parent_interface",
            "breakout_position",
            "bridge",
            "lag",
            "mgmt_only",
            "mtu",
            "vrf",
            "mode",
            "mac_address",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
            "ip_addresses",
            "untagged_vlan",
            "tagged_vlans",
            "virtual_device_context_count",
            "actions",
        )
        default_columns = [
            "pk",
            "name",
            "status",
            "role",
            "label",
            "module",
            "enabled",
            "type",
            "port_type",
            "speed",
            "parent_interface",
            "breakout_position",
            "lag",
            "mtu",
            "vrf",
            "mode",
            "description",
            "ip_addresses",
            "virtual_device_context_count",
            "cable",
            "connection",
            "actions",
        ]
        row_attrs = {
            "class": cable_status_color_css,
            "data-name": lambda record: record.name,
        }

    def render_speed(self, record):
        return humanize_speed(record.speed)


class FrontPortTable(ModularDeviceComponentTable, CableTerminationTable):
    rear_port_position = tables.Column(verbose_name="Position")
    rear_port = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:frontport_list")
    actions = ButtonsColumn(model=FrontPort, prepend_template=CABLE_TERMINATION_BUTTONS)

    class Meta(ModularDeviceComponentTable.Meta):
        model = FrontPort
        row_attrs = {"class": cable_status_color_css}
        fields = (
            "pk",
            "device",
            "module",
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "cable",
            "cable_peer",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "device",
            "module",
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "actions",
        )


class DeviceModuleFrontPortTable(FrontPortTable):
    name = DeviceComponentNameColumn(
        modelname="frontport",
        template_code=(
            '<span class="mdi mdi-arrow-right-bold-box{% if not record.cable %}-outline{% endif %}"></span> '
            '<a href="{{ record.get_absolute_url }}">{{ value }}</a>'
        ),
    )

    class Meta(ModularDeviceComponentTable.Meta):
        model = FrontPort
        fields = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "cable",
            "cable_peer",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "cable",
            "cable_peer",
            "actions",
        )
        row_attrs = {"class": cable_status_color_css}


class RearPortTable(ModularDeviceComponentTable, CableTerminationTable):
    tags = TagColumn(url_name="dcim:rearport_list")
    actions = ButtonsColumn(model=RearPort, prepend_template=CABLE_TERMINATION_BUTTONS)

    class Meta(ModularDeviceComponentTable.Meta):
        model = RearPort
        row_attrs = {"class": cable_status_color_css}
        fields = (
            "pk",
            "device",
            "module",
            "name",
            "label",
            "type",
            "positions",
            "description",
            "cable",
            "cable_peer",
            "tags",
            "actions",
        )
        default_columns = ("pk", "device", "module", "name", "label", "type", "description", "actions")


class DeviceModuleRearPortTable(RearPortTable):
    name = DeviceComponentNameColumn(
        modelname="rearport",
        template_code=(
            '<span class="mdi mdi-arrow-left-bold-box{% if not record.cable %}-outline{% endif %}"></span> '
            '<a href="{{ record.get_absolute_url }}">{{ value }}</a>'
        ),
    )

    class Meta(ModularDeviceComponentTable.Meta):
        model = RearPort
        fields = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "positions",
            "description",
            "cable",
            "cable_peer",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "label",
            "module",
            "type",
            "positions",
            "description",
            "cable",
            "cable_peer",
            "actions",
        )
        row_attrs = {"class": cable_status_color_css}


class DeviceBayTable(DeviceComponentTable):
    installed_device__status = ColoredLabelColumn()
    installed_device = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:devicebay_list")
    actions = ButtonsColumn(model=DeviceBay, prepend_template=DEVICEBAY_BUTTONS)

    class Meta(DeviceComponentTable.Meta):
        model = DeviceBay
        fields = (
            "pk",
            "device",
            "name",
            "label",
            "installed_device__status",
            "installed_device",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "device",
            "name",
            "label",
            "installed_device__status",
            "installed_device",
            "description",
            "actions",
        )


class ModuleBayTable(BaseTable):
    pk = ToggleColumn()
    parent_device = tables.Column(
        linkify=lambda record: record.parent_device.get_absolute_url(),
        verbose_name="Parent Device",
        accessor="parent_device__display",
        order_by=["parent_device"],
    )
    parent_module = tables.Column(
        linkify=lambda record: record.parent_module.get_absolute_url(),
        verbose_name="Parent Module",
        accessor="parent_module__display",
        order_by=["parent_module"],
    )
    name = tables.Column(linkify=True, order_by=("_name",))
    installed_module = tables.Column(linkify=True, verbose_name="Installed Module")
    installed_module__status = ColoredLabelColumn()
    tags = TagColumn(url_name="dcim:devicebay_list")
    module_family = tables.Column(linkify=True, verbose_name="Family")
    actions = ButtonsColumn(model=ModuleBay, prepend_template=MODULEBAY_BUTTONS)

    class Meta(BaseTable.Meta):
        model = ModuleBay
        fields = (
            "pk",
            "parent_device",
            "parent_module",
            "name",
            "position",
            "label",
            "module_family",
            "description",
            "installed_module",
            "installed_module__status",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "parent_device",
            "parent_module",
            "name",
            "position",
            "label",
            "module_family",
            "description",
            "installed_module",
            "installed_module__status",
            "actions",
        )


class DeviceDeviceBayTable(DeviceBayTable):
    name = DeviceComponentNameColumn(
        modelname="devicebay",
        template_code=(
            '<span class="mdi mdi-circle-{% if record.installed_device %}slice-8{% else %}outline{% endif %}">'
            '</span> <a href="{{ record.get_absolute_url }}">{{ value }}</a>'
        ),
    )

    class Meta(DeviceComponentTable.Meta):
        model = DeviceBay
        fields = (
            "pk",
            "name",
            "label",
            "installed_device__status",
            "installed_device",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "label",
            "installed_device__status",
            "installed_device",
            "description",
            "actions",
        )
        row_attrs = {
            "class": lambda record: "table-success" if record.installed_device else "",
        }


class DeviceModuleBayTable(ModuleBayTable):
    name = DeviceComponentNameColumn(
        modelname="modulebay",
        template_code=(
            '<span class="mdi mdi-{% if record.installed_module %}expansion-card-variant{% else %}tray{% endif %}'
            '"></span> <a href="{{ record.get_absolute_url }}">{{ value }}</a>'
        ),
    )
    module_family = tables.Column(linkify=True, verbose_name="Family")
    installed_module = tables.Column(linkify=True, verbose_name="Installed Module")
    installed_module__status = ColoredLabelColumn(verbose_name="Installed Module Status")
    requires_first_party_modules = BooleanColumn(verbose_name="First-Party Only")

    class Meta(ModularDeviceComponentTable.Meta):
        model = ModuleBay
        fields = (
            "pk",
            "name",
            "position",
            "module_family",
            "requires_first_party_modules",
            "installed_module",
            "installed_module__status",
            "label",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "position",
            "module_family",
            "requires_first_party_modules",
            "installed_module",
            "installed_module__status",
            "actions",
        )
        row_attrs = {
            "class": lambda record: "table-success" if record.installed_module else "",
        }


class ModuleModuleBayTable(DeviceModuleBayTable):
    class Meta(DeviceModuleBayTable.Meta):
        pass


class InventoryItemTable(DeviceComponentTable):
    manufacturer = tables.Column(linkify=True)
    discovered = BooleanColumn()
    tags = TagColumn(url_name="dcim:inventoryitem_list")
    actions = ButtonsColumn(InventoryItem)

    class Meta(DeviceComponentTable.Meta):
        model = InventoryItem
        fields = (
            "pk",
            "device",
            "name",
            "label",
            "manufacturer",
            "part_id",
            "serial",
            "asset_tag",
            "description",
            "discovered",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "device",
            "name",
            "label",
            "manufacturer",
            "part_id",
            "serial",
            "asset_tag",
            "actions",
        )


class DeviceInventoryItemTable(InventoryItemTable):
    name = DeviceComponentNameColumn(
        modelname="inventoryitem",
        template_code=(
            "{% load cables %}"
            '<span class="mdi {{ record|termination_type_icon }}" style="padding-left: {{ record.tree_depth }}0px">'
            "</span> "
            '<a href="{{ record.get_absolute_url }}">{{ value }}</a>'
        ),
    )
    actions = ButtonsColumn(model=InventoryItem)

    class Meta(DeviceComponentTable.Meta):
        model = InventoryItem
        fields = (
            "pk",
            "name",
            "label",
            "manufacturer",
            "part_id",
            "serial",
            "asset_tag",
            "description",
            "discovered",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "label",
            "manufacturer",
            "part_id",
            "serial",
            "asset_tag",
            "description",
            "discovered",
            "actions",
        )


#
# Virtual chassis
#


class VirtualChassisTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    master = tables.Column(linkify=True)
    member_count = LinkedCountColumn(
        viewname="dcim:device_list",
        url_params={"virtual_chassis": "pk"},
        verbose_name="Members",
    )
    tags = TagColumn(url_name="dcim:virtualchassis_list")

    class Meta(BaseTable.Meta):
        model = VirtualChassis
        fields = ("pk", "name", "domain", "master", "member_count", "tags")
        default_columns = ("pk", "name", "domain", "master", "member_count")


#
# Device Redundancy Group
#


class DeviceRedundancyGroupTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    device_count = LinkedCountColumn(
        viewname="dcim:device_list",
        url_params={"device_redundancy_group": "pk"},
        verbose_name="Devices",
    )
    controller_count = LinkedCountColumn(
        viewname="dcim:controller_list",
        url_params={"controller_device_redundancy_group": "pk"},
        verbose_name="Controllers",
    )
    secrets_group = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:deviceredundancygroup_list")

    class Meta(BaseTable.Meta):
        model = DeviceRedundancyGroup
        fields = (
            "pk",
            "name",
            "description",
            "status",
            "failover_strategy",
            "controller_count",
            "device_count",
            "secrets_group",
            "tags",
        )
        default_columns = ("pk", "name", "status", "failover_strategy", "controller_count", "device_count")


#
# Interface Redundancy Group
#


class InterfaceRedundancyGroupTable(StatusTableMixin, BaseTable):
    """Table for list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    interfaces = tables.TemplateColumn(
        template_code=INTERFACE_REDUNDANCY_GROUP_INTERFACES,
        orderable=False,
        verbose_name="Interfaces",
    )
    actions = ButtonsColumn(InterfaceRedundancyGroup)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = InterfaceRedundancyGroup
        fields = (
            "pk",
            "name",
            "status",
            "description",
            "protocol",
            "protocol_group_id",
            "interfaces",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "protocol",
            "protocol_group_id",
            "interfaces",
        )


class InterfaceRedundancyGroupAssociationTable(BaseTable):
    """Table for list view."""

    pk = ToggleColumn()
    interface__enabled = BooleanColumn()
    interface_redundancy_group = tables.Column(linkify=True, verbose_name="Group Name")
    interface_redundancy_group__virtual_ip = tables.Column(linkify=True, verbose_name="Virtual IP")
    interface_redundancy_group__protocol_group_id = tables.Column(verbose_name="Group ID")
    priority = tables.TemplateColumn(template_code=INTERFACE_REDUNDANCY_INTERFACE_PRIORITY)
    interface__device = tables.Column(linkify=True)
    interface = tables.Column(linkify=True)
    interface__status = ColoredLabelColumn()
    interface_redundancy_group__status = ColoredLabelColumn(verbose_name="Group Status")
    interface__ip_addresses = tables.TemplateColumn(
        template_code=INTERFACE_REDUNDANCY_GROUP_INTERFACES_IPADDRESSES,
        orderable=False,
        verbose_name="IP Addresses",
    )
    actions = ButtonsColumn(model=InterfaceRedundancyGroupAssociation, buttons=["edit", "delete"])

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = InterfaceRedundancyGroupAssociation
        fields = (
            "pk",
            "interface_redundancy_group",
            "interface",
            "priority",
            "interface_redundancy_group__status",
            "interface_redundancy_group__virtual_ip",
            "interface_redundancy_group__protocol",
            "interface_redundancy_group__protocol_group_id",
            "interface__device",
            "interface__name",
            "interface__status",
            "interface__label",
            "interface__enabled",
            "interface__type",
            "interface__description",
            "interface__ip_addresses",
        )

        default_columns = ("priority", "actions")


#
# Software image files
#


class SoftwareImageFileTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    image_file_name = tables.Column(linkify=True)
    software_version = tables.Column(linkify=True)
    default_image = BooleanColumn()
    device_type_count = LinkedCountColumn(
        viewname="dcim:devicetype_list",
        url_params={"software_image_files": "pk"},
        verbose_name="Device Types",
    )
    tags = TagColumn(url_name="dcim:softwareimagefile_list")
    actions = ButtonsColumn(SoftwareImageFile)

    class Meta(BaseTable.Meta):
        model = SoftwareImageFile
        fields = (
            "pk",
            "image_file_name",
            "status",
            "software_version",
            "default_image",
            "image_file_checksum",
            "hashing_algorithm",
            "download_url",
            "external_integration",
            "device_type_count",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "image_file_name",
            "status",
            "software_version",
            "default_image",
            "device_type_count",
            "tags",
            "actions",
        )


class SoftwareVersionTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    version = tables.Column(linkify=True)
    platform = tables.Column(linkify=True)
    release_date = tables.DateColumn()
    end_of_support_date = tables.DateColumn()
    software_image_file_count = LinkedCountColumn(
        viewname="dcim:softwareimagefile_list",
        url_params={"software_version": "pk"},
        verbose_name="Software Image Files",
    )
    device_count = LinkedCountColumn(
        viewname="dcim:device_list",
        url_params={"software_version": "pk"},
        verbose_name="Devices",
    )
    inventory_item_count = LinkedCountColumn(
        viewname="dcim:inventoryitem_list",
        url_params={"software_version": "pk"},
        verbose_name="Inventory Items",
    )
    long_term_support = BooleanColumn()
    pre_release = BooleanColumn()
    tags = TagColumn(url_name="dcim:softwareversion_list")
    actions = ButtonsColumn(SoftwareVersion)

    class Meta(BaseTable.Meta):
        model = SoftwareVersion
        fields = (
            "pk",
            "version",
            "alias",
            "status",
            "platform",
            "release_date",
            "end_of_support_date",
            "long_term_support",
            "pre_release",
            "documentation_url",
            "software_image_file_count",
            "device_count",
            "inventory_item_count",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "version",
            "alias",
            "platform",
            "status",
            "release_date",
            "end_of_support_date",
            "software_image_file_count",
            "device_count",
            "inventory_item_count",
            "tags",
            "actions",
        )


class ControllerTable(StatusTableMixin, RoleTableMixin, BaseTable):
    """Table for list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    platform = tables.Column(linkify=True)
    tenant = TenantColumn()
    capabilities = tables.Column()
    external_integration = tables.Column(linkify=True)
    controller_device = tables.Column(linkify=True)
    controller_device_redundancy_group = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:controller_list")
    actions = ButtonsColumn(Controller)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = Controller
        fields = (
            "pk",
            "name",
            "status",
            "location",
            "platform",
            "role",
            "tenant",
            "capabilities",
            "external_integration",
            "controller_device",
            "controller_device_redundancy_group",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "status",
            "location",
            "platform",
            "role",
            "tenant",
            "capabilities",
            "actions",
        )

    def render_capabilities(self, value):
        """Render capabilities."""
        if not value:
            return HTML_NONE
        return format_html_join(" ", '<span class="badge bg-secondary">{}</span>', ((v,) for v in value))


class ControllerManagedDeviceGroupTable(BaseTable):
    """Table for list view."""

    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=TREE_LINK, attrs={"td": {"class": "text-nowrap"}})
    weight = tables.Column()
    controller = tables.Column(linkify=True)
    tenant = TenantColumn()
    capabilities = tables.Column()
    tags = TagColumn(url_name="dcim:controllermanageddevicegroup_list")
    actions = ButtonsColumn(ControllerManagedDeviceGroup)
    device_count = LinkedCountColumn(
        viewname="dcim:device_list",
        url_params={"controller_managed_device_group": "pk"},
        verbose_name="Devices",
    )
    radio_profiles_count = LinkedCountColumn(
        viewname="wireless:radioprofile_list",
        url_params={"controller_managed_device_groups": "pk"},
        verbose_name="Radio Profiles",
    )
    wireless_networks_count = LinkedCountColumn(
        viewname="wireless:wirelessnetwork_list",
        url_params={"controller_managed_device_groups": "pk"},
        verbose_name="Wireless Networks",
    )

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = ControllerManagedDeviceGroup
        fields = (
            "pk",
            "name",
            "device_count",
            "radio_profiles_count",
            "wireless_networks_count",
            "controller",
            "weight",
            "tenant",
            "capabilities",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "device_count",
            "radio_profiles_count",
            "wireless_networks_count",
            "controller",
            "weight",
            "capabilities",
            "tags",
            "actions",
        )

    def render_capabilities(self, value):
        """Render capabilities."""
        if not value:
            return HTML_NONE
        return format_html_join(" ", '<span class="badge bg-secondary">{}</span>', ((v,) for v in value))


class VirtualDeviceContextTable(StatusTableMixin, RoleTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    tenant = TenantColumn()
    device = tables.Column(linkify=True)
    primary_ip = tables.Column(linkify=True, order_by=("primary_ip6", "primary_ip4"), verbose_name="IP Address")
    primary_ip4 = tables.Column(linkify=True, verbose_name="IPv4 Address")
    primary_ip6 = tables.Column(linkify=True, verbose_name="IPv6 Address")
    interface_count = LinkedCountColumn(
        viewname="dcim:interface_list",
        url_params={"virtual_device_contexts": "pk"},
        verbose_name="Interfaces",
    )
    tags = TagColumn(url_name="dcim:device_list")

    class Meta(BaseTable.Meta):
        model = VirtualDeviceContext
        fields = (
            "pk",
            "name",
            "identifier",
            "device",
            "status",
            "role",
            "tenant",
            "primary_ip",
            "primary_ip4",
            "primary_ip6",
            "interface_count",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "identifier",
            "device",
            "status",
            "role",
            "tenant",
            "primary_ip",
            "interface_count",
        )
