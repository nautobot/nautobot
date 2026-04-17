"""Test vpn models."""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from nautobot.apps.testing import ModelTestCases
from nautobot.dcim.models import Device, Interface, Module
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.vpn import choices, models
from nautobot.vpn.factory import get_status_for_model
from nautobot.vpn.tests import VPNTerminationFixtureMixin


class TestVPNProfileModel(ModelTestCases.BaseModelTestCase):
    """Test VPNProfile model."""

    model = models.VPNProfile


class TestVPNPhase1PolicyModel(ModelTestCases.BaseModelTestCase):
    """Test VPNPhase1Policy model."""

    model = models.VPNPhase1Policy


class TestVPNPhase2PolicyModel(ModelTestCases.BaseModelTestCase):
    """Test VPNPhase2Policy model."""

    model = models.VPNPhase2Policy


class TestVPNProfilePhase1PolicyAssignmentModel(ModelTestCases.BaseModelTestCase):
    """Test VPNProfilePhase1PolicyAssignment model."""

    model = models.VPNProfilePhase1PolicyAssignment


class TestVPNProfilePhase2PolicyAssignmentModel(ModelTestCases.BaseModelTestCase):
    """Test VPNProfilePhase2PolicyAssignment model."""

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

    def test_clean_rejects_tunnel_when_vpn_has_terminations(self):
        """Test that a VPN with terminations cannot have tunnels."""
        ct = ContentType.objects.get_for_model(models.VPN)
        vpn_status = Status.objects.filter(content_types=ct).first()
        if not vpn_status:
            vpn_status = Status.objects.get(name="Active")
            vpn_status.content_types.add(ct)
        tunnel_status = Status.objects.get_for_model(models.VPNTunnel).first()

        vpn = models.VPN.objects.create(
            name="Termination-Only VPN",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=vpn_status,
            vpn_id="99999",
        )
        vlan = VLAN.objects.exclude(
            pk__in=models.VPNTermination.objects.exclude(vlan__isnull=True).values_list("vlan_id", flat=True)
        ).first()
        models.VPNTermination.objects.create(vpn=vpn, vlan=vlan)

        tunnel = models.VPNTunnel(name="Should Fail Tunnel", vpn=vpn, status=tunnel_status)
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


class VPNOverlayModelTestCase(VPNTerminationFixtureMixin, TestCase):
    """Behavioral tests for overlay-related VPN fields."""

    @classmethod
    def setUpTestData(cls):
        cls.status = get_status_for_model(models.VPN)

    def test_can_add_termination_non_p2p(self):
        vpn = models.VPN.objects.create(
            name="VXLAN Service",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            vpn_id="10001",
        )
        self.assertTrue(vpn.can_add_termination)

    def test_can_add_termination_p2p_under_limit(self):
        vpn = models.VPN.objects.create(
            name="VPWS Service",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPWS,
            status=self.status,
        )
        self.assertTrue(vpn.can_add_termination)

    def test_can_add_termination_p2p_at_limit(self):
        vpn = models.VPN.objects.create(
            name="VPWS Limited Service",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPWS,
            status=self.status,
        )
        interfaces = self._ensure_available_interfaces(2)
        models.VPNTermination.objects.create(vpn=vpn, interface=interfaces[0])
        models.VPNTermination.objects.create(vpn=vpn, interface=interfaces[1])
        self.assertFalse(vpn.can_add_termination)

    def test_can_add_termination_eplan_not_limited_to_two(self):
        vpn = models.VPN.objects.create(
            name="EPLAN Service",
            service_type=choices.VPNServiceTypeChoices.TYPE_EPLAN,
            status=self.status,
        )
        vlans = self._ensure_available_vlans(3)
        models.VPNTermination.objects.create(vpn=vpn, vlan=vlans[0])
        models.VPNTermination.objects.create(vpn=vpn, vlan=vlans[1])
        self.assertTrue(vpn.can_add_termination)

        termination = models.VPNTermination(vpn=vpn, vlan=vlans[2])
        termination.clean()

    def test_can_add_termination_evpn_vpws_at_limit(self):
        vpn = models.VPN.objects.create(
            name="EVPN VPWS Service",
            service_type=choices.VPNServiceTypeChoices.TYPE_EVPN_VPWS,
            status=self.status,
        )
        interfaces = self._ensure_available_interfaces(2)
        models.VPNTermination.objects.create(vpn=vpn, interface=interfaces[0])
        models.VPNTermination.objects.create(vpn=vpn, interface=interfaces[1])
        self.assertFalse(vpn.can_add_termination)

    def test_vpn_id_valid_vxlan_vni(self):
        vpn = models.VPN(
            name="Valid VNI Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            vpn_id="10000",
        )
        vpn.full_clean()

    def test_vpn_id_required_for_vxlan_service(self):
        vpn = models.VPN(
            name="Missing VNI Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
        )
        with self.assertRaises(ValidationError) as context:
            vpn.full_clean()
        self.assertIn("vpn_id", context.exception.message_dict)

    def test_vpn_id_vxlan_vni_too_high(self):
        vpn = models.VPN(
            name="High VNI Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            vpn_id="16777215",
        )
        with self.assertRaises(ValidationError) as context:
            vpn.full_clean()
        self.assertIn("vpn_id", context.exception.message_dict)

    def test_vpn_id_vxlan_boundary_values(self):
        for vpn_id in (
            choices.VPNServiceTypeChoices.VXLAN_VNI_MIN,
            choices.VPNServiceTypeChoices.VXLAN_VNI_MAX,
        ):
            with self.subTest(vpn_id=vpn_id):
                vpn = models.VPN(
                    name=f"Boundary VNI {vpn_id}",
                    service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
                    status=self.status,
                    vpn_id=str(vpn_id),
                )
                vpn.full_clean()

    def test_vpn_id_negative_rejected(self):
        vpn = models.VPN(
            name="Negative ID Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            vpn_id="-1",
        )
        with self.assertRaises(ValidationError) as context:
            vpn.full_clean()
        self.assertIn("vpn_id", context.exception.message_dict)

    def test_vpn_id_non_vxlan_type_allows_large_value(self):
        vpn = models.VPN(
            name="Large VPLS ID Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPLS,
            status=self.status,
            vpn_id="99999999",
        )
        vpn.full_clean()

    def test_tenant_relationship(self):
        tenant = self._ensure_tenant()
        vpn = models.VPN.objects.create(
            name="VPN Tenant Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            vpn_id="11000",
            tenant=tenant,
        )
        self.assertEqual(vpn.tenant, tenant)
        self.assertIn(vpn, tenant.vpns.all())


class VPNTerminationModelTestCase(VPNTerminationFixtureMixin, ModelTestCases.BaseModelTestCase):
    """Behavioral tests for VPNTermination."""

    model = models.VPNTermination

    @classmethod
    def setUpTestData(cls):
        cls.status = get_status_for_model(models.VPN)
        cls.vpn = models.VPN.objects.create(
            name="VPN For Termination Tests",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=cls.status,
            vpn_id="12000",
        )
        cls.seed_termination = models.VPNTermination.objects.create(vpn=cls.vpn, vlan=cls._ensure_available_vlans(1)[0])

    def test_str_returns_computed_name(self):
        """Test __str__ returns the computed name from _name()."""
        vlan = self._ensure_available_vlans(1)[0]
        termination = models.VPNTermination.objects.create(vpn=self.vpn, vlan=vlan)
        self.assertEqual(str(termination), termination.name)
        self.assertEqual(termination.name, termination._name())

    def test_name_computed_on_save(self):
        """Test name field is correctly computed for each attachment type."""
        with self.subTest("Interface termination name includes device and interface"):
            interface = self._ensure_available_interfaces(1)[0]
            termination = models.VPNTermination.objects.create(vpn=self.vpn, interface=interface)
            self.assertEqual(termination.name, f"{interface.device.name} {interface.name}")

        with self.subTest("VLAN termination name includes VLAN group and VLAN"):
            vlan = self._ensure_available_vlans(1)[0]
            termination = models.VPNTermination.objects.create(vpn=self.vpn, vlan=vlan)
            if vlan.vlan_group:
                self.assertEqual(termination.name, f"{vlan.vlan_group.name} {vlan.name}")
            else:
                self.assertEqual(termination.name, vlan.name)

        with self.subTest("VM interface termination name includes VM and interface"):
            vm_interface = self._ensure_available_vm_interfaces(1)[0]
            termination = models.VPNTermination.objects.create(vpn=self.vpn, vm_interface=vm_interface)
            self.assertEqual(termination.name, f"{vm_interface.virtual_machine.name} {vm_interface.name}")

    def test_clean_requires_exactly_one_object(self):
        termination = models.VPNTermination(vpn=self.vpn)
        with self.assertRaises(ValidationError):
            termination.clean()

    def test_clean_rejects_multiple_objects(self):
        vlan = self._ensure_available_vlans(1)[0]
        interface = self._ensure_available_interfaces(1)[0]
        termination = models.VPNTermination(vpn=self.vpn, vlan=vlan, interface=interface)
        with self.assertRaises(ValidationError):
            termination.clean()

    def test_clean_p2p_limit_exceeded(self):
        vpn = models.VPN.objects.create(
            name="P2P Termination Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPWS,
            status=self.status,
        )
        interfaces = self._ensure_available_interfaces(3)
        models.VPNTermination.objects.create(vpn=vpn, interface=interfaces[0])
        models.VPNTermination.objects.create(vpn=vpn, interface=interfaces[1])

        termination = models.VPNTermination(vpn=vpn, interface=interfaces[2])
        with self.assertRaises(ValidationError):
            termination.clean()

    def test_clean_rejects_termination_when_vpn_has_tunnels(self):
        """Test that a VPN with tunnels cannot have terminations."""
        tunnel_status = get_status_for_model(models.VPNTunnel)
        vpn = models.VPN.objects.create(
            name="Tunnel-Only VPN",
            status=self.status,
        )
        models.VPNTunnel.objects.create(name="Test Tunnel", vpn=vpn, status=tunnel_status)
        interface = self._ensure_available_interfaces(1)[0]
        termination = models.VPNTermination(vpn=vpn, interface=interface)
        with self.assertRaises(ValidationError):
            termination.clean()

    def test_duplicate_termination_rejected_by_validation(self):
        interface = self._ensure_available_interfaces(1)[0]
        models.VPNTermination.objects.create(vpn=self.vpn, interface=interface)
        with self.assertRaises(ValidationError):
            models.VPNTermination(vpn=self.vpn, interface=interface).validated_save()

    def test_termination_with_interface(self):
        interface = self._ensure_available_interfaces(1)[0]
        termination = models.VPNTermination.objects.create(vpn=self.vpn, interface=interface)
        self.assertEqual(termination.assigned_object, interface)
        self.assertEqual(termination.assigned_object_type, "dcim.interface")
        self.assertEqual(termination.assigned_object_parent, interface.device)

    def test_termination_with_vlan(self):
        vlan = self._ensure_available_vlans(1)[0]
        termination = models.VPNTermination.objects.create(vpn=self.vpn, vlan=vlan)
        self.assertEqual(termination.assigned_object, vlan)
        self.assertEqual(termination.assigned_object_type, "ipam.vlan")

    def test_termination_with_vm_interface(self):
        vm_interface = self._ensure_available_vm_interfaces(1)[0]
        termination = models.VPNTermination.objects.create(vpn=self.vpn, vm_interface=vm_interface)
        self.assertEqual(termination.assigned_object, vm_interface)
        self.assertEqual(termination.assigned_object_type, "virtualization.vminterface")

    def test_cascade_delete_on_vpn_delete(self):
        interface = self._ensure_available_interfaces(1)[0]
        vpn = models.VPN.objects.create(
            name="Cascade Delete Termination Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            vpn_id="13000",
        )
        termination = models.VPNTermination.objects.create(vpn=vpn, interface=interface)
        termination_pk = termination.pk

        vpn.delete()
        self.assertFalse(models.VPNTermination.objects.filter(pk=termination_pk).exists())
