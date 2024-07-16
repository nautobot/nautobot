import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.tenancy.tables import TenantColumn

from .models import CloudAccount, CloudNetwork, CloudNetworkPrefixAssignment, CloudService, CloudType


class CloudAccountTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    provider = tables.Column(linkify=True)
    secrets_group = tables.Column(linkify=True)
    tags = TagColumn(url_name="cloud:cloudaccount_list")
    actions = ButtonsColumn(CloudAccount)

    class Meta(BaseTable.Meta):
        model = CloudAccount
        fields = (
            "pk",
            "name",
            "account_number",
            "description",
            "provider",
            "secrets_group",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "account_number",
            "provider",
            "actions",
        )


class CloudNetworkTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    cloud_type = tables.Column(linkify=True)
    cloud_account = tables.Column(linkify=True)
    parent = tables.Column(linkify=True)
    actions = ButtonsColumn(CloudNetwork)
    assigned_prefix_count = LinkedCountColumn(
        viewname="ipam:prefix_list",
        url_params={"cloud_networks": "name"},
        verbose_name="Assigned Prefixes",
    )
    circuit_count = LinkedCountColumn(
        viewname="circuits:circuit_list",
        url_params={"cloud_network": "name"},
        verbose_name="Circuits",
        reverse_lookup="circuit_terminations__cloud_network",
    )

    class Meta(BaseTable.Meta):
        model = CloudNetwork
        fields = (
            "pk",
            "name",
            "description",
            "cloud_type",
            "cloud_account",
            "parent",
            "assigned_prefix_count",
            "circuit_count",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "cloud_type",
            "cloud_account",
            "assigned_prefix_count",
            "circuit_count",
            "parent",
            "actions",
        )


class CloudNetworkPrefixAssignmentTable(BaseTable):
    cloud_network = tables.Column(
        verbose_name="Cloud Network",
        linkify=lambda record: record.cloud_network.get_absolute_url(),
        accessor="cloud_network.name",
    )
    prefix = tables.Column(linkify=True)
    rd = tables.Column(accessor="vrf.rd", verbose_name="RD")
    tenant = TenantColumn(accessor="vrf.tenant")

    class Meta(BaseTable.Meta):
        model = CloudNetworkPrefixAssignment
        fields = ("cloud_network", "prefix", "rd", "tenant")


class CloudTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    provider = tables.Column(linkify=True)
    actions = ButtonsColumn(CloudType)

    class Meta(BaseTable.Meta):
        model = CloudType
        fields = (
            "pk",
            "name",
            "description",
            "provider",
            "config_schema",
            "content_types",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "provider",
            "config_schema",
            "content_types",
            "actions",
        )


class CloudServiceTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    cloud_account = tables.Column(linkify=True)
    cloud_network = tables.Column(linkify=True)
    cloud_type = tables.Column(linkify=True)
    actions = ButtonsColumn(CloudService)

    class Meta(BaseTable.Meta):
        model = CloudService
        fields = (
            "pk",
            "name",
            "cloud_account",
            "cloud_network",
            "cloud_type",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "cloud_account",
            "cloud_network",
            "cloud_type",
            "actions",
        )
