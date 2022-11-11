import django_tables2 as tables
from django_tables2.utils import Accessor

from nautobot.extras.tables import StatusTableMixin
from nautobot.tenancy.tables import TenantColumn
from nautobot.utilities.tables import (
    BaseTable,
    ButtonsColumn,
    TagColumn,
    ToggleColumn,
)
from .models import Circuit, CircuitType, Provider, ProviderNetwork

CIRCUIT_TERMINATION_PARENT = """
{% load helpers %}
{% if value.provider_network %}
{{ value.provider_network|hyperlinked_object }}
{% elif value.site %}
{{ value.site|hyperlinked_object }}
{% else %}
{{ None|placeholder }}
{% endif %}
"""

#
# Provider Network
#


class ProviderNetworkTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    provider = tables.Column(linkify=True)
    tags = TagColumn(url_name="circuits:providernetwork_list")

    class Meta(BaseTable.Meta):
        model = ProviderNetwork
        fields = ("pk", "name", "provider", "description", "tags")
        default_columns = ("pk", "name", "provider", "description")


#
# Providers
#


class ProviderTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    circuit_count = tables.Column(accessor=Accessor("count_circuits"), verbose_name="Circuits")
    tags = TagColumn(url_name="circuits:provider_list")

    class Meta(BaseTable.Meta):
        model = Provider
        fields = (
            "pk",
            "name",
            "asn",
            "account",
            "portal_url",
            "noc_contact",
            "admin_contact",
            "circuit_count",
            "tags",
        )
        default_columns = ("pk", "name", "asn", "account", "circuit_count")


#
# Circuit types
#


class CircuitTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    circuit_count = tables.Column(verbose_name="Circuits")
    actions = ButtonsColumn(CircuitType, pk_field="slug")

    class Meta(BaseTable.Meta):
        model = CircuitType
        fields = ("pk", "name", "circuit_count", "description", "slug", "actions")
        default_columns = (
            "pk",
            "name",
            "circuit_count",
            "description",
            "slug",
            "actions",
        )


#
# Circuits
#


class CircuitTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    cid = tables.LinkColumn(verbose_name="ID")
    provider = tables.LinkColumn(viewname="circuits:provider", args=[Accessor("provider__slug")])
    tenant = TenantColumn()
    tags = TagColumn(url_name="circuits:circuit_list")

    termination_a = tables.TemplateColumn(
        template_code=CIRCUIT_TERMINATION_PARENT,
        accessor=Accessor("termination_a"),
        orderable=False,
        verbose_name="Side A",
    )
    termination_z = tables.TemplateColumn(
        template_code=CIRCUIT_TERMINATION_PARENT,
        accessor=Accessor("termination_z"),
        orderable=False,
        verbose_name="Side Z",
    )

    class Meta(BaseTable.Meta):
        model = Circuit
        fields = (
            "pk",
            "cid",
            "provider",
            "type",
            "status",
            "tenant",
            "termination_a",
            "termination_z",
            "install_date",
            "commit_rate",
            "description",
            "tags",
        )
        default_columns = (
            "pk",
            "cid",
            "provider",
            "type",
            "status",
            "tenant",
            "termination_a",
            "termination_z",
            "description",
        )
