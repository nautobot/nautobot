import django_tables2 as tables
from django_tables2.utils import Accessor

from nautobot.core.tables import BaseTable, BooleanColumn
from nautobot.dcim.models import CablePath, ConsolePort, PowerPort

from .cables import CableTable, CableTypeTable
from .devices import (
    ConsolePortTable,
    ConsoleServerPortTable,
    ControllerManagedDeviceGroupTable,
    ControllerTable,
    DeviceBayTable,
    DeviceDeviceBayTable,
    DeviceImportTable,
    DeviceInventoryItemTable,
    DeviceModuleBayTable,
    DeviceModuleConsolePortTable,
    DeviceModuleConsoleServerPortTable,
    DeviceModuleFrontPortTable,
    DeviceModuleInterfaceTable,
    DeviceModulePowerOutletTable,
    DeviceModulePowerPortTable,
    DeviceModuleRearPortTable,
    DeviceRedundancyGroupTable,
    DeviceTable,
    FrontPortTable,
    InterfaceRedundancyGroupAssociationTable,
    InterfaceRedundancyGroupTable,
    InterfaceTable,
    InventoryItemTable,
    ModuleBayTable,
    ModuleFamilyTable,
    ModuleModuleBayTable,
    ModuleTable,
    PlatformTable,
    PowerOutletTable,
    PowerPortTable,
    RearPortTable,
    SoftwareImageFileTable,
    SoftwareVersionTable,
    VirtualChassisMembersTable,
    VirtualChassisTable,
    VirtualDeviceContextTable,
)
from .devicetypes import (
    ConsolePortTemplateTable,
    ConsoleServerPortTemplateTable,
    DeviceBayTemplateTable,
    DeviceFamilyTable,
    DeviceTypeTable,
    FrontPortTemplateTable,
    InterfaceTemplateTable,
    ManufacturerTable,
    ModuleBayTemplateTable,
    ModuleTypeTable,
    PowerOutletTemplateTable,
    PowerPortTemplateTable,
    RearPortTemplateTable,
)
from .locations import LocationTable, LocationTypeTable
from .power import PowerFeedTable, PowerPanelTable
from .racks import (
    RackDetailTable,
    RackGroupTable,
    RackReservationTable,
    RackTable,
)
from .template_code import INTERFACE_CONNECTION_DEVICE_A, INTERFACE_CONNECTION_INTERFACE_A

__all__ = (
    "CableTable",
    "CableTypeTable",
    "ConsoleConnectionTable",
    "ConsolePortTable",
    "ConsolePortTemplateTable",
    "ConsoleServerPortTable",
    "ConsoleServerPortTemplateTable",
    "ControllerManagedDeviceGroupTable",
    "ControllerTable",
    "DeviceBayTable",
    "DeviceBayTemplateTable",
    "DeviceDeviceBayTable",
    "DeviceFamilyTable",
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
    "DeviceTypeTable",
    "FrontPortTable",
    "FrontPortTemplateTable",
    "InterfaceConnectionTable",
    "InterfaceRedundancyGroupAssociationTable",
    "InterfaceRedundancyGroupTable",
    "InterfaceTable",
    "InterfaceTemplateTable",
    "InventoryItemTable",
    "LocationTable",
    "LocationTypeTable",
    "ManufacturerTable",
    "ModuleBayTable",
    "ModuleBayTemplateTable",
    "ModuleFamilyTable",
    "ModuleModuleBayTable",
    "ModuleTable",
    "ModuleTypeTable",
    "PlatformTable",
    "PowerConnectionTable",
    "PowerFeedTable",
    "PowerOutletTable",
    "PowerOutletTemplateTable",
    "PowerPanelTable",
    "PowerPortTable",
    "PowerPortTemplateTable",
    "RackDetailTable",
    "RackGroupTable",
    "RackReservationTable",
    "RackTable",
    "RearPortTable",
    "RearPortTemplateTable",
    "SoftwareImageFileTable",
    "SoftwareVersionTable",
    "VirtualChassisMembersTable",
    "VirtualChassisTable",
    "VirtualDeviceContextTable",
)


#
# Device connections
#


class ConsoleConnectionTable(BaseTable):
    console_server = tables.Column(
        # We cannot use `cable_paths__...` here because it would traverse a related manager, which is not a single object.
        accessor=Accessor("path__destination__parent"),
        orderable=False,
        linkify=True,
        verbose_name="Console Server",
    )
    console_server_port = tables.Column(
        accessor=Accessor("path__destination"),
        orderable=False,
        linkify=True,
        verbose_name="Port",
    )
    device = tables.Column(linkify=True, accessor="parent", orderable=False)
    name = tables.Column(linkify=True, verbose_name="Console Port")
    # `order_by` is the ORM equivalent of the `path__is_active` accessor: `path` is a Python property
    # and cannot be sorted on, but the underlying relation can, so this column stays sortable.
    reachable = BooleanColumn(
        accessor=Accessor("path__is_active"), order_by="cable_paths__is_active", verbose_name="Reachable"
    )

    class Meta(BaseTable.Meta):
        model = ConsolePort
        fields = (
            "device",
            "name",
            "console_server",
            "console_server_port",
            "reachable",
        )


class PowerConnectionTable(BaseTable):
    pdu = tables.Column(
        # We cannot use `cable_paths__...` here because it would traverse a related manager, which is not a single object.
        accessor=Accessor("path__destination__parent"),
        orderable=False,
        linkify=True,
        verbose_name="PDU",
    )
    outlet = tables.Column(
        accessor=Accessor("path__destination"),
        orderable=False,
        linkify=True,
        verbose_name="Outlet",
    )
    device = tables.Column(linkify=True, accessor="parent", orderable=False)
    name = tables.Column(linkify=True, verbose_name="Power Port")
    # `order_by` is the ORM equivalent of the `path__is_active` accessor: `path` is a Python property
    # and cannot be sorted on, but the underlying relation can, so this column stays sortable.
    reachable = BooleanColumn(
        accessor=Accessor("path__is_active"), order_by="cable_paths__is_active", verbose_name="Reachable"
    )

    class Meta(BaseTable.Meta):
        model = PowerPort
        fields = ("device", "name", "pdu", "outlet", "reachable")


class InterfaceConnectionTable(BaseTable):
    """Table over `CablePath` rows representing interface-to-interface connections.

    A breakout cable's lanes are canonicalized so the trunk is always the origin (A side) and its N
    lanes are consecutive rows; the trunk device/interface is shown once (blanked on continuation
    rows) while each fan-out endpoint appears on its own row on the B side.
    """

    device_a = tables.TemplateColumn(
        template_code=INTERFACE_CONNECTION_DEVICE_A, orderable=False, verbose_name="Device A"
    )
    interface_a = tables.TemplateColumn(
        template_code=INTERFACE_CONNECTION_INTERFACE_A, orderable=False, verbose_name="Interface A"
    )
    device_b = tables.Column(
        accessor=Accessor("destination__parent"), orderable=False, linkify=True, verbose_name="Device B"
    )
    interface_b = tables.Column(
        accessor=Accessor("destination"), orderable=False, linkify=True, verbose_name="Interface B"
    )
    reachable = BooleanColumn(accessor=Accessor("is_active"), verbose_name="Reachable")

    class Meta(BaseTable.Meta):
        model = CablePath
        fields = ("device_a", "interface_a", "device_b", "interface_b", "reachable")
        default_columns = ("device_a", "interface_a", "device_b", "interface_b", "reachable")
