import django_tables2 as tables

from nautobot.dcim.models import Region, Site
from nautobot.extras.tables import StatusTableMixin
from nautobot.tenancy.tables import TenantColumn
from nautobot.utilities.tables import (
    BaseTable,
    ButtonsColumn,
    TagColumn,
    ToggleColumn,
)
from .template_code import MPTT_LINK

__all__ = (
    "RegionTable",
    "SiteTable",
)


#
# Regions
#


class RegionTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=MPTT_LINK, attrs={"td": {"class": "text-nowrap"}})
    site_count = tables.Column(verbose_name="Sites")
    actions = ButtonsColumn(Region)

    class Meta(BaseTable.Meta):
        model = Region
        fields = ("pk", "name", "slug", "site_count", "description", "actions")
        default_columns = ("pk", "name", "site_count", "description", "actions")


#
# Sites
#


class SiteTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn(order_by=("_name",))
    region = tables.Column(linkify=True)
    tenant = TenantColumn()
    tags = TagColumn(url_name="dcim:site_list")

    class Meta(BaseTable.Meta):
        model = Site
        fields = (
            "pk",
            "name",
            "slug",
            "status",
            "facility",
            "region",
            "tenant",
            "asn",
            "time_zone",
            "description",
            "physical_address",
            "shipping_address",
            "latitude",
            "longitude",
            "contact_name",
            "contact_phone",
            "contact_email",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "status",
            "facility",
            "region",
            "tenant",
            "asn",
            "description",
        )
