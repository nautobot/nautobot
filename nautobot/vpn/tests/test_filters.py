"""Test vpn Filters."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.apps.testing import FilterTestCases
from nautobot.extras.models import Status
from nautobot.ipam.models import RouteTarget, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
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


class L2VPNFilterTestCase(TestCase):
    """L2VPN FilterSet Test Case."""

    @classmethod
    def _get_l2vpn_status(cls):
        """Get or create a Status for L2VPN model."""
        ct = ContentType.objects.get_for_model(models.L2VPN)
        status = Status.objects.filter(content_types=ct).first()
        if not status:
            status = Status.objects.get(name="Active")
            status.content_types.add(ct)
        return status

    @classmethod
    def setUpTestData(cls):
        status = cls._get_l2vpn_status()
        tenant = Tenant.objects.first()

        # Create L2VPN objects for filter tests
        cls.l2vpn1 = models.L2VPN.objects.create(
            name="L2VPN Filter Test 1",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
            identifier=10001,
            description="Test L2VPN for filtering",
            tenant=tenant,
        )
        cls.l2vpn2 = models.L2VPN.objects.create(
            name="L2VPN Filter Test 2",
            type=choices.L2VPNTypeChoices.TYPE_VPLS,
            status=status,
            identifier=10002,
            description="Another test L2VPN",
        )
        cls.l2vpn3 = models.L2VPN.objects.create(
            name="L2VPN Filter Test 3",
            type=choices.L2VPNTypeChoices.TYPE_VPWS,
            status=status,
            identifier=10003,
            description="Third test L2VPN",
        )

    def test_filter_by_name(self):
        """Test filtering L2VPNs by name."""
        queryset = models.L2VPN.objects.all()
        params = {"name": self.l2vpn1.name}
        filtered_qs = filters.L2VPNFilterSet(params, queryset).qs
        self.assertEqual(filtered_qs.count(), 1)
        self.assertEqual(filtered_qs.first(), self.l2vpn1)

    def test_filter_by_type(self):
        """Test filtering L2VPNs by type."""
        queryset = models.L2VPN.objects.all()
        params = {"type": [choices.L2VPNTypeChoices.TYPE_VXLAN]}
        filtered_qs = filters.L2VPNFilterSet(params, queryset).qs
        self.assertTrue(all(obj.type == choices.L2VPNTypeChoices.TYPE_VXLAN for obj in filtered_qs))

    def test_filter_by_identifier(self):
        """Test filtering L2VPNs by identifier."""
        queryset = models.L2VPN.objects.all()
        params = {"identifier": self.l2vpn1.identifier}
        filtered_qs = filters.L2VPNFilterSet(params, queryset).qs
        self.assertTrue(filtered_qs.filter(pk=self.l2vpn1.pk).exists())

class L2VPNTerminationFilterTestCase(TestCase):
    """L2VPN Termination FilterSet Test Case, simple filter tests."""

    @classmethod
    def _get_l2vpn_status(cls):
        """Get or create a Status for L2VPN model."""
        ct = ContentType.objects.get_for_model(models.L2VPN)
        status = Status.objects.filter(content_types=ct).first()
        if not status:
            status = Status.objects.get(name="Active")
            status.content_types.add(ct)
        return status

    @classmethod
    def setUpTestData(cls):
        status = cls._get_l2vpn_status()

        # Create L2VPN for termination tests
        cls.l2vpn = models.L2VPN.objects.create(
            name="L2VPN Term Filter Test",
            type=choices.L2VPNTypeChoices.TYPE_VXLAN,
            status=status,
        )

        # Create VLANs for terminations (always available, unlike interfaces)
        vlan_status = Status.objects.get(name="Active")
        vlan_ct = ContentType.objects.get_for_model(VLAN)
        if vlan_ct not in vlan_status.content_types.all():
            vlan_status.content_types.add(vlan_ct)

        vlan_group, _ = VLANGroup.objects.get_or_create(name="L2VPN Filter Test Group")

        cls.terminations = []
        for i in range(3):
            vlan = VLAN.objects.create(
                vid=3900 + i,
                name=f"L2VPN Filter Test VLAN {i}",
                status=vlan_status,
                vlan_group=vlan_group,
            )
            term = models.L2VPNTermination.objects.create(l2vpn=cls.l2vpn, assigned_object=vlan)
            cls.terminations.append(term)

    def test_filter_by_l2vpn(self):
        """Test filtering terminations by L2VPN."""
        queryset = models.L2VPNTermination.objects.all()
        params = {"l2vpn": [self.l2vpn.pk]}
        filtered_qs = filters.L2VPNTerminationFilterSet(params, queryset).qs
        self.assertEqual(filtered_qs.count(), 3)
        for term in self.terminations:
            self.assertTrue(filtered_qs.filter(pk=term.pk).exists())

    def test_search_filter(self):
        """Test the q (search) filter for L2VPNTermination."""
        queryset = models.L2VPNTermination.objects.all()
        params = {"q": self.l2vpn.name}
        filtered_qs = filters.L2VPNTerminationFilterSet(params, queryset).qs
        self.assertTrue(filtered_qs.count() >= 1)
        self.assertTrue(filtered_qs.filter(pk=self.terminations[0].pk).exists())
