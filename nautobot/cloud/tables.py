import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.extras.tables import RoleTableMixin, StatusTableMixin
from nautobot.tenancy.tables import TenantColumn

from .models import CloudAccount, CloudAccountGroup, CloudNetwork, CloudResourceGroup, CloudResourceType, CloudService

TREE_LINK = """
{% load helpers %}
{% if not table.hide_hierarchy_ui %}
{% tree_hierarchy_ui_representation record.tree_depth|as_range table.hide_hierarchy_ui %}
{% endif %}
<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
"""


class CloudAccountTable(StatusTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    provider = tables.Column(linkify=True)
    cloud_account_group = tables.Column(linkify=True)
    tenant = TenantColumn()
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
            "cloud_account_group",
            "status",
            "tenant",
            "secrets_group",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "account_number",
            "provider",
            "cloud_account_group",
            "status",
            "actions",
        )


class CloudAccountGroupTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=TREE_LINK, attrs={"td": {"class": "text-nowrap"}})
    cloud_resource_type = tables.Column(linkify=True)
    cloud_account_count = LinkedCountColumn(
        viewname="cloud:cloudaccount_list",
        url_params={"cloud_account_group": "pk"},
        verbose_name="Cloud Accounts",
    )
    tags = TagColumn(url_name="cloud:cloudaccountgroup_list")
    actions = ButtonsColumn(CloudAccountGroup)

    class Meta(BaseTable.Meta):
        model = CloudAccountGroup
        fields = (
            "pk",
            "name",
            "cloud_resource_type",
            "cloud_account_count",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "cloud_resource_type",
            "cloud_account_count",
            "description",
            "actions",
        )


class CloudResourceGroupTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    cloud_account = tables.Column(linkify=True)
    cloud_resource_type = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    cloud_network_count = LinkedCountColumn(
        viewname="cloud:cloudnetwork_list",
        url_params={"cloud_resource_group": "pk"},
        verbose_name="Cloud Networks",
    )
    cloud_service_count = LinkedCountColumn(
        viewname="cloud:cloudservice_list",
        url_params={"cloud_resource_group": "pk"},
        verbose_name="Cloud Services",
    )
    tags = TagColumn(url_name="cloud:cloudresourcegroup_list")
    actions = ButtonsColumn(CloudResourceGroup)

    class Meta(BaseTable.Meta):
        model = CloudResourceGroup
        fields = (
            "pk",
            "name",
            "provider_resource_id",
            "cloud_account",
            "cloud_resource_type",
            "location",
            "cloud_network_count",
            "cloud_service_count",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "cloud_account",
            "cloud_resource_type",
            "location",
            "cloud_network_count",
            "cloud_service_count",
            "actions",
        )


class CloudNetworkTable(StatusTableMixin, RoleTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    cloud_resource_type = tables.Column(linkify=True)
    cloud_account = tables.Column(linkify=True)
    cloud_resource_group = tables.Column(linkify=True)
    parent = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    tenant = TenantColumn()
    actions = ButtonsColumn(CloudNetwork)
    assigned_prefix_count = LinkedCountColumn(
        viewname="ipam:prefix_list",
        url_params={"cloud_networks": "pk"},
        verbose_name="Assigned Prefixes",
    )
    circuit_count = LinkedCountColumn(
        viewname="circuits:circuit_list",
        url_params={"cloud_network": "pk"},
        lookup="circuit_terminations__circuit",
        verbose_name="Circuits",
        reverse_lookup="circuit_terminations__cloud_network",
        distinct=True,
        display_field="cid",
    )
    cloud_service_count = LinkedCountColumn(
        viewname="cloud:cloudservice_list",
        url_params={"cloud_networks": "pk"},
        verbose_name="Cloud Services",
    )
    tags = TagColumn(url_name="cloud:cloudnetwork_list")

    class Meta(BaseTable.Meta):
        model = CloudNetwork
        fields = (
            "pk",
            "name",
            "description",
            "provider_resource_id",
            "cloud_resource_type",
            "cloud_account",
            "cloud_resource_group",
            "parent",
            "location",
            "status",
            "role",
            "tenant",
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
            "cloud_resource_group",
            "location",
            "status",
            "cloud_service_count",
            "assigned_prefix_count",
            "circuit_count",
            "parent",
            "actions",
        )


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


class CloudServiceTable(StatusTableMixin, RoleTableMixin, BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    cloud_account = tables.Column(linkify=True)
    cloud_resource_group = tables.Column(linkify=True)
    cloud_resource_type = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    tenant = TenantColumn()
    cloud_network_count = LinkedCountColumn(
        viewname="cloud:cloudnetwork_list",
        url_params={"cloud_services": "pk"},
        verbose_name="Cloud Networks",
    )
    tags = TagColumn(url_name="cloud:cloudservice_list")
    actions = ButtonsColumn(CloudService)

    class Meta(BaseTable.Meta):
        model = CloudService
        fields = (
            "pk",
            "name",
            "provider_resource_id",
            "cloud_resource_type",
            "cloud_account",
            "cloud_resource_group",
            "location",
            "status",
            "role",
            "tenant",
            "cloud_network_count",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "cloud_resource_type",
            "cloud_account",
            "cloud_resource_group",
            "location",
            "status",
            "cloud_network_count",
            "actions",
        )
