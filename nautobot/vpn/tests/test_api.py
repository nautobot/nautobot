"""Unit tests for vpn."""

from django.contrib.contenttypes.models import ContentType
from rest_framework import status

from nautobot.apps.testing import APIViewTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import Status
from nautobot.ipam.models import RouteTarget, VLAN, VLANGroup
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


class L2VPNAPITest(APIViewTestCases.APIViewTestCase):
    """L2VPN API tests."""

    model = models.L2VPN
    choices_fields = ("type",)

    @classmethod
    def _get_l2vpn_status(cls):
        """Get or create a Status for L2VPN model."""
        ct = ContentType.objects.get_for_model(models.L2VPN)
        l2vpn_status = Status.objects.filter(content_types=ct).first()
        if not l2vpn_status:
            l2vpn_status = Status.objects.get(name="Active")
            l2vpn_status.content_types.add(ct)
        return l2vpn_status

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        l2vpn_status = cls._get_l2vpn_status()

        # Create at least 3 L2VPN objects for GET tests (required by base class)
        models.L2VPN.objects.create(
            name="L2VPN API Existing 1",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=l2vpn_status,
            identifier=1001,
            description="Existing L2VPN 1 for API tests",
        )
        models.L2VPN.objects.create(
            name="L2VPN API Existing 2",
            type=choices.L2VPNTypeChoices.TYPE_VPLS,
            status=l2vpn_status,
            identifier=1002,
            description="Existing L2VPN 2 for API tests",
        )
        models.L2VPN.objects.create(
            name="L2VPN API Existing 3",
            type=choices.L2VPNTypeChoices.TYPE_VPWS,
            status=l2vpn_status,
            identifier=1003,
            description="Existing L2VPN 3 for API tests",
        )

        cls.create_data = [
            {
                "name": "L2VPN API Test 1",
                "type": choices.L2VPNTypeChoices.TYPE_VXLAN,
                "status": l2vpn_status.pk,
                "identifier": 10001,
                "description": "Test L2VPN via API",
            },
            {
                "name": "L2VPN API Test 2",
                "type": choices.L2VPNTypeChoices.TYPE_VPLS,
                "status": l2vpn_status.pk,
                "identifier": 10002,
                "description": "Another test L2VPN",
            },
            {
                "name": "L2VPN API Test 3",
                "type": choices.L2VPNTypeChoices.TYPE_VPWS,
                "status": l2vpn_status.pk,
                "identifier": 10003,
            },
        ]

        cls.update_data = {
            "name": "L2VPN API Updated",
            "type": choices.L2VPNTypeChoices.TYPE_VXLAN_EVPN,
            "description": "Updated via API",
            "identifier": 20001,
        }

    def test_create_l2vpn_with_route_targets(self):
        """Test creating L2VPN with import/export route targets."""
        route_targets = list(RouteTarget.objects.all()[:2])
        if len(route_targets) >= 2:
            self.add_permissions("vpn.add_l2vpn")
            # Get status fresh within the test
            ct = ContentType.objects.get_for_model(models.L2VPN)
            l2vpn_status = Status.objects.filter(content_types=ct).first()
            if not l2vpn_status:
                l2vpn_status = Status.objects.get(name="Active")
                l2vpn_status.content_types.add(ct)

            data = {
                "name": "L2VPN With Route Targets",
                "type": choices.L2VPNTypeChoices.TYPE_VXLAN_EVPN,
                "status": l2vpn_status.pk,
                "import_targets": [rt.pk for rt in route_targets[:1]],
                "export_targets": [rt.pk for rt in route_targets[1:2]],
            }

            url = self._get_list_url()
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)

            l2vpn = models.L2VPN.objects.get(pk=response.data["id"])
            self.assertEqual(l2vpn.import_targets.count(), 1)
            self.assertEqual(l2vpn.export_targets.count(), 1)

    def test_create_l2vpn_with_tenant(self):
        """Test creating L2VPN with tenant."""
        tenant = Tenant.objects.first()
        if tenant:
            self.add_permissions("vpn.add_l2vpn")
            # Get status fresh within the test
            ct = ContentType.objects.get_for_model(models.L2VPN)
            l2vpn_status = Status.objects.filter(content_types=ct).first()
            if not l2vpn_status:
                l2vpn_status = Status.objects.get(name="Active")
                l2vpn_status.content_types.add(ct)

            data = {
                "name": "L2VPN With Tenant",
                "type": choices.L2VPNTypeChoices.TYPE_VXLAN,
                "status": l2vpn_status.pk,
                "tenant": tenant.pk,
            }

            url = self._get_list_url()
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)

            l2vpn = models.L2VPN.objects.get(pk=response.data["id"])
            self.assertEqual(l2vpn.tenant, tenant)


    def test_filter_by_type(self):
        """Test filtering L2VPNs by type via API."""
        self.add_permissions("vpn.view_l2vpn")

        url = self._get_list_url()
        response = self.client.get(
            f"{url}?type={choices.L2VPNTypeChoices.TYPE_VXLAN}",
            **self.header
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_filter_by_identifier(self):
        """Test filtering L2VPNs by identifier via API."""
        self.add_permissions("vpn.view_l2vpn")
        l2vpn = models.L2VPN.objects.filter(identifier__isnull=False).first()

        if l2vpn:
            url = self._get_list_url()
            response = self.client.get(
                f"{url}?identifier={l2vpn.identifier}",
                **self.header
            )
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_partial_update_l2vpn(self):
        """Test partial update (PATCH) of L2VPN via API."""
        self.add_permissions("vpn.change_l2vpn")
        l2vpn = models.L2VPN.objects.first()

        if l2vpn:
            url = self._get_detail_url(l2vpn)
            data = {
                "description": "Updated via PATCH",
            }
            response = self.client.patch(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)

            l2vpn.refresh_from_db()
            self.assertEqual(l2vpn.description, "Updated via PATCH")

    def test_delete_l2vpn(self):
        """Test deleting L2VPN via API."""
        self.add_permissions("vpn.delete_l2vpn")
        l2vpn_status = self._get_l2vpn_status()

        l2vpn = models.L2VPN.objects.create(
            name="L2VPN To Delete",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=l2vpn_status,
        )
        l2vpn_pk = l2vpn.pk

        url = self._get_detail_url(l2vpn)
        response = self.client.delete(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)

        self.assertFalse(models.L2VPN.objects.filter(pk=l2vpn_pk).exists())



class L2VPNTerminationAPITest(APIViewTestCases.APIViewTestCase):
    """L2VPNTermination API tests."""

    model = models.L2VPNTermination
    choices_fields = ("assigned_object_type",)

    @classmethod
    def _get_l2vpn_status(cls):
        """Get or create a Status for L2VPN model."""
        ct = ContentType.objects.get_for_model(models.L2VPN)
        l2vpn_status = Status.objects.filter(content_types=ct).first()
        if not l2vpn_status:
            l2vpn_status = Status.objects.get(name="Active")
            l2vpn_status.content_types.add(ct)
        return l2vpn_status

    @classmethod
    def _get_interfaces_without_terminations(cls):
        """Get interfaces that are not already assigned to an L2VPNTermination."""
        interface_ct = ContentType.objects.get_for_model(Interface)
        used_interface_ids = models.L2VPNTermination.objects.filter(
            assigned_object_type=interface_ct
        ).values_list("assigned_object_id", flat=True)
        return Interface.objects.exclude(pk__in=used_interface_ids).filter(device__isnull=False)

    @classmethod
    def _get_vlans_without_terminations(cls):
        """Get VLANs that are not already assigned to an L2VPNTermination."""
        vlan_ct = ContentType.objects.get_for_model(VLAN)
        used_vlan_ids = models.L2VPNTermination.objects.filter(
            assigned_object_type=vlan_ct
        ).values_list("assigned_object_id", flat=True)
        return VLAN.objects.exclude(pk__in=used_vlan_ids)

    @classmethod
    def _get_vminterfaces_without_terminations(cls):
        """Get VMInterfaces that are not already assigned to an L2VPNTermination."""
        vminterface_ct = ContentType.objects.get_for_model(VMInterface)
        used_vminterface_ids = models.L2VPNTermination.objects.filter(
            assigned_object_type=vminterface_ct
        ).values_list("assigned_object_id", flat=True)
        return VMInterface.objects.exclude(pk__in=used_vminterface_ids)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create L2VPN for tests
        l2vpn_status = cls._get_l2vpn_status()
        cls.l2vpn = models.L2VPN.objects.create(
            name="L2VPN For Termination API Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=l2vpn_status,
        )

        # Get interfaces without existing terminations
        interfaces = list(cls._get_interfaces_without_terminations()[:9])

        # If not enough interfaces, create VLANs for testing
        if len(interfaces) < 6:
            # Create VLAN group and VLANs for termination tests
            vlan_status = Status.objects.get(name="Active")
            vlan_group = VLANGroup.objects.first()
            if not vlan_group:
                vlan_group = VLANGroup.objects.create(name="L2VPN Test VLAN Group")

            # Create 9 VLANs for testing
            vlans = []
            for i in range(9):
                vlan = VLAN.objects.create(
                    vid=3000 + i,
                    name=f"L2VPN Test VLAN {i}",
                    status=vlan_status,
                    vlan_group=vlan_group,
                )
                vlans.append(vlan)

            vlan_ct = ContentType.objects.get_for_model(VLAN)

            # Create 3 terminations for base class tests
            for i in range(3):
                models.L2VPNTermination.objects.create(
                    l2vpn=cls.l2vpn,
                    assigned_object=vlans[i]
                )

            # Set up create_data for POST tests
            cls.create_data = [
                {
                    "l2vpn": cls.l2vpn.pk,
                    "assigned_object_type": f"{vlan_ct.app_label}.{vlan_ct.model}",
                    "assigned_object_id": vlans[3].pk,
                },
                {
                    "l2vpn": cls.l2vpn.pk,
                    "assigned_object_type": f"{vlan_ct.app_label}.{vlan_ct.model}",
                    "assigned_object_id": vlans[4].pk,
                },
                {
                    "l2vpn": cls.l2vpn.pk,
                    "assigned_object_type": f"{vlan_ct.app_label}.{vlan_ct.model}",
                    "assigned_object_id": vlans[5].pk,
                },
            ]
        else:
            interface_ct = ContentType.objects.get_for_model(Interface)

            # Create 3 terminations for base class tests
            for i in range(3):
                models.L2VPNTermination.objects.create(
                    l2vpn=cls.l2vpn,
                    assigned_object=interfaces[i]
                )

            # Set up create_data for POST tests
            cls.create_data = [
                {
                    "l2vpn": cls.l2vpn.pk,
                    "assigned_object_type": f"{interface_ct.app_label}.{interface_ct.model}",
                    "assigned_object_id": interfaces[3].pk,
                },
                {
                    "l2vpn": cls.l2vpn.pk,
                    "assigned_object_type": f"{interface_ct.app_label}.{interface_ct.model}",
                    "assigned_object_id": interfaces[4].pk,
                },
                {
                    "l2vpn": cls.l2vpn.pk,
                    "assigned_object_type": f"{interface_ct.app_label}.{interface_ct.model}",
                    "assigned_object_id": interfaces[5].pk,
                },
            ]

        # Create a second L2VPN for update test
        cls.l2vpn2 = models.L2VPN.objects.create(
            name="L2VPN For Termination API Update Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=l2vpn_status,
        )

        cls.update_data = {
            "l2vpn": cls.l2vpn2.pk,
        }

    # Note: test_create_object from the base class already tests creating L2VPNTerminations
    # with VLANs. The custom termination tests below validate specific model-level behavior
    # rather than API creation (which is covered by test_create_object).

    def test_filter_by_l2vpn(self):
        """Test filtering terminations by L2VPN via API."""
        self.add_permissions("vpn.view_l2vpntermination")
        termination = models.L2VPNTermination.objects.first()

        if termination:
            url = self._get_list_url()
            response = self.client.get(
                f"{url}?l2vpn={termination.l2vpn.pk}",
                **self.header
            )
            self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_p2p_termination_limit_via_api(self):
        """Test that P2P L2VPN cannot have more than 2 terminations via API."""
        # Create a P2P L2VPN
        l2vpn_status = self._get_l2vpn_status()
        p2p_l2vpn = models.L2VPN.objects.create(
            name="P2P L2VPN API Limit Test",
            type=choices.L2VPNTypeChoices.TYPE_VPWS,  # P2P type
            status=l2vpn_status,
        )

        interfaces = self._get_interfaces_without_terminations()[:3]

        if interfaces.count() >= 3:
            self.add_permissions("vpn.add_l2vpntermination")
            interface_ct = ContentType.objects.get_for_model(Interface)

            # Create first 2 terminations
            models.L2VPNTermination.objects.create(
                l2vpn=p2p_l2vpn,
                assigned_object=interfaces[0]
            )
            models.L2VPNTermination.objects.create(
                l2vpn=p2p_l2vpn,
                assigned_object=interfaces[1]
            )

            # Try to create a 3rd termination
            data = {
                "l2vpn": p2p_l2vpn.pk,
                "assigned_object_type": f"{interface_ct.app_label}.{interface_ct.model}",
                "assigned_object_id": str(interfaces[2].pk),
            }

            url = self._get_list_url()
            response = self.client.post(url, data, format="json", **self.header)
            # Should fail validation
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_termination_fails_via_api(self):
        """Test that creating duplicate termination for same object fails via API."""
        l2vpn_status = self._get_l2vpn_status()
        l2vpn1 = models.L2VPN.objects.create(
            name="L2VPN Dup API Test 1",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=l2vpn_status,
        )
        l2vpn2 = models.L2VPN.objects.create(
            name="L2VPN Dup API Test 2",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=l2vpn_status,
        )

        interface = self._get_interfaces_without_terminations().first()

        if interface:
            self.add_permissions("vpn.add_l2vpntermination")
            interface_ct = ContentType.objects.get_for_model(Interface)

            # Create first termination
            models.L2VPNTermination.objects.create(
                l2vpn=l2vpn1,
                assigned_object=interface
            )

            # Try to create second termination to same interface
            data = {
                "l2vpn": l2vpn2.pk,
                "assigned_object_type": f"{interface_ct.app_label}.{interface_ct.model}",
                "assigned_object_id": str(interface.pk),
            }

            url = self._get_list_url()
            response = self.client.post(url, data, format="json", **self.header)
            # Should fail validation
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_delete_termination(self):
        """Test deleting L2VPNTermination via API."""
        self.add_permissions("vpn.delete_l2vpntermination")

        l2vpn_status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="L2VPN Delete Term Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=l2vpn_status,
        )

        interface = self._get_interfaces_without_terminations().first()

        if interface:
            termination = models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=interface
            )
            termination_pk = termination.pk

            url = self._get_detail_url(termination)
            response = self.client.delete(url, **self.header)
            self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)

            self.assertFalse(models.L2VPNTermination.objects.filter(pk=termination_pk).exists())
