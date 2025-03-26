"""Unit tests for views."""

from nautobot.apps.testing import ViewTestCases
from nautobot.vpn import models


class VPNProfileViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the VPNProfile views."""

    model = models.VPNProfile

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "vpn_phase1_policy": "test value",
            "vpn_phase2_policy": "test value",
            "name": "test value",
            "description": "test value",
            "keepalive_enabled": "test value",
            "keepalive_interval": "test value",
            "keepalive_retries": "test value",
            "nat_traversal": "test value",
            "extra_options": "test value",
            "secrets_group": "test value",
            "role": "test value",
        }

        cls.update_data = {
            "vpn_phase1_policy": "updated value",
            "vpn_phase2_policy": "updated value",
            "description": "updated value",
            "keepalive_enabled": "updated value",
            "keepalive_interval": "updated value",
            "keepalive_retries": "updated value",
            "nat_traversal": "updated value",
            "extra_options": "updated value",
            "secrets_group": "updated value",
            "role": "updated value",
        }

        cls.bulk_edit_data = {
            "vpn_phase1_policy": "updated value",
            "vpn_phase2_policy": "updated value",
            "description": "updated value",
            "keepalive_enabled": "updated value",
            "keepalive_interval": "updated value",
            "keepalive_retries": "updated value",
            "nat_traversal": "updated value",
            "extra_options": "updated value",
            "secrets_group": "updated value",
            "role": "updated value",
        }


class VPNPhase1PolicyViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the VPNPhase1Policy views."""

    model = models.VPNPhase1Policy

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "name": "test value",
            "description": "test value",
            "ike_version": "test value",
            "aggressive_mode": "test value",
            "encryption_algorithm": "test value",
            "integrity_algorithm": "test value",
            "dh_group": "test value",
            "lifetime_seconds": "test value",
            "lifetime_kb": "test value",
            "authentication_method": "test value",
        }

        cls.update_data = {
            "description": "updated value",
            "ike_version": "updated value",
            "aggressive_mode": "updated value",
            "encryption_algorithm": "updated value",
            "integrity_algorithm": "updated value",
            "dh_group": "updated value",
            "lifetime_seconds": "updated value",
            "lifetime_kb": "updated value",
            "authentication_method": "updated value",
        }

        cls.bulk_edit_data = {
            "description": "updated value",
            "ike_version": "updated value",
            "aggressive_mode": "updated value",
            "encryption_algorithm": "updated value",
            "integrity_algorithm": "updated value",
            "dh_group": "updated value",
            "lifetime_seconds": "updated value",
            "lifetime_kb": "updated value",
            "authentication_method": "updated value",
        }


class VPNPhase2PolicyViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the VPNPhase2Policy views."""

    model = models.VPNPhase2Policy

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "name": "test value",
            "description": "test value",
            "encryption_algorithm": "test value",
            "integrity_algorithm": "test value",
            "pfs_group": "test value",
            "lifetime": "test value",
        }

        cls.update_data = {
            "description": "updated value",
            "encryption_algorithm": "updated value",
            "integrity_algorithm": "updated value",
            "pfs_group": "updated value",
            "lifetime": "updated value",
        }

        cls.bulk_edit_data = {
            "description": "updated value",
            "encryption_algorithm": "updated value",
            "integrity_algorithm": "updated value",
            "pfs_group": "updated value",
            "lifetime": "updated value",
        }


class VPNViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the VPN views."""

    model = models.VPN

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "vpn_profile": "test value",
            "name": "test value",
            "description": "test value",
            "vpn_id": "test value",
            "tenant": "test value",
            "role": "test value",
            "contact_associations": "test value",
        }

        cls.update_data = {
            "vpn_profile": "updated value",
            "description": "updated value",
            "vpn_id": "updated value",
            "tenant": "updated value",
            "role": "updated value",
            "contact_associations": "updated value",
        }

        cls.bulk_edit_data = {
            "vpn_profile": "updated value",
            "description": "updated value",
            "vpn_id": "updated value",
            "tenant": "updated value",
            "role": "updated value",
            "contact_associations": "updated value",
        }


class VPNTunnelViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the VPNTunnel views."""

    model = models.VPNTunnel

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "vpn_profile": "test value",
            "vpn": "test value",
            "name": "test value",
            "description": "test value",
            "tunnel_id": "test value",
            "encapsulation": "test value",
            "tenant": "test value",
            "role": "test value",
            "contact_associations": "test value",
        }

        cls.update_data = {
            "vpn_profile": "updated value",
            "vpn": "updated value",
            "description": "updated value",
            "tunnel_id": "updated value",
            "encapsulation": "updated value",
            "tenant": "updated value",
            "role": "updated value",
            "contact_associations": "updated value",
        }

        cls.bulk_edit_data = {
            "vpn_profile": "updated value",
            "vpn": "updated value",
            "description": "updated value",
            "tunnel_id": "updated value",
            "encapsulation": "updated value",
            "tenant": "updated value",
            "role": "updated value",
            "contact_associations": "updated value",
        }


class VPNTunnelEndpointViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the VPNTunnelEndpoint views."""

    model = models.VPNTunnelEndpoint

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "vpn_profile": "test value",
            "vpn_tunnel": "test value",
            "source_ipaddress": "test value",
            "source_interface": "test value",
            "destination_ipaddress": "test value",
            "destination_fqdn": "test value",
            "tunnel_interface": "test value",
            "protected_prefixes_dg": "test value",
            "protected_prefixes": "test value",
            "role": "test value",
            "contact_associations": "test value",
        }

        cls.update_data = {
            "vpn_profile": "updated value",
            "vpn_tunnel": "updated value",
            "source_ipaddress": "updated value",
            "source_interface": "updated value",
            "destination_ipaddress": "updated value",
            "destination_fqdn": "updated value",
            "tunnel_interface": "updated value",
            "protected_prefixes_dg": "updated value",
            "protected_prefixes": "updated value",
            "role": "updated value",
            "contact_associations": "updated value",
        }

        cls.bulk_edit_data = {
            "vpn_profile": "updated value",
            "vpn_tunnel": "updated value",
            "source_ipaddress": "updated value",
            "source_interface": "updated value",
            "destination_ipaddress": "updated value",
            "destination_fqdn": "updated value",
            "tunnel_interface": "updated value",
            "protected_prefixes_dg": "updated value",
            "protected_prefixes": "updated value",
            "role": "updated value",
            "contact_associations": "updated value",
        }
