"""Test vpn models."""

from django.core.exceptions import ValidationError

from nautobot.apps.testing import ModelTestCases
from nautobot.dcim.models import Device, Interface, Module
from nautobot.ipam.models import IPAddress
from nautobot.vpn import models


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
