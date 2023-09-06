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
from nautobot.dcim.models import (
    ConsolePort,
    ConsoleServerPort,
    Device,
    DeviceBay,
    DeviceRedundancyGroup,
    FrontPort,
    Interface,
    InterfaceRedundancyGroup,
    InterfaceRedundancyGroupAssociation,
    InventoryItem,
    Platform,
    PowerOutlet,
    PowerPort,
    RearPort,
    VirtualChassis,
)
from nautobot.dcim.utils import cable_status_color_css
from nautobot.extras.tables import RoleTableMixin, StatusTableMixin
from nautobot.tenancy.tables import TenantColumn
from .template_code import (
    CABLETERMINATION,
    CONSOLEPORT_BUTTONS,
    CONSOLESERVERPORT_BUTTONS,
    DEVICE_LINK,
    DEVICEBAY_BUTTONS,
    DEVICEBAY_STATUS,
    FRONTPORT_BUTTONS,
    INTERFACE_BUTTONS,
    INTERFACE_IPADDRESSES,
    INTERFACE_REDUNDANCY_GROUP_INTERFACES,
    INTERFACE_REDUNDANCY_GROUP_INTERFACES_IPADDRESSES,
    INTERFACE_REDUNDANCY_GROUP_STATUS,
    INTERFACE_REDUNDANCY_INTERFACE_PRIORITY,
    INTERFACE_REDUNDANCY_INTERFACE_STATUS,
    INTERFACE_TAGGED_VLANS,
    LINKED_RECORD_COUNT,
    PATHENDPOINT,
    POWEROUTLET_BUTTONS,
    POWERPORT_BUTTONS,
    REARPORT_BUTTONS,
)

__all__ = (
    "ConsolePortTable",
    "ConsoleServerPortTable",
    "DeviceBayTable",
    "DeviceConsolePortTable",
    "DeviceConsoleServerPortTable",
    "DeviceDeviceBayTable",
    "DeviceFrontPortTable",
    "DeviceImportTable",
    "DeviceInterfaceTable",
    "DeviceInventoryItemTable",
    "DevicePowerPortTable",
    "DevicePowerOutletTable",
    "DeviceRearPortTable",
    "DeviceRedundancyGroupTable",
    "DeviceTable",
    "FrontPortTable",
    "InterfaceTable",
    "InterfaceRedundancyGroupTable",
    "InterfaceRedundancyGroupAssociationTable",
    "InventoryItemTable",
    "PlatformTable",
    "PowerOutletTable",
    "PowerPortTable",
    "RearPortTable",
    "VirtualChassisTable",
)


#
# Platforms
#


class PlatformTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
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


class DeviceTable(StatusTableMixin, RoleTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(order_by=("_name",), template_code=DEVICE_LINK)
    tenant = TenantColumn()
    location = tables.Column(linkify=True)
    rack = tables.Column(linkify=True)
    device_type = tables.LinkColumn(
        viewname="dcim:devicetype",
        args=[Accessor("device_type__pk")],
        verbose_name="Type",
        text=lambda record: record.device_type.display,
    )
    primary_ip = tables.Column(linkify=True, order_by=("primary_ip6", "primary_ip4"), verbose_name="IP Address")
    primary_ip4 = tables.Column(linkify=True, verbose_name="IPv4 Address")
    primary_ip6 = tables.Column(linkify=True, verbose_name="IPv6 Address")
    cluster = tables.LinkColumn(viewname="virtualization:cluster", args=[Accessor("cluster__pk")])
    virtual_chassis = tables.LinkColumn(viewname="dcim:virtualchassis", args=[Accessor("virtual_chassis__pk")])
    vc_position = tables.Column(verbose_name="VC Position")
    vc_priority = tables.Column(verbose_name="VC Priority")
    device_redundancy_group = tables.Column(linkify=True)
    device_redundancy_group_priority = tables.TemplateColumn(
        template_code="""{% if record.device_redundancy_group %}<span class="badge badge-default">{{ record.device_redundancy_group_priority|default:'None' }}</span>{% else %}—{% endif %}"""
    )
    secrets_group = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:device_list")

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
            "cluster",
            "virtual_chassis",
            "vc_position",
            "vc_priority",
            "device_redundancy_group",
            "device_redundancy_group_priority",
            "secrets_group",
            "tags",
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
        )


class DeviceImportTable(BaseTable):
    name = tables.TemplateColumn(template_code=DEVICE_LINK)
    status = ColoredLabelColumn()
    tenant = TenantColumn()
    location = tables.Column(linkify=True)
    rack = tables.Column(linkify=True)
    role = tables.Column(verbose_name="Role")
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
# Device components
#


class DeviceComponentTable(BaseTable):
    pk = ToggleColumn()
    device = tables.Column(linkify=True)
    name = tables.Column(linkify=True, order_by=("_name",))
    cable = tables.Column(linkify=True)

    class Meta(BaseTable.Meta):
        order_by = ("device", "name")


class CableTerminationTable(BaseTable):
    cable = tables.Column(linkify=True)
    cable_peer = tables.TemplateColumn(
        accessor="_cable_peer",
        template_code=CABLETERMINATION,
        orderable=False,
        verbose_name="Cable Peer",
    )


class PathEndpointTable(CableTerminationTable):
    connection = tables.TemplateColumn(
        accessor="_path",
        template_code=PATHENDPOINT,
        verbose_name="Connection",
        orderable=False,
    )


class ConsolePortTable(DeviceComponentTable, PathEndpointTable):
    tags = TagColumn(url_name="dcim:consoleport_list")

    class Meta(DeviceComponentTable.Meta):
        model = ConsolePort
        fields = (
            "pk",
            "device",
            "name",
            "label",
            "type",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
        )
        default_columns = ("pk", "device", "name", "label", "type", "description")


class DeviceConsolePortTable(ConsolePortTable):
    name = tables.TemplateColumn(
        template_code='<i class="mdi mdi-console"></i> <a href="{{ record.get_absolute_url }}">{{ value }}</a>',
        attrs={"td": {"class": "text-nowrap"}},
    )
    actions = ButtonsColumn(
        model=ConsolePort,
        buttons=("edit", "delete"),
        prepend_template=CONSOLEPORT_BUTTONS,
    )

    class Meta(DeviceComponentTable.Meta):
        model = ConsolePort
        fields = (
            "pk",
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
        default_columns = (
            "pk",
            "name",
            "label",
            "type",
            "description",
            "cable",
            "connection",
            "actions",
        )
        row_attrs = {
            "style": cable_status_color_css,
        }


class ConsoleServerPortTable(DeviceComponentTable, PathEndpointTable):
    tags = TagColumn(url_name="dcim:consoleserverport_list")

    class Meta(DeviceComponentTable.Meta):
        model = ConsoleServerPort
        fields = (
            "pk",
            "device",
            "name",
            "label",
            "type",
            "description",
            "cable",
            "cable_peer",
            "connection",
            "tags",
        )
        default_columns = ("pk", "device", "name", "label", "type", "description")


class DeviceConsoleServerPortTable(ConsoleServerPortTable):
    name = tables.TemplateColumn(
        template_code='<i class="mdi mdi-console-network-outline"></i> '
        '<a href="{{ record.get_absolute_url }}">{{ value }}</a>',
        attrs={"td": {"class": "text-nowrap"}},
    )
    actions = ButtonsColumn(
        model=ConsoleServerPort,
        buttons=("edit", "delete"),
        prepend_template=CONSOLESERVERPORT_BUTTONS,
    )

    class Meta(DeviceComponentTable.Meta):
        model = ConsoleServerPort
        fields = (
            "pk",
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
        default_columns = (
            "pk",
            "name",
            "label",
            "type",
            "description",
            "cable",
            "connection",
            "actions",
        )
        row_attrs = {
            "style": cable_status_color_css,
        }


class PowerPortTable(DeviceComponentTable, PathEndpointTable):
    tags = TagColumn(url_name="dcim:powerport_list")

    class Meta(DeviceComponentTable.Meta):
        model = PowerPort
        fields = (
            "pk",
            "device",
            "name",
            "label",
            "type",
            "description",
            "maximum_draw",
            "allocated_draw",
            "cable",
            "cable_peer",
            "connection",
            "tags",
        )
        default_columns = (
            "pk",
            "device",
            "name",
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
        )


class DevicePowerPortTable(PowerPortTable):
    name = tables.TemplateColumn(
        template_code='<i class="mdi mdi-power-plug-outline"></i> <a href="{{ record.get_absolute_url }}">'
        "{{ value }}</a>",
        attrs={"td": {"class": "text-nowrap"}},
    )
    actions = ButtonsColumn(model=PowerPort, buttons=("edit", "delete"), prepend_template=POWERPORT_BUTTONS)

    class Meta(DeviceComponentTable.Meta):
        model = PowerPort
        fields = (
            "pk",
            "name",
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
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
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
            "cable",
            "connection",
            "actions",
        )
        row_attrs = {"style": cable_status_color_css}


class PowerOutletTable(DeviceComponentTable, PathEndpointTable):
    power_port = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:poweroutlet_list")

    class Meta(DeviceComponentTable.Meta):
        model = PowerOutlet
        fields = (
            "pk",
            "device",
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
        )
        default_columns = (
            "pk",
            "device",
            "name",
            "label",
            "type",
            "power_port",
            "feed_leg",
            "description",
        )


class DevicePowerOutletTable(PowerOutletTable):
    name = tables.TemplateColumn(
        template_code='<i class="mdi mdi-power-socket"></i> <a href="{{ record.get_absolute_url }}">{{ value }}</a>',
        attrs={"td": {"class": "text-nowrap"}},
    )
    actions = ButtonsColumn(
        model=PowerOutlet,
        buttons=("edit", "delete"),
        prepend_template=POWEROUTLET_BUTTONS,
    )

    class Meta(DeviceComponentTable.Meta):
        model = PowerOutlet
        fields = (
            "pk",
            "name",
            "label",
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
            "type",
            "power_port",
            "feed_leg",
            "description",
            "cable",
            "connection",
            "actions",
        )
        row_attrs = {"style": cable_status_color_css}


class BaseInterfaceTable(BaseTable):
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


class InterfaceTable(StatusTableMixin, DeviceComponentTable, BaseInterfaceTable, PathEndpointTable):
    mgmt_only = BooleanColumn()
    tags = TagColumn(url_name="dcim:interface_list")

    class Meta(DeviceComponentTable.Meta):
        model = Interface
        fields = (
            "pk",
            "device",
            "name",
            "status",
            "label",
            "enabled",
            "type",
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
        )
        default_columns = (
            "pk",
            "device",
            "name",
            "status",
            "label",
            "enabled",
            "type",
            "description",
        )


class DeviceInterfaceTable(InterfaceTable):
    name = tables.TemplateColumn(
        template_code='<i class="mdi mdi-{% if iface.mgmt_only %}wrench{% elif iface.is_lag %}drag-horizontal-variant'
        "{% elif iface.is_virtual %}circle{% elif iface.is_wireless %}wifi{% else %}ethernet"
        '{% endif %}"></i> <a href="{{ record.get_absolute_url }}">{{ value }}</a>',
        attrs={"td": {"class": "text-nowrap"}},
    )
    parent_interface = tables.Column(linkify=True, verbose_name="Parent")
    bridge = tables.Column(linkify=True)
    lag = tables.Column(linkify=True, verbose_name="LAG")
    actions = ButtonsColumn(model=Interface, buttons=("edit", "delete"), prepend_template=INTERFACE_BUTTONS)

    class Meta(DeviceComponentTable.Meta):
        model = Interface
        fields = (
            "pk",
            "name",
            "status",
            "device",
            "label",
            "enabled",
            "type",
            "parent_interface",
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
            "actions",
        )
        default_columns = [
            "pk",
            "name",
            "status",
            "label",
            "enabled",
            "type",
            "parent_interface",
            "lag",
            "mtu",
            "vrf",
            "mode",
            "description",
            "ip_addresses",
            "cable",
            "connection",
            "actions",
        ]
        row_attrs = {
            "style": cable_status_color_css,
            "data-name": lambda record: record.name,
        }


class FrontPortTable(DeviceComponentTable, CableTerminationTable):
    rear_port_position = tables.Column(verbose_name="Position")
    rear_port = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:frontport_list")

    class Meta(DeviceComponentTable.Meta):
        model = FrontPort
        fields = (
            "pk",
            "device",
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "cable",
            "cable_peer",
            "tags",
        )
        default_columns = (
            "pk",
            "device",
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
        )


class DeviceFrontPortTable(FrontPortTable):
    name = tables.TemplateColumn(
        template_code='<i class="mdi mdi-square-rounded{% if not record.cable %}-outline{% endif %}"></i> '
        '<a href="{{ record.get_absolute_url }}">{{ value }}</a>',
        attrs={"td": {"class": "text-nowrap"}},
    )
    actions = ButtonsColumn(model=FrontPort, buttons=("edit", "delete"), prepend_template=FRONTPORT_BUTTONS)

    class Meta(DeviceComponentTable.Meta):
        model = FrontPort
        fields = (
            "pk",
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
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "cable",
            "cable_peer",
            "actions",
        )
        row_attrs = {"style": cable_status_color_css}


class RearPortTable(DeviceComponentTable, CableTerminationTable):
    tags = TagColumn(url_name="dcim:rearport_list")

    class Meta(DeviceComponentTable.Meta):
        model = RearPort
        fields = (
            "pk",
            "device",
            "name",
            "label",
            "type",
            "positions",
            "description",
            "cable",
            "cable_peer",
            "tags",
        )
        default_columns = ("pk", "device", "name", "label", "type", "description")


class DeviceRearPortTable(RearPortTable):
    name = tables.TemplateColumn(
        template_code='<i class="mdi mdi-square-rounded{% if not record.cable %}-outline{% endif %}"></i> '
        '<a href="{{ record.get_absolute_url }}">{{ value }}</a>',
        attrs={"td": {"class": "text-nowrap"}},
    )
    actions = ButtonsColumn(model=RearPort, buttons=("edit", "delete"), prepend_template=REARPORT_BUTTONS)

    class Meta(DeviceComponentTable.Meta):
        model = RearPort
        fields = (
            "pk",
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
        default_columns = (
            "pk",
            "name",
            "label",
            "type",
            "positions",
            "description",
            "cable",
            "cable_peer",
            "actions",
        )
        row_attrs = {"style": cable_status_color_css}


class DeviceBayTable(DeviceComponentTable):
    status = tables.TemplateColumn(template_code=DEVICEBAY_STATUS)
    installed_device = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:devicebay_list")

    class Meta(DeviceComponentTable.Meta):
        model = DeviceBay
        fields = (
            "pk",
            "device",
            "name",
            "label",
            "status",
            "installed_device",
            "description",
            "tags",
        )
        default_columns = (
            "pk",
            "device",
            "name",
            "label",
            "status",
            "installed_device",
            "description",
        )


class DeviceDeviceBayTable(DeviceBayTable):
    name = tables.TemplateColumn(
        template_code='<i class="mdi mdi-circle{% if record.installed_device %}slice-8{% else %}outline{% endif %}'
        '"></i> <a href="{{ record.get_absolute_url }}">{{ value }}</a>',
        attrs={"td": {"class": "text-nowrap"}},
    )
    actions = ButtonsColumn(model=DeviceBay, buttons=("edit", "delete"), prepend_template=DEVICEBAY_BUTTONS)

    class Meta(DeviceComponentTable.Meta):
        model = DeviceBay
        fields = (
            "pk",
            "name",
            "label",
            "status",
            "installed_device",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "label",
            "status",
            "installed_device",
            "description",
            "actions",
        )


class InventoryItemTable(DeviceComponentTable):
    manufacturer = tables.Column(linkify=True)
    discovered = BooleanColumn()
    tags = TagColumn(url_name="dcim:inventoryitem_list")
    cable = None  # Override DeviceComponentTable

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
        )


class DeviceInventoryItemTable(InventoryItemTable):
    name = tables.TemplateColumn(
        template_code='<a href="{{ record.get_absolute_url }}" style="padding-left: {{ record.tree_depth }}0px">'
        "{{ value }}</a>",
        attrs={"td": {"class": "text-nowrap"}},
    )
    actions = ButtonsColumn(model=InventoryItem, buttons=("edit", "delete"))

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
        url_params={"virtual_chassis_id": "pk"},
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
    device_count = tables.TemplateColumn(
        template_code=LINKED_RECORD_COUNT,
        verbose_name="Devices",
    )
    secrets_group = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:deviceredundancygroup_list")

    class Meta(BaseTable.Meta):
        model = DeviceRedundancyGroup
        fields = ("pk", "name", "status", "failover_strategy", "device_count", "secrets_group", "tags")
        default_columns = ("pk", "name", "status", "failover_strategy", "device_count")


#
# Interface Redundancy Group
#


class InterfaceRedundancyGroupTable(BaseTable):
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
            "description",
            "protocol",
            "protocol_group_id",
            "interfaces",
        )


class InterfaceRedundancyGroupAssociationTable(BaseTable):
    """Table for list view."""

    pk = ToggleColumn()
    interface_redundancy_group = tables.Column(linkify=True, verbose_name="Group Name")
    interface_redundancy_group__virtual_ip = tables.Column(linkify=True, verbose_name="Virtual IP")
    interface_redundancy_group__protocol_group_id = tables.Column(verbose_name="Group ID")
    priority = tables.TemplateColumn(template_code=INTERFACE_REDUNDANCY_INTERFACE_PRIORITY)
    interface__device = tables.Column(linkify=True)
    interface = tables.Column(linkify=True)
    interface__status = tables.TemplateColumn(template_code=INTERFACE_REDUNDANCY_INTERFACE_STATUS)
    interface_redundancy_group__status = tables.TemplateColumn(
        template_code=INTERFACE_REDUNDANCY_GROUP_STATUS,
        verbose_name="Group Status",
    )
    interface__ip_addresses = tables.TemplateColumn(
        template_code=INTERFACE_REDUNDANCY_GROUP_INTERFACES_IPADDRESSES,
        orderable=False,
        verbose_name="IP Addresses",
    )
    actions = ButtonsColumn(
        model=InterfaceRedundancyGroupAssociation,
        buttons=("edit", "delete"),
    )

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
