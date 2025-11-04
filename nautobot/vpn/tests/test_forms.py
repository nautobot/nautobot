"""Test vpn forms."""

from django.contrib.contenttypes.models import ContentType

from nautobot.apps.testing import FormTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import DynamicGroup, Role, SecretsGroup, Status
from nautobot.ipam.models import Prefix
from nautobot.tenancy.models import Tenant
from nautobot.vpn import choices, forms, models


class VPNProfileFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNProfile form."""

    form_class = forms.VPNProfileForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""
        profile_role, _ = Role.objects.get_or_create(name="Default")
        profile_role.content_types.add(ContentType.objects.get_for_model(models.VPNProfile))

        data = {
            "name": "test 1",
            "description": "test value",
            "role": profile_role,
            "secrets_group": SecretsGroup.objects.first(),
            "keepalive_enabled": True,
            "keepalive_interval": 3,
            "keepalive_retries": 5,
            "nat_traversal": False,
            "extra_options": {"option": "value"},
            "tenant": Tenant.objects.first(),
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
            "keepalive_enabled": True,
            "keepalive_interval": 3,
            "keepalive_retries": 5,
            "nat_traversal": False,
            "extra_options": None,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])


class VPNPhase1PolicyFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNPhase1Policy form."""

    form_class = forms.VPNPhase1PolicyForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "name": "test 1",
            "description": "test value",
            "ike_version": choices.IkeVersionChoices.ike_v2,
            "aggressive_mode": False,
            "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_128_cbc],
            "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha1],
            "dh_group": [choices.DhGroupChoices.group5],
            "lifetime_seconds": 10,
            "lifetime_kb": 1024,
            "authentication_method": choices.AuthenticationMethodChoices.rsa,
            "tenant": Tenant.objects.first(),
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
            "ike_version": choices.IkeVersionChoices.ike_v2,
            "aggressive_mode": False,
            "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_128_cbc],
            "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha1],
            "dh_group": [choices.DhGroupChoices.group5],
            "lifetime_seconds": 10,
            "lifetime_kb": 1024,
            "authentication_method": choices.AuthenticationMethodChoices.rsa,
            "tenant": Tenant.objects.first(),
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])


class VPNPhase2PolicyFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNPhase2Policy form."""

    form_class = forms.VPNPhase2PolicyForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "name": "test 1",
            "description": "test value",
            "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_128_cbc],
            "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha1],
            "pfs_group": [choices.DhGroupChoices.group5],
            "lifetime": 10,
            "tenant": Tenant.objects.first(),
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
            "encryption_algorithm": [choices.EncryptionAlgorithmChoices.aes_128_cbc],
            "integrity_algorithm": [choices.IntegrityAlgorithmChoices.sha1],
            "pfs_group": [choices.DhGroupChoices.group5],
            "lifetime": 10,
            "tenant": Tenant.objects.first(),
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])


class VPNFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPN form."""

    form_class = forms.VPNForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""
        vpn_role, _ = Role.objects.get_or_create(name="Default")
        vpn_role.content_types.add(ContentType.objects.get_for_model(models.VPN))

        data = {
            "name": "test 1",
            "description": "test value",
            "vpn_id": "test value",
            "role": vpn_role,
            "vpn_profile": models.VPNProfile.objects.first(),
            "tenant": Tenant.objects.first(),
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
            "vpn_id": "test value",
            "vpn_profile": models.VPNProfile.objects.first(),
            "tenant": Tenant.objects.first(),
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])


class VPNTunnelFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNTunnel form."""

    form_class = forms.VPNTunnelForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""
        endpoints = models.VPNTunnelEndpoint.objects.all()
        tunnel_role, _ = Role.objects.get_or_create(name="Default")
        tunnel_role.content_types.add(ContentType.objects.get_for_model(models.VPNTunnel))
        data = {
            "name": "test 1",
            "description": "test value",
            "vpn_profile": models.VPNProfile.objects.first(),
            "vpn": models.VPN.objects.first(),
            "tunnel_id": "test value",
            "status": Status.objects.get(name="Active"),
            "role": tunnel_role,
            "encapsulation": choices.EncapsulationChoices.ipsec_tunnel,
            "endpoint_a": endpoints[1],
            "endpoint_z": endpoints[2],
            "tenant": Tenant.objects.first(),
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {
            "name": "test value",
            "status": Status.objects.get(name="Active"),
            "encapsulation": choices.EncapsulationChoices.ipsec_tunnel,
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_validate_name_is_required(self):
        """Test that the name field is required."""

        data = {
            "description": "test value",
            "vpn_profile": models.VPNProfile.objects.first(),
            "vpn": models.VPN.objects.first(),
            "tunnel_id": "test value",
            "status": Status.objects.get(name="Active"),
            "encapsulation": choices.EncapsulationChoices.ipsec_tunnel,
            "tenant": Tenant.objects.first(),
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])


class VPNTunnelEndpointFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNTunnelEndpoint form."""

    form_class = forms.VPNTunnelEndpointForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""
        interfaces = Interface.objects.filter(device__isnull=False, vpn_tunnel_endpoints_src_int__isnull=True)
        data = {
            "source_interface": interfaces[0],
            "vpn_profile": models.VPNProfile.objects.first(),
            "protected_prefixes": [Prefix.objects.first()],
            "protected_prefixes_dg": [DynamicGroup.objects.first()],
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {"source_fqdn": "cloud.com"}
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
