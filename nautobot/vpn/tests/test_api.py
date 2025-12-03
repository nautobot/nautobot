"""Unit tests for vpn."""

from nautobot.apps.testing import APIViewTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import Status
from nautobot.vpn import choices, models


class VPNProfileAPITest(APIViewTestCases.APIViewTestCase):
    """VPNProfile API tests."""

    # Removes 'crypt' because of encryption_algorithm field.
    VERBOTEN_STRINGS = (
        "password",
        "argon2",
        "bcrypt",
        "md5",
        "pbkdf2",
        "scrypt",
        "sha1",
        "sha256",
        "sha512",
    )
    model = models.VPNProfile
    choices_fields = ()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "name": "test 1",
                "description": "test value",
                "keepalive_enabled": True,
                "keepalive_interval": 3,
                "keepalive_retries": 5,
                "nat_traversal": False,
                "extra_options": None,
            },
            {
                "name": "test 2",
                "description": "test value",
                "keepalive_enabled": True,
                "keepalive_interval": 15,
                "keepalive_retries": 3,
                "nat_traversal": False,
                "extra_options": None,
            },
            {
                "name": "test 3",
                "description": "test value",
                "keepalive_enabled": True,
                "keepalive_interval": 30,
                "keepalive_retries": 3,
                "nat_traversal": True,
                "extra_options": None,
            },
        ]

        cls.update_data = {
            "name": "test 1",
            "description": "updated value",
            "keepalive_enabled": True,
            "keepalive_interval": 60,
            "keepalive_retries": 3,
            "nat_traversal": False,
            "extra_options": None,
        }


class VPNPhase1PolicyAPITest(APIViewTestCases.APIViewTestCase):
    """VPNPhase1Policy API tests."""

    # Removes 'crypt' because of encryption_algorithm field.
    VERBOTEN_STRINGS = (
        "password",
        "argon2",
        "bcrypt",
        "md5",
        "pbkdf2",
        "scrypt",
        "sha1",
        "sha256",
        "sha512",
    )
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
                "name": "test 1",
                "description": "test value",
                "ike_version": choices.IkeVersionChoices.ike_v2,
                "aggressive_mode": False,
                "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_128_cbc],
                "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha1],
                "dh_group": [choices.DhGroupChoices.group5],
                "lifetime_seconds": 10,
                "lifetime_kb": None,
                "authentication_method": choices.AuthenticationMethodChoices.rsa,
            },
            {
                "name": "test 2",
                "description": "test value",
                "ike_version": choices.IkeVersionChoices.ike_v2,
                "aggressive_mode": False,
                "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_256_gcm],
                "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha256],
                "dh_group": [choices.DhGroupChoices.group14],
                "lifetime_seconds": 10,
                "lifetime_kb": None,
                "authentication_method": choices.AuthenticationMethodChoices.ecdsa,
            },
            {
                "name": "test 3",
                "description": "test value",
                "ike_version": choices.IkeVersionChoices.ike_v2,
                "aggressive_mode": False,
                "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_192_cbc],
                "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha512],
                "dh_group": [choices.DhGroupChoices.group21],
                "lifetime_seconds": 10,
                "lifetime_kb": None,
                "authentication_method": choices.AuthenticationMethodChoices.certificate,
            },
        ]

        cls.update_data = {
            "name": "test 1",
            "description": "updated value",
            "ike_version": choices.IkeVersionChoices.ike_v1,
            "lifetime_seconds": 5,
            "authentication_method": choices.AuthenticationMethodChoices.ecdsa,
        }


class VPNPhase2PolicyAPITest(APIViewTestCases.APIViewTestCase):
    """VPNPhase2Policy API tests."""

    # Removes 'crypt' because of encryption_algorithm field.
    VERBOTEN_STRINGS = (
        "password",
        "argon2",
        "bcrypt",
        "md5",
        "pbkdf2",
        "scrypt",
        "sha1",
        "sha256",
        "sha512",
    )
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
                "name": "test 1",
                "description": "test value",
                "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_128_cbc],
                "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha1],
                "pfs_group": [choices.DhGroupChoices.group5],
                "lifetime": 10,
            },
            {
                "name": "test 2",
                "description": "test value",
                "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_256_gcm],
                "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha256],
                "pfs_group": [choices.DhGroupChoices.group14],
                "lifetime": 10,
            },
            {
                "name": "test 3",
                "description": "test value",
                "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_192_cbc],
                "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha512],
                "pfs_group": [choices.DhGroupChoices.group21],
                "lifetime": 10,
            },
        ]

        cls.update_data = {
            "name": "test 1",
            "description": "updated value",
            "lifetime_seconds": 5,
        }


class VPNAPITest(APIViewTestCases.APIViewTestCase):
    """VPN API tests."""

    model = models.VPN
    choices_fields = ()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        profiles = models.VPNProfile.objects.all()

        cls.create_data = [
            {
                "name": "test 1",
                "description": "test value",
                "vpn_id": "test value",
                "vpn_profile": profiles[1].pk,
            },
            {
                "name": "test 2",
                "description": "test value",
                "vpn_id": "test value",
                "vpn_profile": profiles[2].pk,
            },
            {
                "name": "test 3",
                "description": "test value",
                "vpn_id": "test value",
                "vpn_profile": profiles[3].pk,
            },
        ]

        cls.update_data = {
            "name": "test 3",
            "vpn_profile": profiles[4].pk,
        }


class VPNTunnelAPITest(APIViewTestCases.APIViewTestCase):
    """VPNTunnel API tests."""

    model = models.VPNTunnel
    choices_fields = ("encapsulation",)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        endpoints = models.VPNTunnelEndpoint.objects.all()

        cls.create_data = [
            {
                "name": "test 1",
                "description": "test value",
                "vpn_profile": models.VPNProfile.objects.first().pk,
                "vpn": models.VPN.objects.first().pk,
                "tunnel_id": "test value",
                "status": Status.objects.get(name="Active").pk,
                "encapsulation": choices.EncapsulationChoices.ipsec_tunnel,
                "endpoint_a": endpoints[1].pk,
                "endpoint_z": endpoints[2].pk,
            },
            {
                "name": "test 2",
                "description": "test value",
                "vpn_profile": models.VPNProfile.objects.first().pk,
                "vpn": models.VPN.objects.first().pk,
                "tunnel_id": "test value",
                "status": Status.objects.get(name="Active").pk,
                "encapsulation": choices.EncapsulationChoices.l2tp,
                "endpoint_a": endpoints[3].pk,
                "endpoint_z": endpoints[4].pk,
            },
            {
                "name": "test 3",
                "description": "test value",
                "vpn_profile": models.VPNProfile.objects.first().pk,
                "vpn": models.VPN.objects.first().pk,
                "tunnel_id": "test value",
                "status": Status.objects.get(name="Active").pk,
                "encapsulation": choices.EncapsulationChoices.ipsec_transport,
                "endpoint_a": endpoints[5].pk,
                "endpoint_z": endpoints[6].pk,
            },
        ]

        cls.update_data = {
            "name": "test 4",
            "encapsulation": choices.EncapsulationChoices.ipsec_transport,
            "endpoint_a": endpoints[7].pk,
            "endpoint_z": endpoints[8].pk,
        }

    def get_deletable_object(self):
        """Return VPNTunnel where both endpoints are attached to a device."""
        return models.VPNTunnel.objects.create(name="Deletable VPN Tunnel", status=Status.objects.get(name="Active"))


class VPNTunnelEndpointAPITest(APIViewTestCases.APIViewTestCase):
    """VPNTunnelEndpoint API tests."""

    model = models.VPNTunnelEndpoint
    choices_fields = ()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        interfaces = Interface.objects.filter(device__isnull=False, vpn_tunnel_endpoints_src_int__isnull=True)

        cls.create_data = [
            {
                "source_interface": interfaces[0].pk,
                "vpn_profile": models.VPNProfile.objects.first().pk,
            },
            {
                "source_interface": interfaces[1].pk,
                "vpn_profile": models.VPNProfile.objects.first().pk,
            },
            {
                "source_interface": interfaces[2].pk,
                "vpn_profile": models.VPNProfile.objects.first().pk,
            },
        ]

        cls.update_data = {
            "vpn_profile": models.VPNProfile.objects.last().pk,
        }
