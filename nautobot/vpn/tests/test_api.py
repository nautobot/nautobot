"""Unit tests for nautobot_vpn_models."""

from nautobot.apps.testing import APIViewTestCases
from nautobot.vpn import models


class VPNProfileAPITest(APIViewTestCases.APIViewTestCase):
    """VPNProfile API tests."""

    model = models.VPNProfile
    choices_fields = ()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "vpn_phase1_policy": "replaceme",
                "vpn_phase2_policy": "replaceme",
                "name": "replaceme",
                "description": "replaceme",
                "keepalive_enabled": "replaceme",
                "keepalive_interval": "replaceme",
                "keepalive_retries": "replaceme",
                "nat_traversal": "replaceme",
                "extra_options": "replaceme",
                "secrets_group": "replaceme",
                "role": "replaceme",
            },
            {
                "vpn_phase1_policy": "replaceme",
                "vpn_phase2_policy": "replaceme",
                "name": "replaceme",
                "description": "replaceme",
                "keepalive_enabled": "replaceme",
                "keepalive_interval": "replaceme",
                "keepalive_retries": "replaceme",
                "nat_traversal": "replaceme",
                "extra_options": "replaceme",
                "secrets_group": "replaceme",
                "role": "replaceme",
            },
            {
                "vpn_phase1_policy": "replaceme",
                "vpn_phase2_policy": "replaceme",
                "name": "replaceme",
                "description": "replaceme",
                "keepalive_enabled": "replaceme",
                "keepalive_interval": "replaceme",
                "keepalive_retries": "replaceme",
                "nat_traversal": "replaceme",
                "extra_options": "replaceme",
                "secrets_group": "replaceme",
                "role": "replaceme",
            },
        ]

        cls.update_data = {
            "vpn_phase1_policy": "replaceme",
            "vpn_phase2_policy": "replaceme",
            "description": "replaceme",
            "keepalive_enabled": "replaceme",
            "keepalive_interval": "replaceme",
            "keepalive_retries": "replaceme",
            "nat_traversal": "replaceme",
            "extra_options": "replaceme",
            "secrets_group": "replaceme",
            "role": "replaceme",
        }


class VPNPhase1PolicyAPITest(APIViewTestCases.APIViewTestCase):
    """VPNPhase1Policy API tests."""

    model = models.VPNPhase1Policy
    choices_fields = (
        "ike_version",
        "encryption_algorithm",
        "integrity_algorithm",
        "dh_group",
        "authentication_method",
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "name": "replaceme",
                "description": "replaceme",
                "ike_version": "replaceme",
                "aggressive_mode": "replaceme",
                "encryption_algorithm": "replaceme",
                "integrity_algorithm": "replaceme",
                "dh_group": "replaceme",
                "lifetime_seconds": "replaceme",
                "lifetime_kb": "replaceme",
                "authentication_method": "replaceme",
            },
            {
                "name": "replaceme",
                "description": "replaceme",
                "ike_version": "replaceme",
                "aggressive_mode": "replaceme",
                "encryption_algorithm": "replaceme",
                "integrity_algorithm": "replaceme",
                "dh_group": "replaceme",
                "lifetime_seconds": "replaceme",
                "lifetime_kb": "replaceme",
                "authentication_method": "replaceme",
            },
            {
                "name": "replaceme",
                "description": "replaceme",
                "ike_version": "replaceme",
                "aggressive_mode": "replaceme",
                "encryption_algorithm": "replaceme",
                "integrity_algorithm": "replaceme",
                "dh_group": "replaceme",
                "lifetime_seconds": "replaceme",
                "lifetime_kb": "replaceme",
                "authentication_method": "replaceme",
            },
        ]

        cls.update_data = {
            "description": "replaceme",
            "ike_version": "replaceme",
            "aggressive_mode": "replaceme",
            "encryption_algorithm": "replaceme",
            "integrity_algorithm": "replaceme",
            "dh_group": "replaceme",
            "lifetime_seconds": "replaceme",
            "lifetime_kb": "replaceme",
            "authentication_method": "replaceme",
        }


class VPNPhase2PolicyAPITest(APIViewTestCases.APIViewTestCase):
    """VPNPhase2Policy API tests."""

    model = models.VPNPhase2Policy
    choices_fields = (
        "encryption_algorithm",
        "integrity_algorithm",
        "pfs_group",
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "name": "replaceme",
                "description": "replaceme",
                "encryption_algorithm": "replaceme",
                "integrity_algorithm": "replaceme",
                "pfs_group": "replaceme",
                "lifetime": "replaceme",
            },
            {
                "name": "replaceme",
                "description": "replaceme",
                "encryption_algorithm": "replaceme",
                "integrity_algorithm": "replaceme",
                "pfs_group": "replaceme",
                "lifetime": "replaceme",
            },
            {
                "name": "replaceme",
                "description": "replaceme",
                "encryption_algorithm": "replaceme",
                "integrity_algorithm": "replaceme",
                "pfs_group": "replaceme",
                "lifetime": "replaceme",
            },
        ]

        cls.update_data = {
            "description": "replaceme",
            "encryption_algorithm": "replaceme",
            "integrity_algorithm": "replaceme",
            "pfs_group": "replaceme",
            "lifetime": "replaceme",
        }


class VPNAPITest(APIViewTestCases.APIViewTestCase):
    """VPN API tests."""

    model = models.VPN
    choices_fields = ()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "vpn_profile": "replaceme",
                "name": "replaceme",
                "description": "replaceme",
                "vpn_id": "replaceme",
                "tenant": "replaceme",
                "role": "replaceme",
                "contact_associations": "replaceme",
            },
            {
                "vpn_profile": "replaceme",
                "name": "replaceme",
                "description": "replaceme",
                "vpn_id": "replaceme",
                "tenant": "replaceme",
                "role": "replaceme",
                "contact_associations": "replaceme",
            },
            {
                "vpn_profile": "replaceme",
                "name": "replaceme",
                "description": "replaceme",
                "vpn_id": "replaceme",
                "tenant": "replaceme",
                "role": "replaceme",
                "contact_associations": "replaceme",
            },
        ]

        cls.update_data = {
            "vpn_profile": "replaceme",
            "description": "replaceme",
            "vpn_id": "replaceme",
            "tenant": "replaceme",
            "role": "replaceme",
            "contact_associations": "replaceme",
        }


class VPNTunnelAPITest(APIViewTestCases.APIViewTestCase):
    """VPNTunnel API tests."""

    model = models.VPNTunnel
    choices_fields = ("encapsulation",)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "vpn_profile": "replaceme",
                "vpn": "replaceme",
                "name": "replaceme",
                "description": "replaceme",
                "tunnel_id": "replaceme",
                "encapsulation": "replaceme",
                "tenant": "replaceme",
                "role": "replaceme",
                "contact_associations": "replaceme",
            },
            {
                "vpn_profile": "replaceme",
                "vpn": "replaceme",
                "name": "replaceme",
                "description": "replaceme",
                "tunnel_id": "replaceme",
                "encapsulation": "replaceme",
                "tenant": "replaceme",
                "role": "replaceme",
                "contact_associations": "replaceme",
            },
            {
                "vpn_profile": "replaceme",
                "vpn": "replaceme",
                "name": "replaceme",
                "description": "replaceme",
                "tunnel_id": "replaceme",
                "encapsulation": "replaceme",
                "tenant": "replaceme",
                "role": "replaceme",
                "contact_associations": "replaceme",
            },
        ]

        cls.update_data = {
            "vpn_profile": "replaceme",
            "vpn": "replaceme",
            "description": "replaceme",
            "tunnel_id": "replaceme",
            "encapsulation": "replaceme",
            "tenant": "replaceme",
            "role": "replaceme",
            "contact_associations": "replaceme",
        }


class VPNTunnelEndpointAPITest(APIViewTestCases.APIViewTestCase):
    """VPNTunnelEndpoint API tests."""

    model = models.VPNTunnelEndpoint
    choices_fields = ()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "vpn_profile": "replaceme",
                "vpn_tunnel": "replaceme",
                "source_ipaddress": "replaceme",
                "source_interface": "replaceme",
                "destination_ipaddress": "replaceme",
                "destination_fqdn": "replaceme",
                "tunnel_interface": "replaceme",
                "protected_prefixes_dg": "replaceme",
                "protected_prefixes": "replaceme",
                "role": "replaceme",
                "contact_associations": "replaceme",
            },
            {
                "vpn_profile": "replaceme",
                "vpn_tunnel": "replaceme",
                "source_ipaddress": "replaceme",
                "source_interface": "replaceme",
                "destination_ipaddress": "replaceme",
                "destination_fqdn": "replaceme",
                "tunnel_interface": "replaceme",
                "protected_prefixes_dg": "replaceme",
                "protected_prefixes": "replaceme",
                "role": "replaceme",
                "contact_associations": "replaceme",
            },
            {
                "vpn_profile": "replaceme",
                "vpn_tunnel": "replaceme",
                "source_ipaddress": "replaceme",
                "source_interface": "replaceme",
                "destination_ipaddress": "replaceme",
                "destination_fqdn": "replaceme",
                "tunnel_interface": "replaceme",
                "protected_prefixes_dg": "replaceme",
                "protected_prefixes": "replaceme",
                "role": "replaceme",
                "contact_associations": "replaceme",
            },
        ]

        cls.update_data = {
            "vpn_profile": "replaceme",
            "vpn_tunnel": "replaceme",
            "source_ipaddress": "replaceme",
            "source_interface": "replaceme",
            "destination_ipaddress": "replaceme",
            "destination_fqdn": "replaceme",
            "tunnel_interface": "replaceme",
            "protected_prefixes_dg": "replaceme",
            "protected_prefixes": "replaceme",
            "role": "replaceme",
            "contact_associations": "replaceme",
        }


# TODO: Verify GQL !!!
