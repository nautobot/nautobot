"""Test vpn Filters."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.apps.testing import FilterTestCases
from nautobot.dcim.models import Interface
from nautobot.extras.models import Status
from nautobot.ipam.models import VLAN
from nautobot.virtualization.models import VMInterface
from nautobot.vpn import choices, filters, models


class VPNProfileFilterTestCase(FilterTestCases.FilterTestCase):
    """VPNProfileFilterSet Test Case."""

    queryset = models.VPNProfile.objects.all()
    filterset = filters.VPNProfileFilterSet
    generic_filter_tests = (
        ("name",),
        ("description",),
        ("vpn_phase1_policies", "vpn_phase1_policies__id"),
        ("vpn_phase1_policies", "vpn_phase1_policies__name"),
        ("vpn_phase2_policies", "vpn_phase2_policies__id"),
        ("vpn_phase2_policies", "vpn_phase2_policies__name"),
        ("keepalive_interval",),
        ("keepalive_retries",),
    )


class VPNPhase1PolicyFilterTestCase(FilterTestCases.FilterTestCase):
    """VPNPhase1PolicyFilterSet Test Case."""

    queryset = models.VPNPhase1Policy.objects.all()
    filterset = filters.VPNPhase1PolicyFilterSet
    generic_filter_tests = (
        ("name",),
        ("description",),
        ("lifetime_seconds",),
        ("lifetime_kb",),
        ("authentication_method",),
    )

    def test_encryption_algorithm(self):
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"encryption_algorithm": "AES-128-CBC"}, self.queryset).qs,
            self.queryset.filter(encryption_algorithm__contains=["AES-128-CBC"]),
            ordered=False,
        )

    def test_integrity_algorithm(self):
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"integrity_algorithm": "SHA256"}, self.queryset).qs,
            self.queryset.filter(integrity_algorithm__contains=["SHA256"]),
            ordered=False,
        )

    def test_dh_group(self):
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"dh_group": "14"}, self.queryset).qs,
            self.queryset.filter(dh_group__contains=["14"]),
            ordered=False,
        )


class VPNPhase2PolicyFilterTestCase(FilterTestCases.FilterTestCase):
    """VPNPhase2PolicyFilterSet Test Case."""

    queryset = models.VPNPhase2Policy.objects.all()
    filterset = filters.VPNPhase2PolicyFilterSet
    generic_filter_tests = (
        ("name",),
        ("description",),
        ("lifetime",),
    )

    def test_encryption_algorithm(self):
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"encryption_algorithm": "AES-128-CBC"}, self.queryset).qs,
            self.queryset.filter(encryption_algorithm__contains=["AES-128-CBC"]),
            ordered=False,
        )

    def test_integrity_algorithm(self):
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"integrity_algorithm": "SHA256"}, self.queryset).qs,
            self.queryset.filter(integrity_algorithm__contains=["SHA256"]),
            ordered=False,
        )

    def test_pfs_group(self):
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"pfs_group": "14"}, self.queryset).qs,
            self.queryset.filter(pfs_group__contains=["14"]),
            ordered=False,
        )


class VPNFilterTestCase(FilterTestCases.FilterTestCase):
    """VPNFilterSet Test Case."""

    queryset = models.VPN.objects.all()
    filterset = filters.VPNFilterSet
    generic_filter_tests = (
        ("vpn_profile", "vpn_profile__id"),
        ("vpn_profile", "vpn_profile__name"),
        ("name",),
        ("description",),
        ("vpn_id",),
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        vpn_ct = ContentType.objects.get_for_model(models.VPN)
        active = Status.objects.get(name="Active")
        active.content_types.add(vpn_ct)
        if not models.VPN.objects.filter(name="VPN Filter VXLAN").exists():
            models.VPN.objects.create(
                name="VPN Filter VXLAN",
                service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
                status=active,
                identifier=18001,
            )
            models.VPN.objects.create(
                name="VPN Filter VPLS",
                service_type=choices.VPNServiceTypeChoices.TYPE_VPLS,
                status=active,
                identifier=18002,
            )

    def test_filter_by_service_type(self):
        queryset = self.queryset
        expected = queryset.filter(service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN)
        filtered = self.filterset({"service_type": [choices.VPNServiceTypeChoices.TYPE_VXLAN]}, queryset).qs
        self.assertQuerysetEqualAndNotEmpty(filtered, expected, ordered=False)

    def test_filter_by_identifier(self):
        queryset = self.queryset
        vpn = queryset.filter(identifier__isnull=False).first()
        self.assertIsNotNone(vpn)
        filtered = self.filterset({"identifier": vpn.identifier}, queryset).qs
        self.assertTrue(filtered.filter(pk=vpn.pk).exists())

    def test_search_filter_matches_overlay_fields(self):
        queryset = self.queryset
        vpn = queryset.filter(service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN).first()
        self.assertIsNotNone(vpn)
        filtered = self.filterset({"q": vpn.name[:8]}, queryset).qs
        self.assertTrue(filtered.filter(pk=vpn.pk).exists())


class VPNTunnelFilterTestCase(FilterTestCases.FilterTestCase):
    """VPNTunnelFilterSet Test Case."""

    queryset = models.VPNTunnel.objects.all()
    filterset = filters.VPNTunnelFilterSet
    generic_filter_tests = (
        ("id",),
        ("vpn_profile", "vpn_profile__id"),
        ("vpn_profile", "vpn_profile__name"),
        ("vpn", "vpn__id"),
        ("vpn", "vpn__name"),
        ("name",),
        ("description",),
        ("tunnel_id",),
        ("encapsulation",),
    )


class VPNTunnelEndpointFilterTestCase(FilterTestCases.FilterTestCase):
    """VPNTunnelEndpointFilterSet Test Case."""

    queryset = models.VPNTunnelEndpoint.objects.all()
    filterset = filters.VPNTunnelEndpointFilterSet
    generic_filter_tests = (
        ("device", "device__id"),
        ("device", "device__name"),
        ("source_interface", "source_interface__id"),
        ("source_interface", "source_interface__name"),
        ("source_fqdn",),
        ("endpoint_a_vpn_tunnels", "endpoint_a_vpn_tunnels__id"),
        ("endpoint_a_vpn_tunnels", "endpoint_a_vpn_tunnels__name"),
        ("endpoint_z_vpn_tunnels", "endpoint_z_vpn_tunnels__id"),
        ("endpoint_z_vpn_tunnels", "endpoint_z_vpn_tunnels__name"),
    )


class VPNAttachmentFilterTestCase(TestCase):
    """VPNAttachment filter tests."""

    @classmethod
    def _get_available_vlans(cls):
        used_vlan_ids = models.VPNAttachment.objects.exclude(vlan__isnull=True).values_list("vlan_id", flat=True)
        return VLAN.objects.exclude(pk__in=used_vlan_ids)

    @classmethod
    def _get_available_interfaces(cls):
        used_interface_ids = models.VPNAttachment.objects.exclude(interface__isnull=True).values_list(
            "interface_id", flat=True
        )
        return Interface.objects.exclude(pk__in=used_interface_ids).filter(device__isnull=False)

    @classmethod
    def _get_available_vm_interfaces(cls):
        used_vm_interface_ids = models.VPNAttachment.objects.exclude(vm_interface__isnull=True).values_list(
            "vm_interface_id", flat=True
        )
        return VMInterface.objects.exclude(pk__in=used_vm_interface_ids)

    @classmethod
    def setUpTestData(cls):
        active = Status.objects.get(name="Active")
        active.content_types.add(ContentType.objects.get_for_model(models.VPN))
        cls.vpn = models.VPN.objects.create(
            name="VPN Attachment Filter Test",
            service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
            status=active,
            identifier=15000,
        )

        cls.attachments = []
        vlan = cls._get_available_vlans().first()
        interface = cls._get_available_interfaces().first()
        vm_interface = cls._get_available_vm_interfaces().first()
        if vlan:
            cls.attachments.append(models.VPNAttachment.objects.create(vpn=cls.vpn, vlan=vlan))
        if interface:
            cls.attachments.append(models.VPNAttachment.objects.create(vpn=cls.vpn, interface=interface))
        if vm_interface:
            cls.attachments.append(models.VPNAttachment.objects.create(vpn=cls.vpn, vm_interface=vm_interface))

    def test_filter_by_vpn(self):
        queryset = models.VPNAttachment.objects.all()
        filtered_qs = filters.VPNAttachmentFilterSet({"vpn": [self.vpn.pk]}, queryset).qs
        self.assertEqual(filtered_qs.count(), len(self.attachments))

    def test_search_filter(self):
        queryset = models.VPNAttachment.objects.all()
        filtered_qs = filters.VPNAttachmentFilterSet({"q": self.vpn.name}, queryset).qs
        self.assertTrue(filtered_qs.count() >= 1)
