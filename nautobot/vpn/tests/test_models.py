"""Test vpn models."""

from django.core.exceptions import ValidationError

from nautobot.apps.testing import ModelTestCases
from nautobot.dcim.models import Interface
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

    def test_composite_key(self):
        """Model doesn't support this property."""

    def test_natural_key_symmetry(self):
        """Model doesn't support this property."""

    def test_name(self):
        """Test dynamic name property."""
        with self.subTest("Test name contains interface name and device name."):
            endpoint = models.VPNTunnelEndpoint.objects.filter(source_interface__isnull=False).first()
            self.assertIn(endpoint.source_interface.name, endpoint.name)
            self.assertIn(endpoint.source_interface.device.name, endpoint.name)

        with self.subTest("Test name contains interface name, device name and IP address."):
            endpoint = models.VPNTunnelEndpoint.objects.filter(
                source_interface__isnull=False, source_ipaddress__isnull=False
            ).first()
            self.assertIn(endpoint.source_interface.name, endpoint.name)
            self.assertIn(endpoint.source_interface.device.name, endpoint.name)
            self.assertIn(endpoint.source_ipaddress.host, endpoint.name)

        with self.subTest("Test name is fqdn"):
            endpoint = (
                models.VPNTunnelEndpoint.objects.filter(source_fqdn__isnull=False).exclude(source_fqdn="").first()
            )
            self.assertEqual(endpoint.source_fqdn, endpoint.name)

    def test_save(self):
        """Test save adds device field when only interface is given on create."""
        interface = Interface.objects.filter(vpn_tunnel_endpoints_src_int__isnull=True).first()
        new_endpoint = models.VPNTunnelEndpoint.objects.create(source_interface=interface)
        self.assertEqual(new_endpoint.device, interface.device)
