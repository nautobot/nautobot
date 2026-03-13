"""Test vpn forms."""

from django.contrib.contenttypes.models import ContentType

from nautobot.apps.testing import FormTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import DynamicGroup, Role, SecretsGroup, Status
from nautobot.ipam.models import Prefix, RouteTarget, VLAN
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import VMInterface
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


class L2VPNFormTest(FormTestCases.BaseFormTestCase):
    """Test the L2VPN form."""

    form_class = forms.L2VPNForm

    @classmethod
    def _get_l2vpn_status(cls):
        """Get or create a Status for L2VPN model."""
        ct = ContentType.objects.get_for_model(models.L2VPN)
        status = Status.objects.filter(content_types=ct).first()
        if not status:
            status = Status.objects.get(name="Active")
            status.content_types.add(ct)
        return status

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""
        data = {
            "name": "Test L2VPN Full",
            "type": choices.L2VPNTypeChoices.TYPE_VXLAN,
            "status": self._get_l2vpn_status(),
            "identifier": 10001,
            "description": "Test L2VPN description",
            "tenant": Tenant.objects.first(),
            "import_targets": RouteTarget.objects.all()[:1],
            "export_targets": RouteTarget.objects.all()[:1],
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""
        data = {
            "name": "Test L2VPN Required Only",
            "type": choices.L2VPNTypeChoices.TYPE_VXLAN,
            "status": self._get_l2vpn_status(),
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertIsNotNone(instance)
        # Verify slug is auto-generated
        self.assertEqual(instance.slug, "test-l2vpn-required-only")

    def test_validate_name_is_required(self):
        """Test that the name field is required."""
        data = {
            "type": choices.L2VPNTypeChoices.TYPE_VXLAN,
            "status": self._get_l2vpn_status(),
            "description": "Test without name",
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_validate_type_is_required(self):
        """Test that the type field is required."""
        data = {
            "name": "Test L2VPN No Type",
            "status": self._get_l2vpn_status(),
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("type", form.errors)

    def test_validate_status_is_required(self):
        """Test that the status field is required."""
        data = {
            "name": "Test L2VPN No Status",
            "type": choices.L2VPNTypeChoices.TYPE_VXLAN,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)

    def test_all_l2vpn_types(self):
        """Test that all L2VPN type choices are valid."""
        status = self._get_l2vpn_status()

        for type_value, type_label in [
            (choices.L2VPNTypeChoices.TYPE_VXLAN, "VXLAN"),
            (choices.L2VPNTypeChoices.TYPE_VPLS, "VPLS"),
            (choices.L2VPNTypeChoices.TYPE_VPWS, "VPWS"),
            (choices.L2VPNTypeChoices.TYPE_EPL, "EPL"),
            (choices.L2VPNTypeChoices.TYPE_EVPL, "EVPL"),
            (choices.L2VPNTypeChoices.TYPE_VXLAN_EVPN, "VXLAN-EVPN"),
        ]:
            with self.subTest(type_value=type_value):
                data = {
                    "name": f"Test L2VPN {type_label}",
                    "type": type_value,
                    "status": status,
                }
                form = self.form_class(data=data)
                self.assertTrue(form.is_valid(), f"Form should be valid for type {type_value}")

    def test_identifier_optional(self):
        """Test that identifier is optional."""
        data = {
            "name": "Test L2VPN No Identifier",
            "type": choices.L2VPNTypeChoices.TYPE_VXLAN,
            "status": self._get_l2vpn_status(),
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertIsNone(instance.identifier)


class L2VPNTerminationFormTest(FormTestCases.BaseFormTestCase):
    """Test the L2VPNTermination form."""

    form_class = forms.L2VPNTerminationForm

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

    def test_termination_with_interface(self):
        """Test creating termination with interface."""
        l2vpn = models.L2VPN.objects.first()
        interface = self._get_interfaces_without_terminations().first()

        if l2vpn and interface:
            data = {
                "l2vpn": l2vpn.pk,
                "interface": interface.pk,
            }
            form = self.form_class(data=data)
            self.assertTrue(form.is_valid(), form.errors)
            instance = form.save()
            self.assertEqual(instance.assigned_object, interface)

    def test_termination_with_vlan(self):
        """Test creating termination with VLAN."""
        l2vpn = models.L2VPN.objects.first()
        vlan = self._get_vlans_without_terminations().first()

        if l2vpn and vlan:
            data = {
                "l2vpn": l2vpn.pk,
                "vlan": vlan.pk,
            }
            form = self.form_class(data=data)
            self.assertTrue(form.is_valid(), form.errors)
            instance = form.save()
            self.assertEqual(instance.assigned_object, vlan)

    def test_termination_with_vminterface(self):
        """Test creating termination with VM interface."""
        l2vpn = models.L2VPN.objects.first()
        vminterface = self._get_vminterfaces_without_terminations().first()

        if l2vpn and vminterface:
            data = {
                "l2vpn": l2vpn.pk,
                "vminterface": vminterface.pk,
            }
            form = self.form_class(data=data)
            self.assertTrue(form.is_valid(), form.errors)
            instance = form.save()
            self.assertEqual(instance.assigned_object, vminterface)

    def test_validation_no_termination_object(self):
        """Test validation fails when no termination object is selected."""
        l2vpn = models.L2VPN.objects.first()

        if l2vpn:
            data = {
                "l2vpn": l2vpn.pk,
                # No interface, vlan, or vminterface
            }
            form = self.form_class(data=data)
            self.assertFalse(form.is_valid())
            self.assertIn("Must specify an interface or VLAN", str(form.errors))

    def test_validation_multiple_objects_selected(self):
        """Test validation fails when multiple termination objects are selected."""
        l2vpn = models.L2VPN.objects.first()
        interface = self._get_interfaces_without_terminations().first()
        vlan = self._get_vlans_without_terminations().first()

        if l2vpn and interface and vlan:
            data = {
                "l2vpn": l2vpn.pk,
                "interface": interface.pk,
                "vlan": vlan.pk,
            }
            form = self.form_class(data=data)
            self.assertFalse(form.is_valid())
            self.assertIn("Can only have one terminating object", str(form.errors))

    def test_validation_interface_and_vminterface_selected(self):
        """Test validation fails when interface and vminterface are both selected."""
        l2vpn = models.L2VPN.objects.first()
        interface = self._get_interfaces_without_terminations().first()
        vminterface = self._get_vminterfaces_without_terminations().first()

        if l2vpn and interface and vminterface:
            data = {
                "l2vpn": l2vpn.pk,
                "interface": interface.pk,
                "vminterface": vminterface.pk,
            }
            form = self.form_class(data=data)
            self.assertFalse(form.is_valid())
            self.assertIn("Can only have one terminating object", str(form.errors))

    def test_l2vpn_required(self):
        """Test that L2VPN field is required."""
        interface = self._get_interfaces_without_terminations().first()

        if interface:
            data = {
                "interface": interface.pk,
                # No l2vpn
            }
            form = self.form_class(data=data)
            self.assertFalse(form.is_valid())
            self.assertIn("l2vpn", form.errors)


