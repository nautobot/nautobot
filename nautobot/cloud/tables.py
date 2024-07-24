import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.tenancy.tables import TenantColumn

from .models import CloudAccount, CloudNetwork, CloudNetworkPrefixAssignment, CloudResourceType, CloudService


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
    cloud_resource_type = tables.Column(linkify=True)
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
    cloud_service_count = LinkedCountColumn(
        viewname="cloud:cloudservice_list",
        url_params={"cloud_networks": "name"},
        verbose_name="Cloud Services",
    )
    tags = TagColumn(url_name="cloud:cloudnetwork_list")

    class Meta(BaseTable.Meta):
        model = CloudNetwork
        fields = (
            "pk",
            "name",
            "description",
            "cloud_resource_type",
            "cloud_account",
            "parent",
            "cloud_service_count",
            "assigned_prefix_count",
            "circuit_count",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "cloud_resource_type",
            "cloud_account",
            "cloud_service_count",
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


class CloudResourceTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    provider = tables.Column(linkify=True)
    tags = TagColumn(url_name="cloud:cloudresourcetype_list")
    actions = ButtonsColumn(CloudResourceType)

    class Meta(BaseTable.Meta):
        model = CloudResourceType
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
    cloud_resource_type = tables.Column(linkify=True)
    cloud_network_count = LinkedCountColumn(
        viewname="cloud:cloudnetwork_list",
        url_params={"cloud_services": "name"},
        verbose_name="Cloud Networks",
    )
    tags = TagColumn(url_name="cloud:cloudservice_list")
    actions = ButtonsColumn(CloudService)

    class Meta(BaseTable.Meta):
        model = CloudService
        fields = (
            "pk",
            "name",
            "cloud_resource_type",
            "cloud_account",
            "cloud_network_count",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "cloud_resource_type",
            "cloud_account",
            "cloud_network_count",
            "actions",
        )
