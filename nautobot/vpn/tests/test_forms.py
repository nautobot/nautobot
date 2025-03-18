"""Test nautobot_vpn_models forms."""

from nautobot.apps.testing import FormTestCases

from nautobot_vpn_models import choices, forms











class VPNProfileFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNProfile form."""

    form_class = forms.VPNProfileForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "vpn_phase1_policy": "test value",
            "vpn_phase2_policy": "test value",
            "name": "test value",
            "description": "test value",
            "keepalive_enabled": "test value",
            "keepalive_interval": "test value",
            "keepalive_retries": "test value",
            "nat_traversal": "test value",
            "extra_options": "test value",
            "secrets_group": "test value",
            "role": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {
            "name": "test value",
            "keepalive_enabled": "test value",
            "nat_traversal": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
    def test_validate_name_is_required(self):
        """Test that the name field is required."""

        data = {
            "vpn_phase1_policy": "test value",
            "vpn_phase2_policy": "test value",
            "description": "test value",
            "keepalive_enabled": "test value",
            "keepalive_interval": "test value",
            "keepalive_retries": "test value",
            "nat_traversal": "test value",
            "extra_options": "test value",
            "secrets_group": "test value",
            "role": "test value",
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])
    def test_validate_keepalive_enabled_is_required(self):
        """Test that the keepalive_enabled field is required."""

        data = {
            "vpn_phase1_policy": "test value",
            "vpn_phase2_policy": "test value",
            "name": "test value",
            "description": "test value",
            "keepalive_interval": "test value",
            "keepalive_retries": "test value",
            "nat_traversal": "test value",
            "extra_options": "test value",
            "secrets_group": "test value",
            "role": "test value",
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["keepalive_enabled"])
    def test_validate_nat_traversal_is_required(self):
        """Test that the nat_traversal field is required."""

        data = {
            "vpn_phase1_policy": "test value",
            "vpn_phase2_policy": "test value",
            "name": "test value",
            "description": "test value",
            "keepalive_enabled": "test value",
            "keepalive_interval": "test value",
            "keepalive_retries": "test value",
            "extra_options": "test value",
            "secrets_group": "test value",
            "role": "test value",
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["nat_traversal"])

class VPNPhase1PolicyFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNPhase1Policy form."""

    form_class = forms.VPNPhase1PolicyForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "name": "test value",
            "description": "test value",
            "ike_version": "test value",
            "aggressive_mode": "test value",
            "encryption_algorithm": "test value",
            "integrity_algorithm": "test value",
            "dh_group": "test value",
            "lifetime_seconds": "test value",
            "lifetime_kb": "test value",
            "authentication_method": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {
            "name": "test value",
            "aggressive_mode": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
    def test_validate_name_is_required(self):
        """Test that the name field is required."""

        data = {
            "description": "test value",
            "ike_version": "test value",
            "aggressive_mode": "test value",
            "encryption_algorithm": "test value",
            "integrity_algorithm": "test value",
            "dh_group": "test value",
            "lifetime_seconds": "test value",
            "lifetime_kb": "test value",
            "authentication_method": "test value",
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])
    def test_validate_aggressive_mode_is_required(self):
        """Test that the aggressive_mode field is required."""

        data = {
            "name": "test value",
            "description": "test value",
            "ike_version": "test value",
            "encryption_algorithm": "test value",
            "integrity_algorithm": "test value",
            "dh_group": "test value",
            "lifetime_seconds": "test value",
            "lifetime_kb": "test value",
            "authentication_method": "test value",
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["aggressive_mode"])

class VPNPhase2PolicyFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNPhase2Policy form."""

    form_class = forms.VPNPhase2PolicyForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "name": "test value",
            "description": "test value",
            "encryption_algorithm": "test value",
            "integrity_algorithm": "test value",
            "pfs_group": "test value",
            "lifetime": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {
            "name": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
    def test_validate_name_is_required(self):
        """Test that the name field is required."""

        data = {
            "description": "test value",
            "encryption_algorithm": "test value",
            "integrity_algorithm": "test value",
            "pfs_group": "test value",
            "lifetime": "test value",
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])

class VPNFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPN form."""

    form_class = forms.VPNForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "vpn_profile": "test value",
            "name": "test value",
            "description": "test value",
            "vpn_id": "test value",
            "tenant": "test value",
            "role": "test value",
            "contact_associations": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {
            "name": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
    def test_validate_name_is_required(self):
        """Test that the name field is required."""

        data = {
            "vpn_profile": "test value",
            "description": "test value",
            "vpn_id": "test value",
            "tenant": "test value",
            "role": "test value",
            "contact_associations": "test value",
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])

class VPNTunnelFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNTunnel form."""

    form_class = forms.VPNTunnelForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "vpn_profile": "test value",
            "vpn": "test value",
            "name": "test value",
            "description": "test value",
            "tunnel_id": "test value",
            "encapsulation": "test value",
            "tenant": "test value",
            "role": "test value",
            "contact_associations": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {
            "name": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
    def test_validate_name_is_required(self):
        """Test that the name field is required."""

        data = {
            "vpn_profile": "test value",
            "vpn": "test value",
            "description": "test value",
            "tunnel_id": "test value",
            "encapsulation": "test value",
            "tenant": "test value",
            "role": "test value",
            "contact_associations": "test value",
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])

class VPNTunnelEndpointFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNTunnelEndpoint form."""

    form_class = forms.VPNTunnelEndpointForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "vpn_profile": "test value",
            "vpn_tunnel": "test value",
            "source_ipaddress": "test value",
            "source_interface": "test value",
            "destination_ipaddress": "test value",
            "destination_fqdn": "test value",
            "tunnel_interface": "test value",
            "protected_prefixes_dg": "test value",
            "protected_prefixes": "test value",
            "role": "test value",
            "contact_associations": "test value",
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
