import django_tables2 as tables
from django_tables2.utils import Accessor

from nautobot.dcim.models import Rack, RackGroup, RackReservation, RackRole
from nautobot.extras.tables import StatusTableMixin
from nautobot.tenancy.tables import TenantColumn
from nautobot.utilities.tables import (
    BaseTable,
    ButtonsColumn,
    ColorColumn,
    ColoredLabelColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from .template_code import MPTT_LINK, RACKGROUP_ELEVATIONS, UTILIZATION_GRAPH

__all__ = (
    "RackTable",
    "RackDetailTable",
    "RackGroupTable",
    "RackReservationTable",
    "RackRoleTable",
)


#
# Rack groups
#


class RackGroupTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=MPTT_LINK, orderable=False, attrs={"td": {"class": "text-nowrap"}})
    site = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    rack_count = tables.Column(verbose_name="Racks")
    actions = ButtonsColumn(model=RackGroup, prepend_template=RACKGROUP_ELEVATIONS)

    class Meta(BaseTable.Meta):
        model = RackGroup
        fields = ("pk", "name", "site", "location", "rack_count", "description", "slug", "actions")
        default_columns = ("pk", "name", "site", "location", "rack_count", "description", "actions")


#
# Rack roles
#


class RackRoleTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    rack_count = tables.Column(verbose_name="Racks")
    color = ColorColumn()
    actions = ButtonsColumn(RackRole)

    class Meta(BaseTable.Meta):
        model = RackRole
        fields = ("pk", "name", "rack_count", "color", "description", "slug", "actions")
        default_columns = (
            "pk",
            "name",
            "rack_count",
            "color",
            "description",
            "actions",
        )


#
# Racks
#


class RackTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.Column(order_by=("_name",), linkify=True)
    group = tables.Column(linkify=True)
    site = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    tenant = TenantColumn()
    role = ColoredLabelColumn()
    u_height = tables.TemplateColumn(template_code="{{ record.u_height }}U", verbose_name="Height")

    class Meta(BaseTable.Meta):
        model = Rack
        fields = (
            "pk",
            "name",
            "site",
            "location",
            "group",
            "status",
            "facility_id",
            "tenant",
            "role",
            "serial",
            "asset_tag",
            "type",
            "width",
            "u_height",
        )
        default_columns = (
            "pk",
            "name",
            "site",
            "location",
            "group",
            "status",
            "facility_id",
            "tenant",
            "role",
            "u_height",
        )


class RackDetailTable(RackTable):
    device_count = LinkedCountColumn(
        viewname="dcim:device_list",
        url_params={"rack_id": "pk"},
        verbose_name="Devices",
    )
    get_utilization = tables.TemplateColumn(template_code=UTILIZATION_GRAPH, orderable=False, verbose_name="Space")
    get_power_utilization = tables.TemplateColumn(
        template_code=UTILIZATION_GRAPH, orderable=False, verbose_name="Power"
    )
    tags = TagColumn(url_name="dcim:rack_list")

    class Meta(RackTable.Meta):
        fields = (
            "pk",
            "name",
            "site",
            "location",
            "group",
            "status",
            "facility_id",
            "tenant",
            "role",
            "serial",
            "asset_tag",
            "type",
            "width",
            "u_height",
            "device_count",
            "get_utilization",
            "get_power_utilization",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "site",
            "location",
            "group",
            "status",
            "facility_id",
            "tenant",
            "role",
            "u_height",
            "device_count",
            "get_utilization",
            "get_power_utilization",
        )


#
# Rack reservations
#


class RackReservationTable(BaseTable):
    pk = ToggleColumn()
    reservation = tables.Column(accessor="pk", linkify=True)
    site = tables.Column(accessor=Accessor("rack__site"), linkify=True)
    location = tables.Column(accessor=Accessor("rack__location"), linkify=True)
    tenant = TenantColumn()
    rack = tables.Column(linkify=True)
    unit_list = tables.Column(orderable=False, verbose_name="Units")
    tags = TagColumn(url_name="dcim:rackreservation_list")
    actions = ButtonsColumn(RackReservation)

    class Meta(BaseTable.Meta):
        model = RackReservation
        fields = (
            "pk",
            "reservation",
            "site",
            "location",
            "rack",
            "unit_list",
            "user",
            "created",
            "tenant",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "reservation",
            "site",
            "location",
            "rack",
            "unit_list",
            "user",
            "description",
            "actions",
        )
