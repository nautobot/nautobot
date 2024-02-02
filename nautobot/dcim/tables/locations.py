import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    ContentTypesColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.dcim.models import Location, LocationType
from nautobot.dcim.tables.template_code import TREE_LINK
from nautobot.extras.tables import StatusTableMixin
from nautobot.tenancy.tables import TenantColumn

__all__ = (
    "LocationTable",
    "LocationTypeTable",
)


class LocationTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=TREE_LINK, attrs={"td": {"class": "text-nowrap"}})
    parent = tables.Column(linkify=True)
    nestable = BooleanColumn()
    content_types = ContentTypesColumn(truncate_words=15)
    actions = ButtonsColumn(LocationType)

    class Meta(BaseTable.Meta):
        model = LocationType
        fields = (
            "pk",
            "name",
            "parent",
            "nestable",
            "content_types",
            "description",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "nestable",
            "content_types",
            "description",
            "actions",
        )


class LocationTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=TREE_LINK, attrs={"td": {"class": "text-nowrap"}})
    location_type = tables.Column(linkify=True)
    parent = tables.Column(linkify=True)
    tenant = TenantColumn()
    tags = TagColumn(url_name="dcim:location_list")
    actions = ButtonsColumn(Location)

    class Meta(BaseTable.Meta):
        model = Location
        fields = (
            "pk",
            "name",
            "status",
            "location_type",
            "parent",
            "tenant",
            "description",
            "facility",
            "asn",
            "time_zone",
            "physical_address",
            "shipping_address",
            "latitude",
            "longitude",
            "contact_name",
            "contact_phone",
            "contact_email",
            "tags",
            "actions",
        )
        default_columns = ("pk", "name", "status", "parent", "tenant", "description", "tags", "actions")
