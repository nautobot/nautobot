"""Unit tests for vpn views."""

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse

from nautobot.apps.testing import ViewTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import DynamicGroup, Status
from nautobot.ipam.models import Prefix, VLAN, VLANGroup
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface
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

        ct = ContentType.objects.get_for_model(models.VPN)
        vpn_status = Status.objects.filter(content_types=ct).first()
        if not vpn_status:
            vpn_status = Status.objects.get(name="Active")
            vpn_status.content_types.add(ct)

        models.VPN.objects.create(
            name="Existing VXLAN VPN View Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=vpn_status,
            vpn_id="16011",
        )
        models.VPN.objects.create(
            name="Existing VPLS VPN View Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPLS,
            status=vpn_status,
            vpn_id="16012",
        )
        models.VPN.objects.create(
            name="Existing IPSec VPN View Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_IPSEC,
            status=vpn_status,
        )

        cls.form_data = {
            "name": "test value",
            "description": "test value",
            "vpn_profile": models.VPNProfile.objects.first().pk,
            "service_type": choices.VPNServiceTypeChoices.TYPE_VXLAN,
            "status": vpn_status.pk,
            "vpn_id": "16001",
        }

        cls.update_data = {
            "name": "updated value",
            "description": "updated value",
            "vpn_id": "16002",
            "vpn_profile": models.VPNProfile.objects.last().pk,
            "service_type": choices.VPNServiceTypeChoices.TYPE_VPLS,
            "status": vpn_status.pk,
        }

        cls.bulk_edit_data = {
            "description": "bulk updated value",
            "service_type": choices.VPNServiceTypeChoices.TYPE_VXLAN_EVPN,
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_vpn_list_filter_by_service_type(self):
        """Test filtering VPN list by service type."""
        self.add_permissions("vpn.view_vpn")
        url = reverse("vpn:vpn_list")
        response = self.client.get(f"{url}?service_type={choices.VPNServiceTypeChoices.TYPE_VXLAN}")
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_vpn_list_filter_by_vpn_id(self):
        """Test filtering VPN list by VPN ID."""
        self.add_permissions("vpn.view_vpn")
        vpn = models.VPN.objects.exclude(vpn_id="").first()
        self.assertIsNotNone(vpn)
        url = reverse("vpn:vpn_list")
        response = self.client.get(f"{url}?vpn_id={vpn.vpn_id}")
        self.assertHttpStatus(response, 200)


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


class VPNTerminationViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    # pylint: disable=too-many-ancestors
    """Test the VPNTermination views."""

    model = models.VPNTermination

    @classmethod
    def _get_vpn_status(cls):
        """Get or create a Status for VPN."""
        ct = ContentType.objects.get_for_model(models.VPN)
        vpn_status = Status.objects.filter(content_types=ct).first()
        if not vpn_status:
            vpn_status = Status.objects.get(name="Active")
            vpn_status.content_types.add(ct)
        return vpn_status

    @classmethod
    def _get_interfaces_without_terminations(cls):
        """Get interfaces not already used by a VPNTermination."""
        used_interface_ids = models.VPNTermination.objects.exclude(interface__isnull=True).values_list(
            "interface_id", flat=True
        )
        return Interface.objects.exclude(pk__in=used_interface_ids).filter(device__isnull=False)

    @classmethod
    def _get_vlans_without_terminations(cls):
        """Get VLANs not already used by a VPNTermination."""
        used_vlan_ids = models.VPNTermination.objects.exclude(vlan__isnull=True).values_list("vlan_id", flat=True)
        return VLAN.objects.exclude(pk__in=used_vlan_ids)

    @classmethod
    def _get_vm_interfaces_without_terminations(cls):
        """Get VM interfaces not already used by a VPNTermination."""
        used_vminterface_ids = models.VPNTermination.objects.exclude(vm_interface__isnull=True).values_list(
            "vm_interface_id", flat=True
        )
        available_vm_interfaces = VMInterface.objects.exclude(pk__in=used_vminterface_ids)
        if available_vm_interfaces.exists():
            return available_vm_interfaces

        vm = VirtualMachine.objects.first()
        if vm is None:
            cluster_type, _ = ClusterType.objects.get_or_create(name=f"{cls.__name__} Cluster Type")
            cluster, _ = Cluster.objects.get_or_create(
                name=f"{cls.__name__} Cluster",
                defaults={"cluster_type": cluster_type},
            )
            if cluster.cluster_type_id != cluster_type.id:
                cluster.cluster_type = cluster_type
                cluster.save()

            vm_status = Status.objects.get_for_model(VirtualMachine).first()
            if vm_status is None:
                vm_ct = ContentType.objects.get_for_model(VirtualMachine)
                vm_status = Status.objects.get(name="Active")
                vm_status.content_types.add(vm_ct)

            vm, _ = VirtualMachine.objects.get_or_create(
                name=f"{cls.__name__} VM",
                defaults={"cluster": cluster, "status": vm_status},
            )
            if vm.cluster_id != cluster.id or vm.status_id != vm_status.id:
                vm.cluster = cluster
                vm.status = vm_status
                vm.save()

        vm_interface_status = Status.objects.get_for_model(VMInterface).first()
        if vm_interface_status is None:
            vm_interface_ct = ContentType.objects.get_for_model(VMInterface)
            vm_interface_status = Status.objects.get(name="Active")
            vm_interface_status.content_types.add(vm_interface_ct)

        VMInterface.objects.create(
            virtual_machine=vm,
            name=f"vpn-termination-view-{cls.__name__.lower()}",
            status=vm_interface_status,
        )
        return VMInterface.objects.exclude(pk__in=used_vminterface_ids)

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        vpn_status = cls._get_vpn_status()
        vpn = models.VPN.objects.create(
            name="VPN For Termination View Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=vpn_status,
            vpn_id="17001",
        )
        vpn2 = models.VPN.objects.create(
            name="VPN For Termination View Test 2",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPLS,
            status=vpn_status,
            vpn_id="17002",
        )

        vlans = list(cls._get_vlans_without_terminations()[:10])
        if len(vlans) < 6:
            vlan_status = Status.objects.get(name="Active")
            vlan_ct = ContentType.objects.get_for_model(VLAN)
            if vlan_ct not in vlan_status.content_types.all():
                vlan_status.content_types.add(vlan_ct)

            vlan_group, _ = VLANGroup.objects.get_or_create(
                name="VPN Termination View Test Group",
            )
            for i in range(6 - len(vlans)):
                vlan = VLAN.objects.create(
                    vid=4000 + i,
                    name=f"VPN Termination View Test VLAN {i}",
                    status=vlan_status,
                    vlan_group=vlan_group,
                )
                vlans.append(vlan)

        for i in range(min(3, len(vlans))):
            models.VPNTermination.objects.create(vpn=vpn, vlan=vlans[i])

        form_vlan = vlans[3] if len(vlans) > 3 else vlans[0]
        update_vlan = vlans[4] if len(vlans) > 4 else vlans[1] if len(vlans) > 1 else vlans[0]

        cls.form_data = {
            "vpn": vpn.pk,
            "vlan": form_vlan.pk,
        }

        cls.update_data = {
            "vpn": vpn.pk,
            "vlan": update_vlan.pk,
        }

        cls.bulk_edit_data = {
            "vpn": vpn2.pk,
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_termination_list_filter_by_vpn(self):
        """Test filtering termination list by VPN."""
        self.add_permissions("vpn.view_vpntermination")
        termination = models.VPNTermination.objects.first()

        self.assertIsNotNone(termination)
        url = reverse("vpn:vpntermination_list")
        response = self.client.get(f"{url}?vpn={termination.vpn.pk}")
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_termination_create_with_interface(self):
        """Test creating a termination with interface via web form."""
        self.add_permissions("vpn.add_vpntermination")

        vpn = models.VPN.objects.first()
        interface = self._get_interfaces_without_terminations().first()

        self.assertIsNotNone(vpn)
        self.assertIsNotNone(interface)
        url = reverse("vpn:vpntermination_add")
        data = {
            "vpn": vpn.pk,
            "interface": interface.pk,
        }
        response = self.client.post(url, data)
        self.assertIn(response.status_code, [200, 302])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_termination_create_with_vlan(self):
        """Test creating a termination with VLAN via web form."""
        self.add_permissions("vpn.add_vpntermination")

        vpn = models.VPN.objects.first()
        vlan = self._get_vlans_without_terminations().first()

        self.assertIsNotNone(vpn)
        self.assertIsNotNone(vlan)
        url = reverse("vpn:vpntermination_add")
        data = {
            "vpn": vpn.pk,
            "vlan": vlan.pk,
        }
        response = self.client.post(url, data)
        self.assertIn(response.status_code, [200, 302])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_termination_list_search(self):
        """Test searching termination list by VPN name."""
        self.add_permissions("vpn.view_vpntermination")
        termination = models.VPNTermination.objects.first()

        self.assertIsNotNone(termination)
        url = reverse("vpn:vpntermination_list")
        response = self.client.get(f"{url}?q={termination.vpn.name[:5]}")
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_termination_create_with_vm_interface(self):
        """Test creating a termination with VM interface via web form."""
        self.add_permissions("vpn.add_vpntermination")

        vpn = models.VPN.objects.first()
        vm_interface = self._get_vm_interfaces_without_terminations().first()

        self.assertIsNotNone(vpn)
        self.assertIsNotNone(vm_interface)
        url = reverse("vpn:vpntermination_add")
        data = {
            "vpn": vpn.pk,
            "vm_interface": vm_interface.pk,
        }
        response = self.client.post(url, data)
        self.assertIn(response.status_code, [200, 302])
