"""Tables for the vpn models."""

import django_tables2 as tables

from nautobot.apps.tables import (
    BaseTable,
    ButtonsColumn,
    LinkedCountColumn,
    RoleTableMixin,
    StatusTableMixin,
    TagColumn,
    ToggleColumn,
)
from nautobot.tenancy.tables import TenantColumn

from . import models


class VPNProfileTable(RoleTableMixin, BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNProfile list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    vpn_phase1_policy_count = LinkedCountColumn(
        viewname="vpn:vpnphase1policy_list",
        verbose_name="VPN Phase 1 Policy",
        # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
        url_params={"vpn_profiles": "pk"},
    )
    vpn_phase2_policy_count = LinkedCountColumn(
        viewname="vpn:vpnphase2policy_list",
        verbose_name="VPN Phase 2 Policy",
        # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
        url_params={"vpn_profiles": "pk"},
    )
    actions = ButtonsColumn(models.VPNProfile)
    tags = TagColumn(url_name="vpn:vpnprofile_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNProfile
        fields = (
            "pk",
            "name",
            "vpn_phase1_policy_count",
            "vpn_phase2_policy_count",
            "description",
            "keepalive_enabled",
            "keepalive_interval",
            "keepalive_retries",
            "nat_traversal",
            "secrets_group",
            "role",
        )
        # TODO INIT Add or Remove the columns below to change the list view default columns.
        default_columns = (
            "pk",
            "name",
            "vpn_phase1_policy_count",
            "vpn_phase2_policy_count",
            "description",
            "keepalive_enabled",
            "keepalive_interval",
            "keepalive_retries",
            "nat_traversal",
            "secrets_group",
            "role",
            "actions",
        )


class VPNPhase1PolicyTable(BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNPhase1Policy list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(models.VPNPhase1Policy)
    tags = TagColumn(url_name="vpn:vpnphase1policy_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNPhase1Policy
        fields = (
            "pk",
            "name",
            "description",
            "ike_version",
            "aggressive_mode",
            "encryption_algorithm",
            "integrity_algorithm",
            "dh_group",
            "lifetime_seconds",
            "lifetime_kb",
            "authentication_method",
        )
        # TODO INIT Add or Remove the columns below to change the list view default columns.
        default_columns = (
            "pk",
            "name",
            "description",
            "ike_version",
            "aggressive_mode",
            "encryption_algorithm",
            "integrity_algorithm",
            "dh_group",
            "lifetime_seconds",
            "lifetime_kb",
            "authentication_method",
            "actions",
        )


class VPNPhase2PolicyTable(BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNPhase2Policy list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(models.VPNPhase2Policy)
    tags = TagColumn(url_name="vpn:vpnphase2policy_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNPhase2Policy
        fields = (
            "pk",
            "name",
            "description",
            "encryption_algorithm",
            "integrity_algorithm",
            "pfs_group",
            "lifetime",
        )
        # TODO INIT Add or Remove the columns below to change the list view default columns.
        default_columns = (
            "pk",
            "name",
            "description",
            "encryption_algorithm",
            "integrity_algorithm",
            "pfs_group",
            "lifetime",
            "actions",
        )


class VPNProfilePhase1PolicyAssignmentTable(BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNProfile list view."""

    pk = ToggleColumn()
    vpn_phase1_policy = tables.Column(linkify=True)
    actions = ButtonsColumn(models.VPNProfilePhase1PolicyAssignment)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNProfilePhase1PolicyAssignment
        fields = (
            "pk",
            "vpn_phase1_policy",
            "weight",
        )
        default_columns = (
            "pk",
            "vpn_phase1_policy",
            "weight",
        )


class VPNProfilePhase2PolicyAssignmentTable(BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNProfile list view."""

    pk = ToggleColumn()
    vpn_phase2_policy = tables.Column(linkify=True)
    actions = ButtonsColumn(models.VPNProfilePhase2PolicyAssignment)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNProfilePhase2PolicyAssignment
        fields = (
            "pk",
            "vpn_phase2_policy",
            "weight",
        )
        default_columns = (
            "pk",
            "vpn_phase2_policy",
            "weight",
        )


class VPNTable(RoleTableMixin, BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPN list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    tunnel_count = LinkedCountColumn(
        viewname="vpn:vpntunnel_list",
        verbose_name="VPN Tunnels",
        url_params={"vpn": "pk"},
    )
    tenant = TenantColumn()
    # contact_associations_count = LinkedCountColumn(
    #     viewname="vpn:contactassociations_list",
    #     verbose_name="Contact Associations",
    #     # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
    #     url_params={},
    # )
    actions = ButtonsColumn(models.VPN)
    tags = TagColumn(url_name="vpn:vpn_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPN
        fields = (
            "pk",
            "name",
            "description",
            "tunnel_count",
            "vpn_profile",
            "vpn_id",
            "tenant",
            "role",
        )
        # TODO INIT Add or Remove the columns below to change the list view default columns.
        default_columns = (
            "pk",
            "vpn_profile",
            "name",
            "description",
            "tunnel_count",
            "vpn_id",
            "tenant",
            "role",
            "actions",
        )
        order_by = ["name"]


class VPNTunnelTable(StatusTableMixin, RoleTableMixin, BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNTunnel list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    endpoint_a = tables.Column(linkify=True)
    endpoint_z = tables.Column(linkify=True)
    tenant = TenantColumn()
    actions = ButtonsColumn(models.VPNTunnel)
    tags = TagColumn(url_name="vpn:vpntunnel_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNTunnel
        fields = (
            "pk",
            "name",
            "description",
            "vpn",
            "vpn_profile",
            "tunnel_id",
            "endpoint_a",
            "endpoint_z",
            "encapsulation",
            "tenant",
            "role",
            "status",
        )
        # TODO INIT Add or Remove the columns below to change the list view default columns.
        default_columns = (
            "pk",
            "name",
            "description",
            "vpn",
            "vpn_profile",
            "tunnel_id",
            "endpoint_a",
            "endpoint_z",
            "encapsulation",
            "tenant",
            "role",
            "status",
            "actions",
        )
        order_by = ["name"]


class VPNTunnelEndpointTable(RoleTableMixin, BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNTunnelEndpoint list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    device = tables.Column(linkify=True)
    source_interface = tables.Column(linkify=True)
    source_ipaddress = tables.Column(linkify=True)
    tunnel_interface = tables.Column(linkify=True)
    protected_prefixes_dg_count = LinkedCountColumn(
        viewname="extras:dynamicgroup_list",
        verbose_name="Dynamic Group",
        url_params={"dynamicgroups": "pk"},
        reverse_lookup="vpn_tunnel_endpoints",
    )
    protected_prefixes_count = LinkedCountColumn(
        viewname="ipam:prefix_list",
        verbose_name="Prefix",
        url_params={"prefixes": "pk"},
        reverse_lookup="vpn_tunnel_endpoints",
    )
    actions = ButtonsColumn(models.VPNTunnelEndpoint)
    tags = TagColumn(url_name="vpn:vpntunnelendpoint_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNTunnelEndpoint
        fields = (
            "pk",
            "name",
            "vpn_profile",
            "device",
            "source_interface",
            "source_ipaddress",
            "tunnel_interface",
            "source_fqdn",
            "protected_prefixes_dg_count",
            "protected_prefixes_count",
            "role",
            "status",
        )
        # TODO INIT Add or Remove the columns below to change the list view default columns.
        default_columns = (
            "pk",
            "name",
            "vpn_profile",
            "device",
            "source_interface",
            "source_ipaddress",
            "tunnel_interface",
            "source_fqdn",
            "protected_prefixes_dg_count",
            "protected_prefixes_count",
            "role",
            "actions",
        )
