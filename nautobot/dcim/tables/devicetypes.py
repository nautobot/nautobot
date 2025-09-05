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
    DeviceFamily,
    DeviceType,
    FrontPortTemplate,
    InterfaceTemplate,
    Manufacturer,
    ModuleBayTemplate,
    ModuleType,
    PowerOutletTemplate,
    PowerPortTemplate,
    RearPortTemplate,
)

__all__ = (
    "ConsolePortTemplateTable",
    "ConsoleServerPortTemplateTable",
    "DeviceBayTemplateTable",
    "DeviceFamilyTable",
    "DeviceTypeTable",
    "FrontPortTemplateTable",
    "InterfaceTemplateTable",
    "ManufacturerTable",
    "ModuleBayTemplateTable",
    "ModuleTypeTable",
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
    cloud_account_count = LinkedCountColumn(
        viewname="cloud:cloudaccount_list", url_params={"provider": "name"}, verbose_name="Cloud Accounts"
    )
    device_type_count = LinkedCountColumn(
        viewname="dcim:devicetype_list", url_params={"manufacturer": "name"}, verbose_name="Device Types"
    )
    inventory_item_count = LinkedCountColumn(
        viewname="dcim:inventoryitem_list", url_params={"manufacturer": "name"}, verbose_name="Inventory Items"
    )
    platform_count = LinkedCountColumn(
        viewname="dcim:platform_list", url_params={"manufacturer": "name"}, verbose_name="Platforms"
    )
    actions = ButtonsColumn(Manufacturer)

    class Meta(BaseTable.Meta):
        model = Manufacturer
        fields = (
            "pk",
            "name",
            "cloud_account_count",
            "device_type_count",
            "inventory_item_count",
            "platform_count",
            "description",
            "actions",
        )


#
# Device Family
#


class DeviceFamilyTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    device_type_count = LinkedCountColumn(
        viewname="dcim:devicetype_list", url_params={"device_family": "name"}, verbose_name="Device Types"
    )
    actions = ButtonsColumn(DeviceFamily)
    tags = TagColumn(url_name="dcim:devicefamily_list")

    class Meta(BaseTable.Meta):
        model = DeviceFamily
        fields = (
            "pk",
            "name",
            "device_type_count",
            "description",
            "actions",
            "tags",
        )


#
# Device types
#


class DeviceTypeTable(BaseTable):
    pk = ToggleColumn()
    manufacturer = tables.Column(linkify=True)
    model = tables.Column(linkify=True, verbose_name="Device Type")
    device_family = tables.Column(linkify=True)
    is_full_depth = BooleanColumn(verbose_name="Full Depth")
    device_count = LinkedCountColumn(
        viewname="dcim:device_list",
        url_params={"device_type": "pk"},
        verbose_name="Devices",
    )
    tags = TagColumn(url_name="dcim:devicetype_list")
    actions = ButtonsColumn(DeviceType)

    class Meta(BaseTable.Meta):
        model = DeviceType
        fields = (
            "pk",
            "model",
            "manufacturer",
            "device_family",
            "part_number",
            "u_height",
            "is_full_depth",
            "subdevice_role",
            "device_count",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "model",
            "manufacturer",
            "part_number",
            "u_height",
            "is_full_depth",
            "device_count",
            "actions",
        )


#
# Module types
#


class ModuleTypeTable(BaseTable):
    pk = ToggleColumn()
    manufacturer = tables.Column(linkify=True)
    model = tables.Column(linkify=True, verbose_name="Module Type")
    module_family = tables.Column(linkify=True, verbose_name="Family")
    module_count = LinkedCountColumn(
        viewname="dcim:module_list",
        url_params={"module_type": "pk"},
        verbose_name="Modules",
    )
    tags = TagColumn(url_name="dcim:moduletype_list")

    class Meta(BaseTable.Meta):
        model = ModuleType
        fields = (
            "pk",
            "model",
            "manufacturer",
            "part_number",
            "module_family",
            "module_count",
            "tags",
        )
        default_columns = (
            "pk",
            "model",
            "manufacturer",
            "part_number",
            "module_family",
            "module_count",
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
        return_url_extra=r"%3Ftab=consoleports",
    )

    class Meta(BaseTable.Meta):
        model = ConsolePortTemplate
        fields = ("pk", "name", "label", "type", "description", "actions")
        empty_text = "None"


class ConsoleServerPortTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=ConsoleServerPortTemplate,
        buttons=("edit", "delete"),
        return_url_extra=r"%3Ftab=consoleserverports",
    )

    class Meta(BaseTable.Meta):
        model = ConsoleServerPortTemplate
        fields = ("pk", "name", "label", "type", "description", "actions")
        empty_text = "None"


class PowerPortTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=PowerPortTemplate,
        buttons=("edit", "delete"),
        return_url_extra=r"%3Ftab=powerports",
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
            "power_factor",
            "description",
            "actions",
        )
        empty_text = "None"


class PowerOutletTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=PowerOutletTemplate,
        buttons=("edit", "delete"),
        return_url_extra=r"%3Ftab=poweroutlets",
    )

    class Meta(BaseTable.Meta):
        model = PowerOutletTemplate
        fields = (
            "pk",
            "name",
            "label",
            "type",
            "power_port_template",
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
        return_url_extra=r"%3Ftab=interfaces",
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
        return_url_extra=r"%3Ftab=frontports",
    )

    class Meta(BaseTable.Meta):
        model = FrontPortTemplate
        fields = (
            "pk",
            "name",
            "label",
            "type",
            "rear_port_template",
            "rear_port_position",
            "description",
            "actions",
        )
        empty_text = "None"


class RearPortTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=RearPortTemplate,
        buttons=("edit", "delete"),
        return_url_extra=r"%3Ftab=rearports",
    )

    class Meta(BaseTable.Meta):
        model = RearPortTemplate
        fields = ("pk", "name", "label", "type", "positions", "description", "actions")
        empty_text = "None"


class DeviceBayTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=DeviceBayTemplate,
        buttons=("edit", "delete"),
        return_url_extra=r"%3Ftab=devicebays",
    )

    class Meta(BaseTable.Meta):
        model = DeviceBayTemplate
        fields = ("pk", "name", "label", "description", "actions")
        empty_text = "None"


class ModuleBayTemplateTable(ComponentTemplateTable):
    actions = ButtonsColumn(
        model=ModuleBayTemplate,
        buttons=("edit", "delete"),
        return_url_extra=r"%3Ftab=modulebays",
    )
    module_family = tables.Column(verbose_name="Family", linkify=True)
    requires_first_party_modules = BooleanColumn(verbose_name="Requires First-Party Modules")

    class Meta(BaseTable.Meta):
        model = ModuleBayTemplate
        fields = (
            "pk",
            "name",
            "position",
            "module_family",
            "label",
            "requires_first_party_modules",
            "description",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "position",
            "module_family",
            "label",
            "requires_first_party_modules",
            "description",
            "actions",
        )
        field_order = (
            "pk",
            "name",
            "position",
            "module_family",
            "label",
            "requires_first_party_modules",
            "description",
            "actions",
        )
        empty_text = "None"
