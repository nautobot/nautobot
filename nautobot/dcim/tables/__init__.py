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
    """Table over `ConsolePort` rows representing console-port-to-console-server-port connections.

    The peer (B) side is reached through `PathEndpoint.path`, a property returning
    `cable_paths.first()`. It must NOT be written as `cable_paths__...`: `Accessor.resolve()` walks
    Python attributes, so `cable_paths` yields a related *manager* with no `destination`/`is_active`
    attribute, and the failed lookup is swallowed into a placeholder (see nautobot#9341). A
    ConsolePort has at most one `CablePath` -- `BREAKOUT_COMPATIBLE_TERMINATION_TYPES` excludes
    console terminations -- so `first()` is the whole path, not an arbitrary one of several.
    """

    console_server = tables.Column(
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
    """Table over `PowerPort` rows representing power-port-to-power-outlet/feed connections.

    As with `ConsoleConnectionTable`, the peer (B) side goes through the `PathEndpoint.path` property
    rather than `cable_paths__...`, which cannot resolve through a related manager (nautobot#9341).
    The `pdu` column is the peer's `parent`: a `Device` for a `PowerOutlet`, a `PowerPanel` for a
    `PowerFeed`.
    """

    pdu = tables.Column(
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
