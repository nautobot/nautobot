"""Test nautobot_vpn_models models."""

from nautobot.apps.testing import ModelTestCases

from nautobot_vpn_models import models












class TestVPNProfileModel(ModelTestCases.BaseModelTestCase):
    """Test VPNProfile model."""

    model = models.VPNProfile

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # Add test data here

        # Attempt to create the foreign key relationship models



class TestVPNPhase1PolicyModel(ModelTestCases.BaseModelTestCase):
    """Test VPNPhase1Policy model."""

    model = models.VPNPhase1Policy

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # Add test data here

        # Attempt to create the foreign key relationship models



class TestVPNPhase2PolicyModel(ModelTestCases.BaseModelTestCase):
    """Test VPNPhase2Policy model."""

    model = models.VPNPhase2Policy

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # Add test data here

        # Attempt to create the foreign key relationship models



class TestVPNModel(ModelTestCases.BaseModelTestCase):
    """Test VPN model."""

    model = models.VPN

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # Add test data here

        # Attempt to create the foreign key relationship models



class TestVPNTunnelModel(ModelTestCases.BaseModelTestCase):
    """Test VPNTunnel model."""

    model = models.VPNTunnel

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # Add test data here

        # Attempt to create the foreign key relationship models



class TestVPNTunnelEndpointModel(ModelTestCases.BaseModelTestCase):
    """Test VPNTunnelEndpoint model."""

    model = models.VPNTunnelEndpoint

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # Add test data here

        # Attempt to create the foreign key relationship models


