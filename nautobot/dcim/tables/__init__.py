import django_tables2 as tables
from django_tables2.utils import Accessor

from nautobot.core.tables import BaseTable, BooleanColumn
from nautobot.dcim.models import ConsolePort, Interface, PowerPort

from .cables import CableTable
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

__all__ = (
    "CableTable",
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
    "VirtualChassisTable",
    "VirtualDeviceContextTable",
)

#
# Device connections
#


class ConsoleConnectionTable(BaseTable):
    console_server = tables.Column(
        accessor=Accessor("_path__destination__parent"),
        orderable=False,
        linkify=True,
        verbose_name="Console Server",
    )
    console_server_port = tables.Column(
        accessor=Accessor("_path__destination"),
        orderable=False,
        linkify=True,
        verbose_name="Port",
    )
    device = tables.Column(linkify=True, accessor="parent", orderable=False)
    name = tables.Column(linkify=True, verbose_name="Console Port")
    reachable = BooleanColumn(accessor=Accessor("_path__is_active"), verbose_name="Reachable")

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
        accessor=Accessor("_path__destination__parent"),
        orderable=False,
        linkify=True,
        verbose_name="PDU",
    )
    outlet = tables.Column(
        accessor=Accessor("_path__destination"),
        orderable=False,
        linkify=True,
        verbose_name="Outlet",
    )
    device = tables.Column(linkify=True, accessor="parent", orderable=False)
    name = tables.Column(linkify=True, verbose_name="Power Port")
    reachable = BooleanColumn(accessor=Accessor("_path__is_active"), verbose_name="Reachable")

    class Meta(BaseTable.Meta):
        model = PowerPort
        fields = ("device", "name", "pdu", "outlet", "reachable")


class InterfaceConnectionTable(BaseTable):
    device_a = tables.Column(accessor=Accessor("parent"), linkify=True, verbose_name="Device A", orderable=False)
    interface_a = tables.Column(accessor=Accessor("name"), linkify=True, verbose_name="Interface A")
    device_b = tables.Column(
        accessor=Accessor("_path__destination__parent"),
        orderable=False,
        linkify=True,
        verbose_name="Device B",
    )
    interface_b = tables.Column(
        accessor=Accessor("_path__destination"),
        orderable=False,
        linkify=True,
        verbose_name="Interface B",
    )
    reachable = BooleanColumn(accessor=Accessor("_path__is_active"), verbose_name="Reachable")

    class Meta(BaseTable.Meta):
        model = Interface
        fields = ("device_a", "interface_a", "device_b", "interface_b", "reachable")
