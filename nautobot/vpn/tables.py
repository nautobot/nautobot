"""Tables for nautobot_vpn_models."""

import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ButtonsColumn, LinkedCountColumn, TagColumn, ToggleColumn
from nautobot.tenancy.tables import TenantColumn

from nautobot_vpn_models import models











class VPNProfileTable(RoleTableMixin, BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNProfile list view."""

    pk = ToggleColumn()
    vpn_phase1_policy_count = LinkedCountColumn(
        viewname="plugins:nautobot_vpn_models:vpnphase1policy_list",
        verbose_name="VPN Phase 1 Policy",
        # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
        url_params={},
    )
    vpn_phase2_policy_count = LinkedCountColumn(
        viewname="plugins:nautobot_vpn_models:vpnphase2policy_list",
        verbose_name="VPN Phase 2 Policy",
        # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
        url_params={},
    )
    actions = ButtonsColumn(models.VPNProfile)
    tags = TagColumn(url_name="plugins:nautobot_vpn_models:vpnprofile_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNProfile
        fields = (
            "pk",
            "vpn_phase1_policy_count",
            "vpn_phase2_policy_count",
            "name",
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
            "vpn_phase1_policy_count",
            "vpn_phase2_policy_count",
            "name",
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
    actions = ButtonsColumn(models.VPNPhase1Policy)
    tags = TagColumn(url_name="plugins:nautobot_vpn_models:vpnphase1policy_list")

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
    actions = ButtonsColumn(models.VPNPhase2Policy)
    tags = TagColumn(url_name="plugins:nautobot_vpn_models:vpnphase2policy_list")

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


class VPNTable(RoleTableMixin, BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPN list view."""

    pk = ToggleColumn()
    tenant = TenantColumn()
    contact_associations_count = LinkedCountColumn(
        viewname="plugins:nautobot_vpn_models:contactassociations_list",
        verbose_name="Contact Associations",
        # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
        url_params={},
    )
    actions = ButtonsColumn(models.VPN)
    tags = TagColumn(url_name="plugins:nautobot_vpn_models:vpn_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPN
        fields = (
            "pk",
            "vpn_profile",
            "name",
            "description",
            "vpn_id",
            "tenant",
            "role",
            "contact_associations_count",
        )
        # TODO INIT Add or Remove the columns below to change the list view default columns.
        default_columns = (
            "pk",
            "vpn_profile",
            "name",
            "description",
            "vpn_id",
            "tenant",
            "role",
            "contact_associations_count",
            "actions",
        )


class VPNTunnelTable(StatusTableMixin, RoleTableMixin, BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNTunnel list view."""

    pk = ToggleColumn()
    tenant = TenantColumn()
    contact_associations_count = LinkedCountColumn(
        viewname="plugins:nautobot_vpn_models:contactassociations_list",
        verbose_name="Contact Associations",
        # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
        url_params={},
    )
    actions = ButtonsColumn(models.VPNTunnel)
    tags = TagColumn(url_name="plugins:nautobot_vpn_models:vpntunnel_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNTunnel
        fields = (
            "pk",
            "vpn_profile",
            "vpn",
            "name",
            "description",
            "tunnel_id",
            "encapsulation",
            "tenant",
            "role",
            "contact_associations_count",
        )
        # TODO INIT Add or Remove the columns below to change the list view default columns.
        default_columns = (
            "pk",
            "vpn_profile",
            "vpn",
            "name",
            "description",
            "tunnel_id",
            "encapsulation",
            "tenant",
            "role",
            "contact_associations_count",
            "actions",
        )


class VPNTunnelEndpointTable(RoleTableMixin, BaseTable):
    # pylint: disable=too-few-public-methods
    """Table for VPNTunnelEndpoint list view."""

    pk = ToggleColumn()
    source_interface = tables.Column(linkify=True)
    tunnel_interface = tables.Column(linkify=True)
    protected_prefixes_dg_count = LinkedCountColumn(
        viewname="plugins:nautobot_vpn_models:dynamicgroup_list",
        verbose_name="Dynamic Group",
        # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
        url_params={},
    )
    protected_prefixes_count = LinkedCountColumn(
        viewname="plugins:nautobot_vpn_models:prefix_list",
        verbose_name="Prefix",
        # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
        url_params={},
    )
    contact_associations_count = LinkedCountColumn(
        viewname="plugins:nautobot_vpn_models:contactassociations_list",
        verbose_name="Contact Associations",
        # TODO INIT Add the URL Params below, and optionally the reverse_lookup.
        url_params={},
    )
    actions = ButtonsColumn(models.VPNTunnelEndpoint)
    tags = TagColumn(url_name="plugins:nautobot_vpn_models:vpntunnelendpoint_list")

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.VPNTunnelEndpoint
        fields = (
            "pk",
            "vpn_profile",
            "vpn_tunnel",
            "source_ipaddress",
            "source_interface",
            "destination_ipaddress",
            "destination_fqdn",
            "tunnel_interface",
            "protected_prefixes_dg_count",
            "protected_prefixes_count",
            "role",
            "contact_associations_count",
        )
        # TODO INIT Add or Remove the columns below to change the list view default columns.
        default_columns = (
            "pk",
            "vpn_profile",
            "vpn_tunnel",
            "source_ipaddress",
            "source_interface",
            "destination_ipaddress",
            "destination_fqdn",
            "tunnel_interface",
            "protected_prefixes_dg_count",
            "protected_prefixes_count",
            "role",
            "contact_associations_count",
            "actions",
        )

