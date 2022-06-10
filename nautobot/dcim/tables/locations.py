import django_tables2 as tables

from nautobot.dcim.models import Location, LocationType
from nautobot.dcim.tables.template_code import TREE_LINK
from nautobot.extras.tables import StatusTableMixin
from nautobot.utilities.tables import BaseTable, ButtonsColumn, ContentTypesColumn, TagColumn, ToggleColumn

__all__ = (
    "LocationTable",
    "LocationTypeTable",
)


class LocationTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=TREE_LINK, orderable=False, attrs={"td": {"class": "text-nowrap"}})
    content_types = ContentTypesColumn(truncate_words=15)
    parent = tables.Column(linkify=True)
    # actions = ButtonsColumn(LocationType)

    class Meta(BaseTable.Meta):
        model = LocationType
        fields = ("pk", "name", "slug", "parent", "content_types", "description", )# "actions")
        default_columns = ("pk", "name", "content_types", "description", ) # "actions")


class LocationTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=TREE_LINK, orderable=False, attrs={"td": {"class": "text-nowrap"}})
    location_type = tables.Column(linkify=True)
    parent = tables.Column(linkify=True)
    tags = TagColumn(url_name="dcim:location_list")

    class Meta(BaseTable.Meta):
        model = Location
        fields = ("pk", "name", "slug", "status", "location_type", "parent", "description", "tags")
        default_columns = ("pk", "name", "status", "location_type", "description", "tags")
