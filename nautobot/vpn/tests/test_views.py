"""Unit tests for vpn views."""

from nautobot.apps.testing import ViewTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import Status
from nautobot.ipam.models import Prefix
from nautobot.vpn import choices, models


class VPNProfileViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the VPNProfile views."""

    model = models.VPNProfile

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "name": "test value",
            "description": "test value",
            "keepalive_enabled": True,
            "keepalive_interval": 10,
            "keepalive_retries": 3,
            "nat_traversal": False,
            "extra_options": None,
            # Management form fields required for the dynamic formset
            "vpn_profile_phase1_policy_assignments-TOTAL_FORMS": "0",
            "vpn_profile_phase1_policy_assignments-INITIAL_FORMS": "1",
            "vpn_profile_phase1_policy_assignments-MIN_NUM_FORMS": "0",
            "vpn_profile_phase1_policy_assignments-MAX_NUM_FORMS": "1000",
            "vpn_profile_phase2_policy_assignments-TOTAL_FORMS": "0",
            "vpn_profile_phase2_policy_assignments-INITIAL_FORMS": "1",
            "vpn_profile_phase2_policy_assignments-MIN_NUM_FORMS": "0",
            "vpn_profile_phase2_policy_assignments-MAX_NUM_FORMS": "1000",
        }

        cls.update_data = {
            "name": "updated value",
            "description": "updated value",
            "keepalive_enabled": True,
            "keepalive_interval": 15,
            "keepalive_retries": 5,
            "nat_traversal": False,
            # Management form fields required for the dynamic formset
            "vpn_profile_phase1_policy_assignments-TOTAL_FORMS": "0",
            "vpn_profile_phase1_policy_assignments-INITIAL_FORMS": "1",
            "vpn_profile_phase1_policy_assignments-MIN_NUM_FORMS": "0",
            "vpn_profile_phase1_policy_assignments-MAX_NUM_FORMS": "1000",
            "vpn_profile_phase2_policy_assignments-TOTAL_FORMS": "0",
            "vpn_profile_phase2_policy_assignments-INITIAL_FORMS": "1",
            "vpn_profile_phase2_policy_assignments-MIN_NUM_FORMS": "0",
            "vpn_profile_phase2_policy_assignments-MAX_NUM_FORMS": "1000",
        }

        cls.bulk_edit_data = {
            "name": "bulk updated value",
            "description": "bulk updated value",
            "keepalive_enabled": True,
            "keepalive_interval": 30,
            "keepalive_retries": 10,
            "nat_traversal": True,
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
            "ike_version": choices.IkeVersionChoices.ike_v2,
            "aggressive_mode": False,
            "encryption_algorithm": choices.EncryptionAlgorithmChoices.aes_128_cbc,
            "integrity_algorithm": choices.IntegrityAlgorithmChoices.sha256,
            "dh_group": choices.DhGroupChoices.group14,
            "lifetime_seconds": 10,
            "lifetime_kb": None,
            "authentication_method": choices.AuthenticationMethodChoices.rsa,
        }

        cls.update_data = {
            "name": "updated value",
            "description": "updated value",
            "ike_version": choices.IkeVersionChoices.ike_v2,
            "aggressive_mode": False,
            "encryption_algorithm": choices.EncryptionAlgorithmChoices.aes_192_cbc,
            "integrity_algorithm": choices.IntegrityAlgorithmChoices.sha512,
            "dh_group": choices.DhGroupChoices.group21,
            "lifetime_seconds": 5,
            "lifetime_kb": None,
            "authentication_method": choices.AuthenticationMethodChoices.certificate,
        }

        cls.bulk_edit_data = {
            "name": "bulk updated value",
            "description": "bulk updated value",
            "ike_version": choices.IkeVersionChoices.ike_v2,
            "aggressive_mode": False,
            "encryption_algorithm": choices.EncryptionAlgorithmChoices.aes_256_gcm,
            "integrity_algorithm": choices.IntegrityAlgorithmChoices.sha1,
            "dh_group": choices.DhGroupChoices.group5,
            "lifetime_seconds": 15,
            "lifetime_kb": None,
            "authentication_method": choices.AuthenticationMethodChoices.ecdsa,
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
            "encryption_algorithm": choices.EncryptionAlgorithmChoices.aes_128_cbc,
            "integrity_algorithm": choices.IntegrityAlgorithmChoices.sha256,
            "pfs_group": choices.DhGroupChoices.group14,
            "lifetime": 10,
        }

        cls.update_data = {
            "name": "updated value",
            "description": "updated value",
            "encryption_algorithm": choices.EncryptionAlgorithmChoices.aes_192_cbc,
            "integrity_algorithm": choices.IntegrityAlgorithmChoices.sha512,
            "pfs_group": choices.DhGroupChoices.group21,
            "lifetime": 5,
        }

        cls.bulk_edit_data = {
            "name": "bulk updated value",
            "description": "bulk updated value",
            "encryption_algorithm": choices.EncryptionAlgorithmChoices.aes_256_gcm,
            "integrity_algorithm": choices.IntegrityAlgorithmChoices.sha1,
            "pfs_group": choices.DhGroupChoices.group5,
            "lifetime": 15,
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
            "name": "test value",
            "description": "test value",
            "vpn_id": "test value",
            "vpn_profile": models.VPNProfile.objects.first().pk,
        }

        cls.update_data = {
            "name": "updated value",
            "description": "updated value",
            "vpn_id": "updated value",
            "vpn_profile": models.VPNProfile.objects.last().pk,
        }

        cls.bulk_edit_data = {
            "description": "bulk updated value",
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
            "name": "test value",
            "description": "test value",
            "vpn_profile": models.VPNProfile.objects.first().pk,
            "vpn": models.VPN.objects.first().pk,
            "tunnel_id": "test value",
            "status": Status.objects.get(name="Active").pk,
            "encapsulation": choices.EncapsulationChoices.ipsec_tunnel,
            "endpoint_a": models.VPNTunnelEndpoint.objects.first().pk,
            "endpoint_z": models.VPNTunnelEndpoint.objects.last().pk,
        }

        cls.update_data = {
            "name": "test value",
            "description": "updated value",
            "vpn_profile": models.VPNProfile.objects.last().pk,
            "vpn": models.VPN.objects.last().pk,
            "tunnel_id": "updated value",
            "status": Status.objects.get(name="Active").pk,
            "encapsulation": choices.EncapsulationChoices.l2tp,
            "endpoint_a": models.VPNTunnelEndpoint.objects.last().pk,
            "endpoint_z": models.VPNTunnelEndpoint.objects.first().pk,
        }

        cls.bulk_edit_data = {
            "description": "bulk updated value",
        }


class VPNTunnelEndpointViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the VPNTunnelEndpoint views."""

    model = models.VPNTunnelEndpoint

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        interfaces = Interface.objects.filter(device__isnull=False, vpn_tunnel_endpoints_src_int__isnull=True)

        cls.form_data = {
            "device": interfaces.first().device.pk,
            "source_interface": interfaces.first().pk,
            "vpn_profile": models.VPNProfile.objects.first().pk,
            "protected_prefixes": [Prefix.objects.first().pk],
        }

        cls.update_data = {
            "device": interfaces.last().device.pk,
            "source_interface": interfaces.last().pk,
            "protected_prefixes": [Prefix.objects.last().pk],
        }

        cls.bulk_edit_data = {"vpn_profile": models.VPNProfile.objects.last().pk}
