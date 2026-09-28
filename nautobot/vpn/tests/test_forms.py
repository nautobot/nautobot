"""Test vpn forms."""

from django.contrib.contenttypes.models import ContentType

from nautobot.apps.testing import FormTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import DynamicGroup, Role, SecretsGroup, Status
from nautobot.ipam.models import Prefix, VLAN
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface
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

    @classmethod
    def _get_vpn_status(cls):
        """Get or create an Active status for VPN."""
        ct = ContentType.objects.get_for_model(models.VPN)
        status = Status.objects.filter(content_types=ct).first()
        if not status:
            status = Status.objects.get(name="Active")
            status.content_types.add(ct)
        return status

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""
        vpn_role, _ = Role.objects.get_or_create(name="Default")
        vpn_role.content_types.add(ContentType.objects.get_for_model(models.VPN))

        data = {
            "name": "test 1",
            "description": "test value",
            "vpn_id": "10001",
            "role": vpn_role,
            "vpn_profile": models.VPNProfile.objects.first().pk,
            "service_type": choices.VPNServiceTypeChoices.TYPE_VXLAN,
            "status": self._get_vpn_status().pk,
            "tenant": Tenant.objects.first().pk,
            "extra_attributes": '{"flooding_mode": "ingress-replication"}',
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
            "vpn_profile": models.VPNProfile.objects.first().pk,
            "tenant": Tenant.objects.first().pk,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])

    def test_vxlan_service_type_requires_vpn_id(self):
        """VXLAN services should require a numeric VPN ID/VNI."""
        data = {
            "name": "VXLAN Without Identifier",
            "service_type": choices.VPNServiceTypeChoices.TYPE_VXLAN,
            "status": self._get_vpn_status().pk,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("vpn_id", form.errors)


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


class VPNTerminationFormTest(FormTestCases.BaseFormTestCase):
    """Test the VPNTermination form."""

    form_class = forms.VPNTerminationForm

    @classmethod
    def _get_available_interfaces(cls):
        used_interface_ids = models.VPNTermination.objects.exclude(interface__isnull=True).values_list(
            "interface_id", flat=True
        )
        return Interface.objects.exclude(pk__in=used_interface_ids).filter(device__isnull=False)

    @classmethod
    def _get_available_vlans(cls):
        used_vlan_ids = models.VPNTermination.objects.exclude(vlan__isnull=True).values_list("vlan_id", flat=True)
        return VLAN.objects.exclude(pk__in=used_vlan_ids)

    @classmethod
    def _get_available_vm_interfaces(cls):
        used_vm_interface_ids = models.VPNTermination.objects.exclude(vm_interface__isnull=True).values_list(
            "vm_interface_id", flat=True
        )
        available_vm_interfaces = VMInterface.objects.exclude(pk__in=used_vm_interface_ids)
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
            name=f"vpn-termination-form-{cls.__name__.lower()}",
            status=vm_interface_status,
        )
        return VMInterface.objects.exclude(pk__in=used_vm_interface_ids)

    def test_termination_with_interface(self):
        vpn = models.VPN.objects.first()
        interface = self._get_available_interfaces().first()

        self.assertIsNotNone(vpn)
        self.assertIsNotNone(interface)
        form = self.form_class(data={"vpn": str(vpn.pk), "interface": str(interface.pk)})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["interface"], interface)

    def test_termination_with_vlan(self):
        vpn = models.VPN.objects.first()
        vlan = self._get_available_vlans().first()

        self.assertIsNotNone(vpn)
        self.assertIsNotNone(vlan)
        form = self.form_class(data={"vpn": str(vpn.pk), "vlan": str(vlan.pk)})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["vlan"], vlan)

    def test_termination_with_vm_interface(self):
        vpn = models.VPN.objects.first()
        vm_interface = self._get_available_vm_interfaces().first()

        self.assertIsNotNone(vpn)
        self.assertIsNotNone(vm_interface)
        form = self.form_class(data={"vpn": str(vpn.pk), "vm_interface": str(vm_interface.pk)})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["vm_interface"], vm_interface)

    def test_validation_no_termination_object(self):
        vpn = models.VPN.objects.first()

        self.assertIsNotNone(vpn)
        form = self.form_class(data={"vpn": str(vpn.pk)})
        self.assertFalse(form.is_valid())
        self.assertIn("Exactly one of VLAN, interface, or VM interface must be selected.", str(form.errors))

    def test_validation_multiple_objects_selected(self):
        vpn = models.VPN.objects.first()
        interface = self._get_available_interfaces().first()
        vlan = self._get_available_vlans().first()

        self.assertIsNotNone(vpn)
        self.assertIsNotNone(interface)
        self.assertIsNotNone(vlan)
        form = self.form_class(
            data={
                "vpn": str(vpn.pk),
                "interface": str(interface.pk),
                "vlan": str(vlan.pk),
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Exactly one of VLAN, interface, or VM interface must be selected.", str(form.errors))

    def test_invalid_vlan_does_not_trigger_multiple_selection_error(self):
        vpn = models.VPN.objects.first()
        interface = self._get_available_interfaces().first()

        self.assertIsNotNone(vpn)
        self.assertIsNotNone(interface)
        form = self.form_class(
            data={
                "vpn": str(vpn.pk),
                "interface": str(interface.pk),
                "vlan": "not-a-valid-pk",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("vlan", form.errors)
        self.assertFalse(form.non_field_errors())

    def test_vpn_required(self):
        interface = self._get_available_interfaces().first()

        self.assertIsNotNone(interface)
        form = self.form_class(data={"interface": str(interface.pk)})
        self.assertFalse(form.is_valid())
        self.assertIn("vpn", form.errors)
