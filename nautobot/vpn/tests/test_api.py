"""Unit tests for vpn."""

from django.contrib.contenttypes.models import ContentType
from rest_framework import status

from nautobot.apps.testing import APIViewTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import Status
from nautobot.ipam.models import VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import VMInterface
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
    choices_fields = ("service_type",)

    @classmethod
    def _get_vpn_status(cls):
        """Get or create an Active status for VPN."""
        ct = ContentType.objects.get_for_model(models.VPN)
        vpn_status = Status.objects.filter(content_types=ct).first()
        if not vpn_status:
            vpn_status = Status.objects.get(name="Active")
            vpn_status.content_types.add(ct)
        return vpn_status

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        profiles = models.VPNProfile.objects.all()
        vpn_status = cls._get_vpn_status()

        models.VPN.objects.create(
            name="Existing VXLAN VPN API Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=vpn_status,
            vpn_id="19001",
        )
        models.VPN.objects.create(
            name="Existing VPLS VPN API Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPLS,
            status=vpn_status,
            vpn_id="19002",
        )
        models.VPN.objects.create(
            name="Existing IPSec VPN API Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_IPSEC,
            status=vpn_status,
        )

        cls.create_data = [
            {
                "name": "test 1",
                "description": "test value",
                "vpn_profile": profiles[1].pk,
                "service_type": choices.VPNServiceTypeChoices.TYPE_VXLAN,
                "status": vpn_status.pk,
                "vpn_id": "12001",
                "extra_attributes": {"flooding_mode": "ingress-replication"},
            },
            {
                "name": "test 2",
                "description": "test value",
                "vpn_id": "12002",
                "vpn_profile": profiles[2].pk,
                "service_type": choices.VPNServiceTypeChoices.TYPE_VPLS,
                "status": vpn_status.pk,
            },
            {
                "name": "test 3",
                "description": "test value",
                "vpn_id": "test value",
                "vpn_profile": profiles[3].pk,
                "service_type": choices.VPNServiceTypeChoices.TYPE_IPSEC,
                "status": vpn_status.pk,
            },
        ]

        cls.update_data = {
            "name": "test 3",
            "vpn_profile": profiles[4].pk,
            "service_type": choices.VPNServiceTypeChoices.TYPE_VXLAN_EVPN,
            "vpn_id": "13001",
        }

    def test_filter_by_service_type(self):
        """Test filtering VPNs by service type via API."""
        self.add_permissions("vpn.view_vpn")
        url = self._get_list_url()
        response = self.client.get(f"{url}?service_type={choices.VPNServiceTypeChoices.TYPE_VXLAN}", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_filter_by_vpn_id(self):
        """Test filtering VPNs by VPN ID via API."""
        self.add_permissions("vpn.view_vpn")
        vpn = models.VPN.objects.exclude(vpn_id="").first()
        self.assertIsNotNone(vpn)
        url = self._get_list_url()
        response = self.client.get(f"{url}?vpn_id={vpn.vpn_id}", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_partial_update_overlay_fields(self):
        """Test updating overlay-specific VPN fields via PATCH."""
        self.add_permissions("vpn.change_vpn")
        vpn = models.VPN.objects.first()
        url = self._get_detail_url(vpn)
        data = {
            "service_type": choices.VPNServiceTypeChoices.TYPE_VXLAN_EVPN,
            "vpn_id": "14001",
            "description": "Updated via PATCH",
        }
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        vpn.refresh_from_db()
        self.assertEqual(vpn.vpn_id, "14001")
        self.assertEqual(vpn.service_type, choices.VPNServiceTypeChoices.TYPE_VXLAN_EVPN)


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


class VPNTerminationAPITest(APIViewTestCases.APIViewTestCase):
    """VPNTermination API tests."""

    model = models.VPNTermination
    choices_fields = ()

    @classmethod
    def _get_vpn_status(cls):
        ct = ContentType.objects.get_for_model(models.VPN)
        vpn_status = Status.objects.filter(content_types=ct).first()
        if not vpn_status:
            vpn_status = Status.objects.get(name="Active")
            vpn_status.content_types.add(ct)
        return vpn_status

    @classmethod
    def _get_available_interfaces(cls):
        used_interface_ids = models.VPNTermination.objects.exclude(interface__isnull=True).values_list(
            "interface_id", flat=True
        )
        return Interface.objects.exclude(pk__in=used_interface_ids).filter(device__isnull=False)

    @classmethod
    def _get_available_vlans(cls):
        used_vlan_ids = models.VPNTermination.objects.exclude(vlan__isnull=True).values_list("vlan_id", flat=True)
        return VLAN.objects.exclude(pk__in=used_vlan_ids)

    @classmethod
    def _get_available_vm_interfaces(cls):
        used_vm_interface_ids = models.VPNTermination.objects.exclude(vm_interface__isnull=True).values_list(
            "vm_interface_id", flat=True
        )
        return VMInterface.objects.exclude(pk__in=used_vm_interface_ids)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        vpn_status = cls._get_vpn_status()
        cls.vpn = models.VPN.objects.create(
            name="VPN For Termination API Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=vpn_status,
            vpn_id="20001",
        )
        cls.vpn2 = models.VPN.objects.create(
            name="VPN For Termination API Update Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPLS,
            status=vpn_status,
            vpn_id="20002",
        )

        vlans = list(cls._get_available_vlans()[:6])
        if len(vlans) < 6:
            vlan_group = VLANGroup.objects.first()
            if vlan_group is None:
                vlan_group = VLANGroup.objects.create(name="VPN Termination API VLAN Group")
            active = Status.objects.get(name="Active")
            vlan_ct = ContentType.objects.get_for_model(VLAN)
            active.content_types.add(vlan_ct)
            for i in range(6 - len(vlans)):
                vlans.append(
                    VLAN.objects.create(
                        vid=4500 + i,
                        name=f"VPN Termination API VLAN {i}",
                        status=active,
                        vlan_group=vlan_group,
                    )
                )

        for vlan in vlans[:3]:
            models.VPNTermination.objects.create(vpn=cls.vpn, vlan=vlan)

        cls.create_data = [
            {"vpn": cls.vpn.pk, "vlan": vlans[3].pk},
            {"vpn": cls.vpn.pk, "vlan": vlans[4].pk},
            {"vpn": cls.vpn.pk, "vlan": vlans[5].pk},
        ]
        cls.update_data = {"vpn": cls.vpn2.pk}

    def test_filter_by_vpn(self):
        """Test filtering terminations by VPN via API."""
        self.add_permissions("vpn.view_vpntermination")
        url = self._get_list_url()
        response = self.client.get(f"{url}?vpn={self.vpn.pk}", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_create_termination_with_interface(self):
        """Test creating a termination to an interface via API."""
        interface = self._get_available_interfaces().first()
        if interface is None:
            self.skipTest("No unused interface available.")

        self.add_permissions(
            "vpn.add_vpntermination",
            "vpn.view_vpn",
            "vpn.view_vpntermination",
            "dcim.view_interface",
        )
        url = self._get_list_url()
        response = self.client.post(url, {"vpn": self.vpn.pk, "interface": interface.pk}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

    def test_create_termination_with_vm_interface(self):
        """Test creating a termination to a VM interface via API."""
        vm_interface = self._get_available_vm_interfaces().first()
        if vm_interface is None:
            self.skipTest("No unused VM interface available.")

        self.add_permissions(
            "vpn.add_vpntermination",
            "vpn.view_vpn",
            "vpn.view_vpntermination",
            "virtualization.view_vminterface",
        )
        url = self._get_list_url()
        response = self.client.post(
            url, {"vpn": self.vpn.pk, "vm_interface": vm_interface.pk}, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

    def test_p2p_termination_limit_via_api(self):
        """Test that P2P VPNs cannot have more than 2 terminations via API."""
        vpn_status = self._get_vpn_status()
        p2p_vpn = models.VPN.objects.create(
            name="P2P VPN API Limit Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPWS,
            status=vpn_status,
        )
        interfaces = list(self._get_available_interfaces()[:3])
        if len(interfaces) < 3:
            self.skipTest("Need at least three unused interfaces.")

        models.VPNTermination.objects.create(vpn=p2p_vpn, interface=interfaces[0])
        models.VPNTermination.objects.create(vpn=p2p_vpn, interface=interfaces[1])

        self.add_permissions(
            "vpn.add_vpntermination",
            "vpn.view_vpn",
            "vpn.view_vpntermination",
            "dcim.view_interface",
        )
        url = self._get_list_url()
        response = self.client.post(
            url, {"vpn": p2p_vpn.pk, "interface": interfaces[2].pk}, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_termination_fails_via_api(self):
        """Test that reusing the same object on another VPN termination fails."""
        interface = self._get_available_interfaces().first()
        if interface is None:
            self.skipTest("No unused interface available.")

        other_vpn = models.VPN.objects.create(
            name="VPN Duplicate Termination Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self._get_vpn_status(),
            vpn_id="21000",
        )
        models.VPNTermination.objects.create(vpn=self.vpn, interface=interface)

        self.add_permissions(
            "vpn.add_vpntermination",
            "vpn.view_vpn",
            "vpn.view_vpntermination",
            "dcim.view_interface",
        )
        url = self._get_list_url()
        response = self.client.post(
            url, {"vpn": other_vpn.pk, "interface": interface.pk}, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
