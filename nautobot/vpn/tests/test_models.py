"""Test vpn models."""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from nautobot.apps.testing import ModelTestCases
from nautobot.dcim.models import Device, Interface, Module
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import VMInterface
from nautobot.vpn import choices, models


class VPNDocsTestMixin:
    """VPN model tests don't rely on project-static documentation assets being present."""

    def test_get_docs_url(self):
        self.skipTest("Static VPN documentation assets are not part of the tracked source tree.")


class TestVPNProfileModel(VPNDocsTestMixin, ModelTestCases.BaseModelTestCase):
    """Test VPNProfile model."""

    model = models.VPNProfile


class TestVPNPhase1PolicyModel(VPNDocsTestMixin, ModelTestCases.BaseModelTestCase):
    """Test VPNPhase1Policy model."""

    model = models.VPNPhase1Policy


class TestVPNPhase2PolicyModel(VPNDocsTestMixin, ModelTestCases.BaseModelTestCase):
    """Test VPNPhase2Policy model."""

    model = models.VPNPhase2Policy


class VPNProfilePhase1PolicyAssignmentModel(VPNDocsTestMixin, ModelTestCases.BaseModelTestCase):
    """Test VPNPhase1Policy model."""

    model = models.VPNProfilePhase1PolicyAssignment


class VPNProfilePhase2PolicyAssignmentModel(VPNDocsTestMixin, ModelTestCases.BaseModelTestCase):
    """Test VPNPhase1Policy model."""

    model = models.VPNProfilePhase2PolicyAssignment


class TestVPNModel(VPNDocsTestMixin, ModelTestCases.BaseModelTestCase):
    """Test VPN model."""

    model = models.VPN


class TestVPNTunnelModel(VPNDocsTestMixin, ModelTestCases.BaseModelTestCase):
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


class TestVPNTunnelEndpointModel(VPNDocsTestMixin, ModelTestCases.BaseModelTestCase):
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


class VPNOverlayModelTestCase(TestCase):
    """Behavioral tests for overlay-related VPN fields."""

    @classmethod
    def _get_vpn_status(cls):
        """Get or create an Active status for the VPN model."""
        ct = ContentType.objects.get_for_model(models.VPN)
        status = Status.objects.filter(content_types=ct).first()
        if not status:
            status = Status.objects.get(name="Active")
            status.content_types.add(ct)
        return status

    @classmethod
    def _get_available_interfaces(cls):
        used = models.VPNAttachment.objects.exclude(interface__isnull=True).values_list("interface_id", flat=True)
        return Interface.objects.exclude(pk__in=used).filter(device__isnull=False)

    @classmethod
    def setUpTestData(cls):
        cls.status = cls._get_vpn_status()

    def test_can_add_attachment_non_p2p(self):
        vpn = models.VPN.objects.create(
            name="VXLAN Service",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            identifier=10001,
        )
        self.assertTrue(vpn.can_add_attachment)

    def test_can_add_attachment_p2p_under_limit(self):
        vpn = models.VPN.objects.create(
            name="VPWS Service",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPWS,
            status=self.status,
        )
        self.assertTrue(vpn.can_add_attachment)

    def test_can_add_attachment_p2p_at_limit(self):
        vpn = models.VPN.objects.create(
            name="VPWS Limited Service",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPWS,
            status=self.status,
        )
        interfaces = list(self._get_available_interfaces()[:2])
        if len(interfaces) < 2:
            self.skipTest("Need at least two unused interfaces for attachment testing.")

        models.VPNAttachment.objects.create(vpn=vpn, interface=interfaces[0])
        models.VPNAttachment.objects.create(vpn=vpn, interface=interfaces[1])
        self.assertFalse(vpn.can_add_attachment)

    def test_identifier_valid_vxlan_vni(self):
        vpn = models.VPN(
            name="Valid VNI Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            identifier=10000,
        )
        vpn.full_clean()

    def test_identifier_required_for_vxlan_service(self):
        vpn = models.VPN(
            name="Missing VNI Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
        )
        with self.assertRaises(ValidationError) as context:
            vpn.full_clean()
        self.assertIn("identifier", context.exception.message_dict)

    def test_identifier_vxlan_vni_too_high(self):
        vpn = models.VPN(
            name="High VNI Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            identifier=16777215,
        )
        with self.assertRaises(ValidationError) as context:
            vpn.full_clean()
        self.assertIn("identifier", context.exception.message_dict)

    def test_identifier_vxlan_boundary_values(self):
        for identifier in (
            choices.VPNServiceTypeChoices.VXLAN_VNI_MIN,
            choices.VPNServiceTypeChoices.VXLAN_VNI_MAX,
        ):
            with self.subTest(identifier=identifier):
                vpn = models.VPN(
                    name=f"Boundary VNI {identifier}",
                    service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
                    status=self.status,
                    identifier=identifier,
                )
                vpn.full_clean()

    def test_identifier_negative_rejected(self):
        vpn = models.VPN(
            name="Negative ID Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPLS,
            status=self.status,
            identifier=-1,
        )
        with self.assertRaises(ValidationError) as context:
            vpn.full_clean()
        self.assertIn("identifier", context.exception.message_dict)

    def test_identifier_non_vxlan_type_allows_large_value(self):
        vpn = models.VPN(
            name="Large VPLS ID Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPLS,
            status=self.status,
            identifier=99999999,
        )
        vpn.full_clean()

    def test_tenant_relationship(self):
        tenant = Tenant.objects.first()
        if tenant is None:
            self.skipTest("No tenant fixture available.")

        vpn = models.VPN.objects.create(
            name="VPN Tenant Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            identifier=11000,
            tenant=tenant,
        )
        self.assertEqual(vpn.tenant, tenant)
        self.assertIn(vpn, tenant.vpns.all())


class VPNAttachmentModelTestCase(TestCase):
    """Behavioral tests for VPNAttachment."""

    @classmethod
    def _get_vpn_status(cls):
        ct = ContentType.objects.get_for_model(models.VPN)
        status = Status.objects.filter(content_types=ct).first()
        if not status:
            status = Status.objects.get(name="Active")
            status.content_types.add(ct)
        return status

    @classmethod
    def _get_available_interfaces(cls):
        used = models.VPNAttachment.objects.exclude(interface__isnull=True).values_list("interface_id", flat=True)
        return Interface.objects.exclude(pk__in=used).filter(device__isnull=False)

    @classmethod
    def _get_available_vlans(cls):
        used = models.VPNAttachment.objects.exclude(vlan__isnull=True).values_list("vlan_id", flat=True)
        return VLAN.objects.exclude(pk__in=used)

    @classmethod
    def _get_available_vm_interfaces(cls):
        used = models.VPNAttachment.objects.exclude(vm_interface__isnull=True).values_list("vm_interface_id", flat=True)
        return VMInterface.objects.exclude(pk__in=used)

    @classmethod
    def setUpTestData(cls):
        cls.status = cls._get_vpn_status()
        cls.vpn = models.VPN.objects.create(
            name="VPN For Attachment Tests",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=cls.status,
            identifier=12000,
        )

    def test_str_with_assigned_object(self):
        vlan = self._get_available_vlans().first()
        if vlan is None:
            self.skipTest("No unused VLAN available.")

        attachment = models.VPNAttachment.objects.create(vpn=self.vpn, vlan=vlan)
        self.assertEqual(str(attachment), f"{vlan} <> {self.vpn}")

    def test_clean_requires_exactly_one_object(self):
        attachment = models.VPNAttachment(vpn=self.vpn)
        with self.assertRaises(ValidationError):
            attachment.clean()

    def test_clean_rejects_multiple_objects(self):
        vlan = self._get_available_vlans().first()
        interface = self._get_available_interfaces().first()
        if vlan is None or interface is None:
            self.skipTest("Need both an unused VLAN and interface.")

        attachment = models.VPNAttachment(vpn=self.vpn, vlan=vlan, interface=interface)
        with self.assertRaises(ValidationError):
            attachment.clean()

    def test_clean_p2p_limit_exceeded(self):
        vpn = models.VPN.objects.create(
            name="P2P Attachment Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VPWS,
            status=self.status,
        )
        interfaces = list(self._get_available_interfaces()[:3])
        if len(interfaces) < 3:
            self.skipTest("Need at least three unused interfaces.")

        models.VPNAttachment.objects.create(vpn=vpn, interface=interfaces[0])
        models.VPNAttachment.objects.create(vpn=vpn, interface=interfaces[1])

        attachment = models.VPNAttachment(vpn=vpn, interface=interfaces[2])
        with self.assertRaises(ValidationError):
            attachment.clean()

    def test_duplicate_attachment_rejected_by_constraint(self):
        interface = self._get_available_interfaces().first()
        if interface is None:
            self.skipTest("No unused interface available.")

        models.VPNAttachment.objects.create(vpn=self.vpn, interface=interface)
        with self.assertRaises(IntegrityError):
            models.VPNAttachment.objects.create(vpn=self.vpn, interface=interface)

    def test_attachment_with_interface(self):
        interface = self._get_available_interfaces().first()
        if interface is None:
            self.skipTest("No unused interface available.")

        attachment = models.VPNAttachment.objects.create(vpn=self.vpn, interface=interface)
        self.assertEqual(attachment.assigned_object, interface)
        self.assertEqual(attachment.assigned_object_type, "dcim.interface")
        self.assertEqual(attachment.assigned_object_parent, interface.device)

    def test_attachment_with_vlan(self):
        vlan = self._get_available_vlans().first()
        if vlan is None:
            self.skipTest("No unused VLAN available.")

        attachment = models.VPNAttachment.objects.create(vpn=self.vpn, vlan=vlan)
        self.assertEqual(attachment.assigned_object, vlan)
        self.assertEqual(attachment.assigned_object_type, "ipam.vlan")

    def test_attachment_with_vm_interface(self):
        vm_interface = self._get_available_vm_interfaces().first()
        if vm_interface is None:
            self.skipTest("No unused VM interface available.")

        attachment = models.VPNAttachment.objects.create(vpn=self.vpn, vm_interface=vm_interface)
        self.assertEqual(attachment.assigned_object, vm_interface)
        self.assertEqual(attachment.assigned_object_type, "virtualization.vminterface")

    def test_cascade_delete_on_vpn_delete(self):
        interface = self._get_available_interfaces().first()
        if interface is None:
            self.skipTest("No unused interface available.")

        vpn = models.VPN.objects.create(
            name="Cascade Delete Attachment Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=self.status,
            identifier=13000,
        )
        attachment = models.VPNAttachment.objects.create(vpn=vpn, interface=interface)
        attachment_pk = attachment.pk

        vpn.delete()
        self.assertFalse(models.VPNAttachment.objects.filter(pk=attachment_pk).exists())
