import django_tables2 as tables

from nautobot.utilities.tables import (
    BaseTable,
    ButtonsColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from .models import Tenant, TenantGroup

MPTT_LINK = """
{% for i in record.get_ancestors %}
    <i class="mdi mdi-circle-small"></i>
{% endfor %}
<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
"""


#
# Table columns
#


class TenantColumn(tables.TemplateColumn):
    """
    Column for linking to a record's associated Tenant, or failing that, it's associated VRF's tenant.
    """

    template_code = """
    {% if record.tenant %}
        <a href="{{ record.tenant.get_absolute_url }}" title="{{ record.tenant.description }}">{{ record.tenant }}</a>
    {% elif record.vrf.tenant %}
        <a href="{{ record.vrf.tenant.get_absolute_url }}" title="{{ record.vrf.tenant.description }}">{{ record.vrf.tenant }}</a>*
    {% else %}
        &mdash;
    {% endif %}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(template_code=self.template_code, *args, **kwargs)

    def value(self, **kwargs):
        return str(kwargs["value"]) if kwargs["value"] else None


#
# Tenant groups
#


class TenantGroupTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=MPTT_LINK, attrs={"td": {"class": "text-nowrap"}})
    tenant_count = LinkedCountColumn(
        viewname="tenancy:tenant_list",
        url_params={"group": "slug"},
        verbose_name="Tenants",
    )
    actions = ButtonsColumn(TenantGroup, pk_field="slug")

    class Meta(BaseTable.Meta):
        model = TenantGroup
        fields = ("pk", "name", "tenant_count", "description", "slug", "actions")
        default_columns = ("pk", "name", "tenant_count", "description", "actions")


#
# Tenants
#


class TenantTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    group = tables.Column(linkify=True)
    tags = TagColumn(url_name="tenancy:tenant_list")

    class Meta(BaseTable.Meta):
        model = Tenant
        fields = ("pk", "name", "slug", "group", "description", "tags")
        default_columns = ("pk", "name", "group", "description")
