import django_tables2 as tables
from django_tables2.utils import Accessor

from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.extras.tables import StatusTableMixin
from nautobot.tenancy.tables import TenantColumn
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork

CIRCUIT_TERMINATION_PARENT = """
{% load helpers %}
{% if value.provider_network %}
{{ value.provider_network|hyperlinked_object }}
{% elif value.location %}
{{ value.location|hyperlinked_object }}
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
    actions = ButtonsColumn(CircuitType)

    class Meta(BaseTable.Meta):
        model = CircuitType
        fields = ("pk", "name", "circuit_count", "description", "actions")
        default_columns = (
            "pk",
            "name",
            "circuit_count",
            "description",
            "actions",
        )


#
# Circuits
#


class CircuitTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    cid = tables.LinkColumn(verbose_name="ID")
    provider = tables.Column(linkify=True)
    tenant = TenantColumn()
    tags = TagColumn(url_name="circuits:circuit_list")

    circuit_termination_a = tables.TemplateColumn(
        template_code=CIRCUIT_TERMINATION_PARENT,
        accessor=Accessor("circuit_termination_a"),
        orderable=False,
        verbose_name="Side A",
    )
    circuit_termination_z = tables.TemplateColumn(
        template_code=CIRCUIT_TERMINATION_PARENT,
        accessor=Accessor("circuit_termination_z"),
        orderable=False,
        verbose_name="Side Z",
    )

    class Meta(BaseTable.Meta):
        model = Circuit
        fields = (
            "pk",
            "cid",
            "provider",
            "circuit_type",
            "status",
            "tenant",
            "circuit_termination_a",
            "circuit_termination_z",
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
            "circuit_termination_a",
            "circuit_termination_z",
            "description",
        )


#
# Circuit Terminations
#


class CircuitTerminationTable(BaseTable):
    pk = ToggleColumn()
    circuit = tables.Column(linkify=True)
    term_side = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    provider_network = tables.Column(linkify=True)
    cable = tables.Column(linkify=True)

    class Meta(BaseTable.Meta):
        model = CircuitTermination
        fields = (
            "pk",
            "circuit",
            "term_side",
            "location",
            "provider_network",
            "cable",
            "port_speed",
            "upstream_speed",
            "xconnect_id",
            "pp_info",
            "description",
            "tags",
        )
        default_columns = (
            "pk",
            "circuit",
            "term_side",
            "location",
            "provider_network",
        )
