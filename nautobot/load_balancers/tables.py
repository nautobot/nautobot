"""Tables for nautobot_load_balancer_models."""

import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.extras.tables import StatusTableMixin
from nautobot.load_balancers import models
from nautobot.tenancy.tables import TenantColumn


class VirtualServerTable(BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VirtualServer list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    vip = tables.Column(linkify=True)
    source_nat_pool = tables.Column(linkify=True)
    load_balancer_pool = tables.Column(linkify=True)
    enabled = BooleanColumn()
    ssl_offload = BooleanColumn()
    device = tables.Column(linkify=True)
    device_redundancy_group = tables.Column(linkify=True)
    cloud_service = tables.Column(linkify=True)
    virtual_chassis = tables.Column(linkify=True)
    tenant = TenantColumn()
    health_check_monitor = tables.Column(linkify=True)
    certificate_profiles_count = LinkedCountColumn(
        viewname="load_balancers:certificateprofile_list",
        verbose_name="Certificate Profiles",
        url_params={"certificate_profiles": "name"},
    )
    actions = ButtonsColumn(models.VirtualServer)
    tags = TagColumn(url_name="load_balancers:virtualserver_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VirtualServer
        fields = (
            "pk",
            "name",
            "vip",
            "enabled",
            "load_balancer_type",
            "port",
            "protocol",
            "load_balancer_pool",
            "tenant",
            "source_nat_pool",
            "source_nat_type",
            "device",
            "device_redundancy_group",
            "cloud_service",
            "virtual_chassis",
            "health_check_monitor",
            "ssl_offload",
            "certificate_profiles_count",
            "tags",
            "actions",
        )

        default_columns = (
            "pk",
            "name",
            "vip",
            "enabled",
            "load_balancer_type",
            "load_balancer_pool",
            "port",
            "protocol",
            "actions",
        )


class LoadBalancerPoolTable(BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for LoadBalancerPool list view."""

    pk = ToggleColumn()
    health_check_monitor = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
    virtual_server = tables.Column(linkify=True)
    load_balancer_pool_member_count = LinkedCountColumn(
        viewname="load_balancers:loadbalancerpoolmember_list",
        url_params={"load_balancer_pool": "name"},
        verbose_name="Load Balancer Pool Members",
    )
    tenant = TenantColumn()
    actions = ButtonsColumn(models.LoadBalancerPool)
    tags = TagColumn(url_name="load_balancers:loadbalancerpool_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.LoadBalancerPool
        fields = (
            "pk",
            "name",
            "virtual_server",
            "load_balancing_algorithm",
            "load_balancer_pool_member_count",
            "health_check_monitor",
            "tenant",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "virtual_server",
            "load_balancing_algorithm",
            "load_balancer_pool_member_count",
            "actions",
        )


class LoadBalancerPoolMemberTable(StatusTableMixin, BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for LoadBalancerPoolMember list view."""

    pk = ToggleColumn()
    display = tables.Column(linkify=True, verbose_name="Load Balancer Pool Member")
    ip_address = tables.Column(linkify=True, verbose_name="IP Address")
    load_balancer_pool = tables.Column(linkify=True, verbose_name="Load Balancer Pool")
    health_check_monitor = tables.Column(linkify=True)
    ssl_offload = BooleanColumn()
    certificate_profiles_count = LinkedCountColumn(
        viewname="load_balancers:certificateprofile_list",
        verbose_name="Certificate Profiles",
        url_params={"certificate_profiles": "name"},
    )
    tenant = TenantColumn()
    actions = ButtonsColumn(models.LoadBalancerPoolMember)
    tags = TagColumn(url_name="load_balancers:loadbalancerpoolmember_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.LoadBalancerPoolMember
        fields = (
            "pk",
            "display",
            "status",
            "ip_address",
            "load_balancer_pool",
            "port",
            "ssl_offload",
            "health_check_monitor",
            "certificate_profiles_count",
            "tenant",
            "actions",
        )
        default_columns = (
            "pk",
            "display",
            "status",
            "port",
            "load_balancer_pool",
            "ssl_offload",
            "actions",
        )


class HealthCheckMonitorTable(BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for HealthCheckMonitor list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    tenant = TenantColumn()
    virtual_server_count = LinkedCountColumn(
        viewname="load_balancers:virtualserver_list",
        url_params={"health_check_monitor": "name"},
        verbose_name="Virtual Servers",
    )
    load_balancer_pool_count = LinkedCountColumn(
        viewname="load_balancers:loadbalancerpool_list",
        url_params={"health_check_monitor": "name"},
        verbose_name="Pools",
    )
    load_balancer_pool_member_count = LinkedCountColumn(
        viewname="load_balancers:loadbalancerpoolmember_list",
        url_params={"health_check_monitor": "name"},
        verbose_name="Load Balancer Pool Members",
    )
    actions = ButtonsColumn(models.HealthCheckMonitor)
    tags = TagColumn(url_name="load_balancers:healthcheckmonitor_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.HealthCheckMonitor
        fields = (
            "pk",
            "name",
            "health_check_type",
            "port",
            "interval",
            "retry",
            "timeout",
            "virtual_server_count",
            "load_balancer_pool_count",
            "load_balancer_pool_member_count",
            "tenant",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "health_check_type",
            "port",
            "interval",
            "retry",
            "timeout",
            "actions",
        )


class CertificateProfileTable(BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for CertificateProfile list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    tenant = TenantColumn()
    actions = ButtonsColumn(models.CertificateProfile)
    tags = TagColumn(url_name="load_balancers:certificateprofile_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.CertificateProfile
        fields = (
            "pk",
            "name",
            "certificate_type",
            "certificate_file_path",
            "chain_file_path",
            "key_file_path",
            "expiration_date",
            "cipher",
            "tenant",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "certificate_type",
            "expiration_date",
            "cipher",
            "tenant",
            "actions",
        )
