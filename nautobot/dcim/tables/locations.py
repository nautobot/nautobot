import django_tables2 as tables

from nautobot.dcim.models import Location, LocationType
from nautobot.dcim.tables.template_code import MPTT_LINK
from nautobot.extras.tables import StatusTableMixin
from nautobot.utilities.tables import BaseTable, ButtonsColumn, TagColumn, ToggleColumn

__all__ = (
    "LocationTable",
    "LocationTypeTable",
)


class LocationTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=MPTT_LINK, orderable=False, attrs={"td": {"class": "text-nowrap"}})
    # actions = ButtonsColumn(LocationType)

    class Meta(BaseTable.Meta):
        model = LocationType
        fields = ("pk", "name", "slug", "parent", "description", )# "actions")
        default_columns = ("pk", "name", "parent", "description", ) # "actions")


class LocationTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=MPTT_LINK, orderable=False, attrs={"td": {"class": "text-nowrap"}})
    location_type = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:location_list")

    class Meta(BaseTable.Meta):
        model = Location
        fields = ("pk", "name", "slug", "status", "location_type", "parent", "description", "tags")
        default_columns = ("pk", "name", "status", "location_type", "parent", "description", "tags")
