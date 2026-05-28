from django.contrib.contenttypes.models import ContentType

from nautobot.core import testing
from nautobot.extras.models import Status
from nautobot.vpn import choices, factory, models


class VPNFactoryTestCase(testing.TestCase):
    """Tests for VPN factories."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        content_type = ContentType.objects.get_for_model(models.VPN)
        status = Status.objects.filter(content_types=content_type).first()
        if status is None:
            status = Status.objects.get(name="Active")
            status.content_types.add(content_type)

    def test_vpn_factory_can_populate_overlay_fields(self):
        """VPNFactory can populate the new overlay-related fields."""
        vpn = factory.VPNFactory.create(has_service_type=True, has_status=True, has_extra_attributes=True)

        self.assertIn(vpn.service_type, choices.VPNServiceTypeChoices.values())
        self.assertIsNotNone(vpn.status)
        self.assertIsInstance(vpn.extra_attributes, dict)

    def test_vpn_factory_generates_valid_vni_for_vxlan_service_types(self):
        """VXLAN-based service types get a valid numeric identifier."""
        for service_type in choices.VPNServiceTypeChoices.VXLAN_TYPES:
            vpn = factory.VPNFactory.create(service_type=service_type)

            self.assertEqual(vpn.service_type, service_type)
            self.assertTrue(vpn.vpn_id.isdigit())
            self.assertGreaterEqual(int(vpn.vpn_id), choices.VPNServiceTypeChoices.VXLAN_VNI_MIN)
            self.assertLessEqual(int(vpn.vpn_id), choices.VPNServiceTypeChoices.VXLAN_VNI_MAX)

    def test_vpn_termination_factory_populates_exactly_one_target(self):
        """VPNTerminationFactory populates one assigned object type per record."""
        expected_types = {
            "vlan": "ipam.vlan",
            "interface": "dcim.interface",
            "vm_interface": "virtualization.vminterface",
        }

        for target_type, assigned_object_type in expected_types.items():
            with self.subTest(target_type=target_type):
                termination = factory.VPNTerminationFactory.create(target_type=target_type)

                self.assertEqual(termination.assigned_object_type, assigned_object_type)
                self.assertEqual(
                    sum(
                        value is not None
                        for value in (termination.vlan, termination.interface, termination.vm_interface)
                    ),
                    1,
                )
