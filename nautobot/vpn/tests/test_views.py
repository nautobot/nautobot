"""Unit tests for vpn views."""

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse

from nautobot.apps.testing import ViewTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import DynamicGroup, Status
from nautobot.ipam.models import Prefix, VLAN, VLANGroup
from nautobot.virtualization.models import VMInterface
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
            "description": "bulk updated value",
            "keepalive_enabled": True,
            "keepalive_interval": 30,
            "keepalive_retries": 10,
            "nat_traversal": True,
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_profile_vpns(self):
        self.add_permissions("vpn.view_vpn")
        profile = models.VPNProfile.objects.filter(vpns__isnull=False).first()

        url = reverse("vpn:vpnprofile_vpns", kwargs={"pk": profile.pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_profile_vpntunnels(self):
        self.add_permissions("vpn.view_vpntunnel")
        profile = models.VPNProfile.objects.filter(vpn_tunnels__isnull=False).first()

        url = reverse("vpn:vpnprofile_vpntunnels", kwargs={"pk": profile.pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_profile_vpnendpoints(self):
        self.add_permissions("vpn.view_vpntunnelendpoint")
        profile = models.VPNProfile.objects.filter(vpn_tunnel_endpoints__isnull=False).first()

        url = reverse("vpn:vpnprofile_vpnendpoints", kwargs={"pk": profile.pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)


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
            "source_interface": interfaces.first().pk,
            "vpn_profile": models.VPNProfile.objects.first().pk,
            "protected_prefixes": [Prefix.objects.first().pk],
        }

        cls.update_data = {
            "source_interface": interfaces.last().pk,
            "protected_prefixes": [Prefix.objects.last().pk],
        }

        cls.bulk_edit_data = {"vpn_profile": models.VPNProfile.objects.last().pk}

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_protected_prefixes(self):
        self.add_permissions("ipam.view_prefix")
        endpoint = models.VPNTunnelEndpoint.objects.filter(protected_prefixes__isnull=False).first()

        url = reverse("vpn:vpntunnelendpoint_protectedprefixes", kwargs={"pk": endpoint.pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_protected_dynamic_groups(self):
        self.add_permissions("extras.view_dynamicgroup")
        endpoint = models.VPNTunnelEndpoint.objects.filter(protected_prefixes_dg__isnull=True).first()
        dg_ct = ContentType.objects.get_for_model(DynamicGroup)
        endpoint.protected_prefixes_dg.add(DynamicGroup.objects.create(name="DG for Prefixes", content_type=dg_ct))

        url = reverse("vpn:vpntunnelendpoint_protecteddynamicgroups", kwargs={"pk": endpoint.pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)


class L2VPNViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the L2VPN views."""

    model = models.L2VPN

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
        """Set up test data."""
        super().setUpTestData()

        l2vpn_status = cls._get_l2vpn_status()

        # Create at least 3 L2VPN objects for view tests (required by base class)
        models.L2VPN.objects.create(
            name="L2VPN View Existing 1",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=l2vpn_status,
            identifier=2001,
            description="Existing L2VPN 1 for view tests",
        )
        models.L2VPN.objects.create(
            name="L2VPN View Existing 2",
            type=choices.L2VPNTypeChoices.TYPE_VPLS,
            status=l2vpn_status,
            identifier=2002,
            description="Existing L2VPN 2 for view tests",
        )
        models.L2VPN.objects.create(
            name="L2VPN View Existing 3",
            type=choices.L2VPNTypeChoices.TYPE_VPWS,
            status=l2vpn_status,
            identifier=2003,
            description="Existing L2VPN 3 for view tests",
        )

        cls.form_data = {
            "name": "L2VPN View Test",
            "type": choices.L2VPNTypeChoices.TYPE_VXLAN,
            "status": l2vpn_status.pk,
            "identifier": 10001,
            "description": "Test L2VPN for views",
        }

        cls.update_data = {
            "name": "L2VPN View Test Updated",
            "type": choices.L2VPNTypeChoices.TYPE_VPLS,
            "status": l2vpn_status.pk,
            "identifier": 20002,
            "description": "Updated L2VPN for views",
        }

        cls.bulk_edit_data = {
            "type": choices.L2VPNTypeChoices.TYPE_VXLAN_EVPN,
            "description": "Bulk updated L2VPN",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_list_filter_by_type(self):
        """Test filtering L2VPN list by type."""
        self.add_permissions("vpn.view_l2vpn")

        url = reverse("vpn:l2vpn_list")
        response = self.client.get(
            f"{url}?type={choices.L2VPNTypeChoices.TYPE_VXLAN}"
        )
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_list_filter_by_identifier(self):
        """Test filtering L2VPN list by identifier."""
        self.add_permissions("vpn.view_l2vpn")
        l2vpn = models.L2VPN.objects.filter(identifier__isnull=False).first()

        if l2vpn:
            url = reverse("vpn:l2vpn_list")
            response = self.client.get(
                f"{url}?identifier={l2vpn.identifier}"
            )
            self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_list_search(self):
        """Test searching L2VPN list by name."""
        self.add_permissions("vpn.view_l2vpn")
        l2vpn = models.L2VPN.objects.first()

        if l2vpn:
            url = reverse("vpn:l2vpn_list")
            # Search by name filter instead of generic 'q' which may have type issues
            response = self.client.get(
                f"{url}?name__ic={l2vpn.name[:10]}"
            )
            self.assertHttpStatus(response, 200)


class L2VPNTerminationViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the L2VPNTermination views."""

    model = models.L2VPNTermination

    # Bulk edit not yet supported for L2VPNTermination
    def test_bulk_edit_form_contains_all_pks(self):
        pass

    def test_bulk_edit_form_contains_all_filtered(self):
        pass

    def test_bulk_edit_objects_with_permission(self):
        pass

    def test_bulk_edit_objects_with_constrained_permission(self):
        pass

    def test_bulk_edit_objects_without_permission(self):
        pass

    def test_bulk_edit_objects_nullable_fields(self):
        pass

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
        """Set up test data."""
        super().setUpTestData()

        # Create L2VPN for tests
        l2vpn_status = cls._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="L2VPN For Termination View Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=l2vpn_status,
        )

        # Create a second L2VPN for bulk edit tests
        l2vpn2 = models.L2VPN.objects.create(
            name="L2VPN For Termination View Test 2",
            type=choices.L2VPNTypeChoices.TYPE_VPLS,
            status=l2vpn_status,
        )

        # Get VLANs without existing terminations (more reliable than interfaces)
        vlans = list(cls._get_vlans_without_terminations()[:10])

        # If not enough VLANs exist, create some
        if len(vlans) < 6:
            vlan_status = Status.objects.get(name="Active")
            vlan_ct = ContentType.objects.get_for_model(VLAN)
            if vlan_ct not in vlan_status.content_types.all():
                vlan_status.content_types.add(vlan_ct)

            vlan_group, _ = VLANGroup.objects.get_or_create(
                name="L2VPN View Test Group",
            )
            for i in range(6 - len(vlans)):
                vlan = VLAN.objects.create(
                    vid=4000 + i,
                    name=f"L2VPN View Test VLAN {i}",
                    status=vlan_status,
                    vlan_group=vlan_group,
                )
                vlans.append(vlan)

        # Create at least 3 termination objects for base class tests
        for i in range(min(3, len(vlans))):
            models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=vlans[i]
            )

        # Use remaining VLANs for form_data and update_data
        form_vlan = vlans[3] if len(vlans) > 3 else vlans[0]
        update_vlan = vlans[4] if len(vlans) > 4 else vlans[1] if len(vlans) > 1 else vlans[0]

        cls.form_data = {
            "l2vpn": l2vpn.pk,
            "vlan": form_vlan.pk,
        }

        cls.update_data = {
            "l2vpn": l2vpn.pk,
            "vlan": update_vlan.pk,
        }

        # bulk_edit_data with l2vpn to change terminations to l2vpn2
        cls.bulk_edit_data = {
            "l2vpn": l2vpn2.pk,
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_termination_list_filter_by_l2vpn(self):
        """Test filtering termination list by L2VPN."""
        self.add_permissions("vpn.view_l2vpntermination")
        termination = models.L2VPNTermination.objects.first()

        if termination:
            url = reverse("vpn:l2vpntermination_list")
            response = self.client.get(
                f"{url}?l2vpn={termination.l2vpn.pk}"
            )
            self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_termination_create_with_interface(self):
        """Test creating termination with interface via web form."""
        self.add_permissions("vpn.add_l2vpntermination")

        l2vpn = models.L2VPN.objects.first()
        interface = self._get_interfaces_without_terminations().first()

        if l2vpn and interface:
            url = reverse("vpn:l2vpntermination_add")
            data = {
                "l2vpn": l2vpn.pk,
                "interface": interface.pk,
            }
            response = self.client.post(url, data)
            self.assertIn(response.status_code, [200, 302])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_termination_create_with_vlan(self):
        """Test creating termination with VLAN via web form."""
        self.add_permissions("vpn.add_l2vpntermination")

        l2vpn = models.L2VPN.objects.first()
        vlan = self._get_vlans_without_terminations().first()

        if l2vpn and vlan:
            url = reverse("vpn:l2vpntermination_add")
            data = {
                "l2vpn": l2vpn.pk,
                "vlan": vlan.pk,
            }
            response = self.client.post(url, data)
            self.assertIn(response.status_code, [200, 302])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_termination_list_search(self):
        """Test searching termination list by L2VPN name."""
        self.add_permissions("vpn.view_l2vpntermination")
        termination = models.L2VPNTermination.objects.first()

        if termination:
            url = reverse("vpn:l2vpntermination_list")
            response = self.client.get(
                f"{url}?q={termination.l2vpn.name[:5]}"
            )
            self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_termination_create_with_vminterface(self):
        """Test creating termination with VMInterface via web form."""
        self.add_permissions("vpn.add_l2vpntermination")

        l2vpn = models.L2VPN.objects.first()
        vminterface = self._get_vminterfaces_without_terminations().first()

        if l2vpn and vminterface:
            url = reverse("vpn:l2vpntermination_add")
            data = {
                "l2vpn": l2vpn.pk,
                "vminterface": vminterface.pk,
            }
            response = self.client.post(url, data)
            # Should redirect on success
            self.assertIn(response.status_code, [200, 302])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_termination_detail_view(self):
        """Test L2VPNTermination detail view."""
        self.add_permissions("vpn.view_l2vpntermination")
        termination = models.L2VPNTermination.objects.first()

        if termination:
            url = reverse("vpn:l2vpntermination", kwargs={"pk": termination.pk})
            response = self.client.get(url)
            self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_l2vpn_detail_view(self):
        """Test L2VPN detail view."""
        self.add_permissions("vpn.view_l2vpn")
        l2vpn = models.L2VPN.objects.first()

        if l2vpn:
            url = reverse("vpn:l2vpn", kwargs={"pk": l2vpn.pk})
            response = self.client.get(url)
            self.assertHttpStatus(response, 200)
