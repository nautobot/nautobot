import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.dcim.models import (
    ConsolePortTemplate,
    ConsoleServerPortTemplate,
    DeviceBayTemplate,
    DeviceType,
    FrontPortTemplate,
    InterfaceTemplate,
    Manufacturer,
    PowerOutletTemplate,
    PowerPortTemplate,
    RearPortTemplate,
)

__all__ = (
    "ConsolePortTemplateTable",
    "ConsoleServerPortTemplateTable",
    "DeviceBayTemplateTable",
    "DeviceTypeTable",
    "FrontPortTemplateTable",
    "InterfaceTemplateTable",
    "ManufacturerTable",
    "PowerOutletTemplateTable",
    "PowerPortTemplateTable",
    "RearPortTemplateTable",
)


#
# Manufacturers
#


class ManufacturerTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    device_type_count = tables.Column(verbose_name="Device Types")
    inventory_item_count = tables.Column(verbose_name="Inventory Items")
    platform_count = tables.Column(verbose_name="Platforms")
    actions = ButtonsColumn(Manufacturer)

    class Meta(BaseTable.Meta):
        model = Manufacturer
        fields = (
            "pk",
            "name",
            "device_type_count",
            "inventory_item_count",
            "platform_count",
            "description",
            "actions",
        )


#
# Device types
#


class DeviceTypeTable(BaseTable):
    pk = ToggleColumn()
    model = tables.Column(linkify=True, verbose_name="Device Type")
    is_full_depth = BooleanColumn(verbose_name="Full Depth")
    device_count = LinkedCountColumn(
        viewname="dcim:device_list",
        url_params={"device_type": "pk"},
        verbose_name="Devices",
    )
    tags = TagColumn(url_name="dcim:devicetype_list")

    class Meta(BaseTable.Meta):
        model = DeviceType
        fields = (
            "pk",
            "model",
            "manufacturer",
            "part_number",
            "u_height",
            "is_full_depth",
            "subdevice_role",
            "device_count",
            "tags",
        )
        default_columns = (
            "pk",
            "model",
            "manufacturer",
            "part_number",
            "u_height",
            "is_full_depth",
            "device_count",
        )


#
# Device type components
#


class ComponentTemplateTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(order_by=("_name",))


class ConsolePortTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=ConsolePortTemplate,
        buttons=("edit", "delete"),
        return_url_extra="%23tab_consoleports",
    )

    class Meta(BaseTable.Meta):
        model = ConsolePortTemplate
        fields = ("pk", "name", "label", "type", "description", "actions")
        empty_text = "None"


class ConsoleServerPortTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=ConsoleServerPortTemplate,
        buttons=("edit", "delete"),
        return_url_extra="%23tab_consoleserverports",
    )

    class Meta(BaseTable.Meta):
        model = ConsoleServerPortTemplate
        fields = ("pk", "name", "label", "type", "description", "actions")
        empty_text = "None"


class PowerPortTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=PowerPortTemplate,
        buttons=("edit", "delete"),
        return_url_extra="%23tab_powerports",
    )

    class Meta(BaseTable.Meta):
        model = PowerPortTemplate
        fields = (
            "pk",
            "name",
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
            "actions",
        )
        empty_text = "None"


class PowerOutletTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=PowerOutletTemplate,
        buttons=("edit", "delete"),
        return_url_extra="%23tab_poweroutlets",
    )

    class Meta(BaseTable.Meta):
        model = PowerOutletTemplate
        fields = (
            "pk",
            "name",
            "label",
            "type",
            "power_port",
            "feed_leg",
            "description",
            "actions",
        )
        empty_text = "None"


class InterfaceTemplateTable(ComponentTemplateTable):
    mgmt_only = BooleanColumn(verbose_name="Management Only")
    actions = ButtonsColumn(
        model=InterfaceTemplate,
        buttons=("edit", "delete"),
        return_url_extra="%23tab_interfaces",
    )

    class Meta(BaseTable.Meta):
        model = InterfaceTemplate
        fields = ("pk", "name", "label", "mgmt_only", "type", "description", "actions")
        empty_text = "None"


class FrontPortTemplateTable(ComponentTemplateTable):
    rear_port_position = tables.Column(verbose_name="Position")
    actions = ButtonsColumn(
        model=FrontPortTemplate,
        buttons=("edit", "delete"),
        return_url_extra="%23tab_frontports",
    )

    class Meta(BaseTable.Meta):
        model = FrontPortTemplate
        fields = (
            "pk",
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "actions",
        )
        empty_text = "None"


class RearPortTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=RearPortTemplate,
        buttons=("edit", "delete"),
        return_url_extra="%23tab_rearports",
    )

    class Meta(BaseTable.Meta):
        model = RearPortTemplate
        fields = ("pk", "name", "label", "type", "positions", "description", "actions")
        empty_text = "None"


class DeviceBayTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=DeviceBayTemplate,
        buttons=("edit", "delete"),
        return_url_extra="%23tab_devicebays",
    )

    class Meta(BaseTable.Meta):
        model = DeviceBayTemplate
        fields = ("pk", "name", "label", "description", "actions")
        empty_text = "None"
