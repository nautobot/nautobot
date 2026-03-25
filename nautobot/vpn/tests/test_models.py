"""Test vpn models."""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from nautobot.apps.testing import ModelTestCases
from nautobot.dcim.models import Device, Interface, Module
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, RouteTarget, VLAN, VLANGroup
from nautobot.virtualization.models import VMInterface
from nautobot.vpn import choices, models

class TestVPNProfileModel(ModelTestCases.BaseModelTestCase):
    """Test VPNProfile model."""

    model = models.VPNProfile


class TestVPNPhase1PolicyModel(ModelTestCases.BaseModelTestCase):
    """Test VPNPhase1Policy model."""

    model = models.VPNPhase1Policy


class TestVPNPhase2PolicyModel(ModelTestCases.BaseModelTestCase):
    """Test VPNPhase2Policy model."""

    model = models.VPNPhase2Policy


class VPNProfilePhase1PolicyAssignmentModel(ModelTestCases.BaseModelTestCase):
    """Test VPNPhase1Policy model."""

    model = models.VPNProfilePhase1PolicyAssignment


class VPNProfilePhase2PolicyAssignmentModel(ModelTestCases.BaseModelTestCase):
    """Test VPNPhase1Policy model."""

    model = models.VPNProfilePhase2PolicyAssignment


class TestVPNModel(ModelTestCases.BaseModelTestCase):
    """Test VPN model."""

    model = models.VPN


class TestVPNTunnelModel(ModelTestCases.BaseModelTestCase):
    """Test VPNTunnel model."""

    model = models.VPNTunnel

    def test_clean(self):
        """Test custom clean method."""
        endpoint = models.VPNTunnelEndpoint.objects.first()
        tunnel = models.VPNTunnel(
            endpoint_a=endpoint,
            endpoint_z=endpoint,
        )
        with self.assertRaises(ValidationError):
            tunnel.clean()


class TestVPNTunnelEndpointModel(ModelTestCases.BaseModelTestCase):
    """Test VPNTunnelEndpoint model."""

    model = models.VPNTunnelEndpoint

    def test_clean(self):
        """Test model constraints."""
        with self.subTest("Test source_ipaddress conflicts with source_fqdn"):
            endpoint = models.VPNTunnelEndpoint(source_ipaddress=IPAddress.objects.first(), source_fqdn="cloud.com")
            with self.assertRaises(ValidationError):
                endpoint.clean()

        with self.subTest("Test at least one required field is missing"):
            endpoint = models.VPNTunnelEndpoint()
            with self.assertRaises(ValidationError):
                endpoint.clean()

        with self.subTest("Test Interface without device"):
            endpoint = models.VPNTunnelEndpoint(
                source_interface=Interface(
                    name="Ethernet",
                    module=Module(),
                ),
            )
            with self.assertRaises(ValidationError):
                endpoint.clean()

        with self.subTest("Test source_ipaddress is assigned to source_interface"):
            endpoint = models.VPNTunnelEndpoint(
                source_interface=Interface.objects.filter(device__isnull=False).first(),
                source_ipaddress=IPAddress.objects.filter(interfaces__isnull=True).first(),
            )
            with self.assertRaises(ValidationError):
                endpoint.clean()

        with self.subTest("Test source_interface and tunnel_interface are assigned to the same device"):
            source_int = Interface.objects.filter(device__isnull=False).first()
            tunnel_int = Interface(
                name="Tunnel0",
                device=Device.objects.exclude(id=source_int.device.id).first(),
                status=source_int.status,
                type="tunnel",
            )
            endpoint = models.VPNTunnelEndpoint(
                device=source_int.device, source_interface=source_int, tunnel_interface=tunnel_int
            )
            with self.assertRaises(ValidationError):
                endpoint.clean()

    def test_name(self):
        """Test dynamic name property."""
        endpoint = models.VPNTunnelEndpoint.objects.filter(source_interface__isnull=False).first()
        ip = IPAddress.objects.filter(interface_assignments__isnull=True).last()
        ip.interfaces.add(endpoint.source_interface)
        endpoint.source_ipaddress = ip
        endpoint.save()

        with self.subTest("Test name contains interface name, device name and IP address"):
            self.assertIn(endpoint.source_interface.name, endpoint.name)
            self.assertIn(endpoint.source_interface.device.name, endpoint.name)
            self.assertIn(endpoint.source_ipaddress.host, endpoint.name)

        with self.subTest("Test name contains interface name and device name"):
            endpoint = models.VPNTunnelEndpoint.objects.filter(
                source_interface__isnull=False, source_ipaddress__isnull=True
            ).first()
            self.assertIn(endpoint.source_interface.name, endpoint.name)
            self.assertIn(endpoint.source_interface.device.name, endpoint.name)

        with self.subTest("Test name is fqdn"):
            endpoint = (
                models.VPNTunnelEndpoint.objects.filter(source_fqdn__isnull=False).exclude(source_fqdn="").first()
            )
            self.assertEqual(endpoint.source_fqdn, endpoint.name)

    def test_save(self):
        """Test save adds dynamic fields."""
        interface = Interface.objects.filter(vpn_tunnel_endpoints_src_int__isnull=True, device__isnull=False).first()
        new_endpoint = models.VPNTunnelEndpoint.objects.create(source_interface=interface)

        with self.subTest("Test device field is saved"):
            self.assertEqual(new_endpoint.device, interface.device)

        with self.subTest("Test name field is saved"):
            self.assertEqual(new_endpoint.name, new_endpoint._name())


class TestL2VPNModel(ModelTestCases.BaseModelTestCase):
    """Test L2VPN model."""

    model = models.L2VPN

    def test_get_docs_url(self):
        """L2VPN documentation not yet created."""
        self.skipTest("todo")

    @classmethod
    def _get_l2vpn_status(cls):
        """Get or create a Status for L2VPN model."""
        ct = ContentType.objects.get_for_model(models.L2VPN)
        status = Status.objects.filter(content_types=ct).first()
        if not status:
            status = Status.objects.get(name="Active")
            status.content_types.add(ct)
        return status

    @classmethod
    def _get_interfaces_without_terminations(cls):
        """Get interfaces that are not already assigned to an L2VPNTermination."""
        interface_ct = ContentType.objects.get_for_model(Interface)
        used_interface_ids = models.L2VPNTermination.objects.filter(
            assigned_object_type=interface_ct
        ).values_list("assigned_object_id", flat=True)
        return Interface.objects.exclude(pk__in=used_interface_ids).filter(device__isnull=False)

    @classmethod
    def setUpTestData(cls):
        """Set up test data for L2VPN model tests."""
        super().setUpTestData()
        status = cls._get_l2vpn_status()
        # Create test L2VPN objects for base model tests
        if not models.L2VPN.objects.exists():
            models.L2VPN.objects.create(
                name="Test L2VPN 1",
                type=choices.L2VPNTypeChoices.TYPE_VXLAN,
                status=status,
                identifier=10001,
                description="Test L2VPN for model tests",
            )
            models.L2VPN.objects.create(
                name="Test L2VPN 2",
                type=choices.L2VPNTypeChoices.TYPE_VPLS,
                status=status,
                description="Another test L2VPN",
            )

    def test_str_with_identifier(self):
        """Test __str__ method when identifier is set."""
        # Ex - with identifier 1001 it should be saved as 'Test L2VPN 1(10001)'
        l2vpn = models.L2VPN.objects.filter(identifier__isnull=False).first()
        if l2vpn:
            expected = f"{l2vpn.name} ({l2vpn.identifier})"
            self.assertEqual(str(l2vpn), expected)

    def test_str_without_identifier(self):
        """Test __str__ method when identifier is not set."""
        # Ex - without identifier, it should be saved as 'Test L2VPN 1'.
        l2vpn = models.L2VPN.objects.filter(identifier__isnull=True).first()
        if l2vpn:
            self.assertEqual(str(l2vpn), l2vpn.name)

    def test_can_add_termination_non_p2p(self):
        """Test can_add_termination returns True for non-P2P types."""
        # Non-P2P types can have unlimited terminations
        l2vpn = models.L2VPN.objects.filter(
            type=choices.L2VPNTypeChoices.TYPE_VXLAN
        ).first()
        if l2vpn:
            self.assertTrue(l2vpn.can_add_termination)

    def test_can_add_termination_p2p_under_limit(self):
        """Test can_add_termination for P2P type with less than 2 terminations."""
        # P2P types allow terminations when < 2
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="Test VPWS Under Limit",
            type=choices.L2VPNTypeChoices.TYPE_VPWS,
            status=status,
        )
        # No terminations yet
        self.assertTrue(l2vpn.can_add_termination)

    def test_can_add_termination_p2p_at_limit(self):
        """Test can_add_termination returns False for P2P type with 2 terminations."""
        # P2P types block terminations at 2
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="Test VPWS At Limit",
            type=choices.L2VPNTypeChoices.TYPE_VPWS,
            status=status,
        )
        # Get interfaces without existing terminations
        interfaces = self._get_interfaces_without_terminations()[:2]

        if interfaces.count() >= 2:
            models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=interfaces[0]
            )
            models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=interfaces[1]
            )
            self.assertFalse(l2vpn.can_add_termination)

    def test_name_unique_constraint(self):
        """Test that L2VPN name must be unique."""
        status = self._get_l2vpn_status()
        models.L2VPN.objects.create(
            name="I Swear This Name Is Unique",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
        )

        with self.assertRaises(IntegrityError):
            models.L2VPN.objects.create(
                name="I Swear This Name Is Unique",
                type=choices.L2VPNTypeChoices.TYPE_VXLAN,
                status=status,
            )

    def test_import_export_targets(self):
        """Test L2VPN import and export route targets relationship."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="L2VPN Route Targets Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN_EVPN,
            status=status,
        )

        route_targets = list(RouteTarget.objects.all()[:2])
        if len(route_targets) >= 2:
            l2vpn.import_targets.add(route_targets[0])
            l2vpn.export_targets.add(route_targets[1])

            self.assertEqual(l2vpn.import_targets.count(), 1)
            self.assertEqual(l2vpn.export_targets.count(), 1)
            self.assertIn(route_targets[0], l2vpn.import_targets.all())
            self.assertIn(route_targets[1], l2vpn.export_targets.all())

    def test_tenant_relationship(self):
        """Test L2VPN tenant relationship."""
        from nautobot.tenancy.models import Tenant

        status = self._get_l2vpn_status()
        tenant = Tenant.objects.first()

        if tenant:
            l2vpn = models.L2VPN.objects.create(
                name="L2VPN Tenant Test",
                type=choices.L2VPNTypeChoices.TYPE_VXLAN,
                status=status,
                tenant=tenant,
            )

            self.assertEqual(l2vpn.tenant, tenant)
            # Verify reverse relationship
            self.assertIn(l2vpn, tenant.l2vpns.all())

    def test_p2p_type_detection(self):
        """Test P2P type detection via can_add_termination."""
        status = self._get_l2vpn_status()

        # Test P2P type - can only have 2 terminations
        p2p_l2vpn = models.L2VPN.objects.create(
            name="Test P2P L2VPN Detection",
            type=choices.L2VPNTypeChoices.TYPE_VPWS,
            status=status,
        )
        # P2P type is in choices.L2VPNTypeChoices.P2P
        self.assertIn(p2p_l2vpn.type, choices.L2VPNTypeChoices.P2P)

        # Test non-P2P type
        non_p2p_l2vpn = models.L2VPN.objects.create(
            name="Test Non-P2P L2VPN Detection",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
        )
        self.assertNotIn(non_p2p_l2vpn.type, choices.L2VPNTypeChoices.P2P)

    def test_all_p2p_types_in_choices(self):
        """Test that P2P L2VPN types list is correctly defined."""
        # Verify expected P2P types are in the P2P tuple
        expected_p2p_types = [
            choices.L2VPNTypeChoices.TYPE_VPWS,
            choices.L2VPNTypeChoices.TYPE_EPL,
            choices.L2VPNTypeChoices.TYPE_EPLAN,
            choices.L2VPNTypeChoices.TYPE_EPTREE,
        ]

        for l2vpn_type in expected_p2p_types:
            with self.subTest(l2vpn_type=l2vpn_type):
                self.assertIn(l2vpn_type, choices.L2VPNTypeChoices.P2P, f"{l2vpn_type} should be P2P")

    def test_identifier_valid_vxlan_vni(self):
        """Test that a valid VNI is accepted for VXLAN types."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN(
            name="Valid VNI Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
            identifier=10000,
        )
        l2vpn.full_clean()  # Should not raise

    def test_identifier_vxlan_vni_too_high(self):
        """Test that a VNI above 16,777,214 is rejected for VXLAN types."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN(
            name="High VNI Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
            identifier=16777215,
        )
        with self.assertRaises(ValidationError) as cm:
            l2vpn.full_clean()
        self.assertIn("identifier", cm.exception.message_dict)

    def test_identifier_vxlan_vni_zero(self):
        """Test that VNI of 0 is rejected for VXLAN types."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN(
            name="Zero VNI Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN_EVPN,
            status=status,
            identifier=0,
        )
        with self.assertRaises(ValidationError) as cm:
            l2vpn.full_clean()
        self.assertIn("identifier", cm.exception.message_dict)

    def test_identifier_negative_rejected(self):
        """Test that a negative identifier is rejected for any type."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN(
            name="Negative ID Test",
            type=choices.L2VPNTypeChoices.TYPE_VPLS,
            status=status,
            identifier=-1,
        )
        with self.assertRaises(ValidationError) as cm:
            l2vpn.full_clean()
        self.assertIn("identifier", cm.exception.message_dict)

    def test_identifier_null_accepted(self):
        """Test that null identifier is accepted (it's optional)."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN(
            name="Null ID Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
            identifier=None,
        )
        l2vpn.full_clean()  # Should not raise

    def test_identifier_non_vxlan_type_allows_large_value(self):
        """Test that non-VXLAN types accept identifiers above 16,777,214."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN(
            name="Large VPLS ID Test",
            type=choices.L2VPNTypeChoices.TYPE_VPLS,
            status=status,
            identifier=99999999,
        )
        l2vpn.full_clean()  # Should not raise

    def test_identifier_vxlan_boundary_values(self):
        """Test VNI boundary values for VXLAN types."""
        status = self._get_l2vpn_status()
        # Min valid VNI (1)
        l2vpn_min = models.L2VPN(
            name="VNI Min Boundary Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
            identifier=1,
        )
        l2vpn_min.full_clean()  # Should not raise

        # Max valid VNI (16,777,214)
        l2vpn_max = models.L2VPN(
            name="VNI Max Boundary Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
            identifier=16777214,
        )
        l2vpn_max.full_clean()  # Should not raise


class TestL2VPNTerminationModel(ModelTestCases.BaseModelTestCase):
    """Test L2VPNTermination model."""

    model = models.L2VPNTermination

    def test_get_docs_url(self):
        """L2VPN Termination documentation not yet created."""
        self.skipTest("todo")

    @classmethod
    def _get_l2vpn_status(cls):
        """Get or create a Status for L2VPN model."""
        ct = ContentType.objects.get_for_model(models.L2VPN)
        status = Status.objects.filter(content_types=ct).first()
        if not status:
            status = Status.objects.get(name="Active")
            status.content_types.add(ct)
        return status

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
        """Set up test data for L2VPNTermination model tests."""
        super().setUpTestData()

        status = cls._get_l2vpn_status()

        # Create L2VPN and terminations for base model tests
        if not models.L2VPNTermination.objects.exists():
            l2vpn = models.L2VPN.objects.create(
                name="L2VPN For Termination Test",
                type=choices.L2VPNTypeChoices.TYPE_VXLAN,
                status=status,
            )

            interfaces = cls._get_interfaces_without_terminations()[:2]
            if interfaces.exists():
                for interface in interfaces:
                    models.L2VPNTermination.objects.create(
                        l2vpn=l2vpn,
                        assigned_object=interface
                    )
            else:
                # If no interfaces with devices exist, try VLANs
                vlans = cls._get_vlans_without_terminations()[:2]
                if vlans.exists():
                    for vlan in vlans:
                        models.L2VPNTermination.objects.create(
                            l2vpn=l2vpn,
                            assigned_object=vlan
                        )
                else:
                    # Create VLAN for termination if none exist
                    active_status = Status.objects.get(name="Active")
                    vlan_group = VLANGroup.objects.first()
                    if not vlan_group:
                        vlan_group = VLANGroup.objects.create(name="Test VLAN Group")

                    vlan = VLAN.objects.create(
                        vid=100,
                        name="Test VLAN for L2VPN",
                        status=active_status,
                        vlan_group=vlan_group,
                    )
                    models.L2VPNTermination.objects.create(
                        l2vpn=l2vpn,
                        assigned_object=vlan
                    )

    def test_str_with_assigned_object(self):
        """Test __str__ method when assigned_object exists."""
        termination = models.L2VPNTermination.objects.filter(
            assigned_object_id__isnull=False
        ).first()
        if termination and termination.assigned_object:
            expected = f"{termination.assigned_object} <> {termination.l2vpn}"
            self.assertEqual(str(termination), expected)

    def test_clean_duplicate_termination(self):
        """Test ValidationError when object already has a termination."""
        status = self._get_l2vpn_status()
        l2vpn1 = models.L2VPN.objects.create(
            name="L2VPN Dup Test 1",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
        )
        l2vpn2 = models.L2VPN.objects.create(
            name="L2VPN Dup Test 2",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
        )

        interface = self._get_interfaces_without_terminations().first()

        if interface:
            # Create first termination
            models.L2VPNTermination.objects.create(
                l2vpn=l2vpn1,
                assigned_object=interface
            )

            # Try to create second termination to same object
            termination2 = models.L2VPNTermination(
                l2vpn=l2vpn2,
                assigned_object=interface
            )

            with self.assertRaises(ValidationError) as cm:
                termination2.clean()

            self.assertIn("already assigned", str(cm.exception))

    def test_clean_p2p_limit_exceeded(self):
        """Test ValidationError when P2P L2VPN exceeds 2 terminations."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="L2VPN P2P Limit Test",
            type=choices.L2VPNTypeChoices.TYPE_VPWS,  # P2P type
            status=status,
        )

        interfaces = self._get_interfaces_without_terminations()[:3]

        if interfaces.count() >= 3:
            # Create 2 terminations
            models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=interfaces[0]
            )
            models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=interfaces[1]
            )

            # Try to create 3rd termination
            termination3 = models.L2VPNTermination(
                l2vpn=l2vpn,
                assigned_object=interfaces[2]
            )

            with self.assertRaises(ValidationError) as cm:
                termination3.clean()

            self.assertIn("cannot have more than 2 terminations", str(cm.exception))

    def test_clean_non_p2p_unlimited_terminations(self):
        """Test that non-P2P L2VPN can have more than 2 terminations."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="L2VPN Non-P2P Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,  # Non-P2P type
            status=status,
        )

        interfaces = self._get_interfaces_without_terminations()[:3]

        if interfaces.count() >= 3:
            # Create 3 terminations , should all succeed
            for interface in interfaces[:3]:
                termination = models.L2VPNTermination(
                    l2vpn=l2vpn,
                    assigned_object=interface
                )
                termination.clean()  # Should not raise
                termination.save()

            self.assertEqual(l2vpn.terminations.count(), 3)

    def test_termination_with_interface(self):
        """Test termination can be assigned to an Interface."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="L2VPN Interface Term Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
        )

        interface = self._get_interfaces_without_terminations().first()

        if interface:
            termination = models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=interface
            )
            self.assertEqual(termination.assigned_object, interface)

    def test_termination_with_vlan(self):
        """Test termination can be assigned to a VLAN."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="L2VPN VLAN Term Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
        )

        vlan = self._get_vlans_without_terminations().first()

        if vlan:
            termination = models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=vlan
            )
            self.assertEqual(termination.assigned_object, vlan)

    def test_termination_with_vminterface(self):
        """Test termination can be assigned to a VMInterface."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="L2VPN VMInterface Term Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
        )

        vminterface = self._get_vminterfaces_without_terminations().first()

        if vminterface:
            termination = models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=vminterface
            )
            self.assertEqual(termination.assigned_object, vminterface)

    def test_cascade_delete_on_l2vpn_delete(self):
        """Test that terminations are deleted when L2VPN is deleted."""
        status = self._get_l2vpn_status()
        l2vpn = models.L2VPN.objects.create(
            name="L2VPN Cascade Delete Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
        )

        interface = self._get_interfaces_without_terminations().first()

        if interface:
            termination = models.L2VPNTermination.objects.create(
                l2vpn=l2vpn,
                assigned_object=interface
            )
            termination_pk = termination.pk

            l2vpn.delete()

            self.assertFalse(
                models.L2VPNTermination.objects.filter(pk=termination_pk).exists()
            )

