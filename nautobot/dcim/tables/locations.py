import django_tables2 as tables

from nautobot.dcim.models import Location, LocationType
from nautobot.dcim.tables.template_code import TREE_LINK
from nautobot.extras.tables import StatusTableMixin
from nautobot.tenancy.tables import TenantColumn
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
    actions = ButtonsColumn(LocationType, pk_field="slug")

    class Meta(BaseTable.Meta):
        model = LocationType
        fields = (
            "pk",
            "name",
            "slug",
            "parent",
            "content_types",
            "description",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "content_types",
            "description",
            "actions",
        )
        orderable = False


class LocationTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=TREE_LINK, orderable=False, attrs={"td": {"class": "text-nowrap"}})
    location_type = tables.Column(linkify=True)
    site = tables.Column(linkify=True)
    parent = tables.Column(linkify=True)
    tenant = TenantColumn()
    tags = TagColumn(url_name="dcim:location_list")
    actions = ButtonsColumn(Location, pk_field="slug")

    class Meta(BaseTable.Meta):
        model = Location
        fields = (
            "pk",
            "name",
            "slug",
            "status",
            "site",
            "location_type",
            "parent",
            "tenant",
            "description",
            "tags",
            "actions",
        )
        default_columns = ("pk", "name", "status", "site", "tenant", "description", "tags", "actions")
        orderable = False
