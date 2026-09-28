"""Test vpn Filters."""

from django.contrib.contenttypes.models import ContentType

from nautobot.apps.testing import FilterTestCases
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress
from nautobot.vpn import choices, factory as vpn_factory, filters, models


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
        self.assertQuerySetEqualAndNotEmpty(
            self.filterset({"encryption_algorithm": "AES-128-CBC"}, self.queryset).qs,
            self.queryset.filter(encryption_algorithm__contains=["AES-128-CBC"]),
            ordered=False,
        )

    def test_integrity_algorithm(self):
        self.assertQuerySetEqualAndNotEmpty(
            self.filterset({"integrity_algorithm": "SHA256"}, self.queryset).qs,
            self.queryset.filter(integrity_algorithm__contains=["SHA256"]),
            ordered=False,
        )

    def test_dh_group(self):
        self.assertQuerySetEqualAndNotEmpty(
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
        self.assertQuerySetEqualAndNotEmpty(
            self.filterset({"encryption_algorithm": "AES-128-CBC"}, self.queryset).qs,
            self.queryset.filter(encryption_algorithm__contains=["AES-128-CBC"]),
            ordered=False,
        )

    def test_integrity_algorithm(self):
        self.assertQuerySetEqualAndNotEmpty(
            self.filterset({"integrity_algorithm": "SHA256"}, self.queryset).qs,
            self.queryset.filter(integrity_algorithm__contains=["SHA256"]),
            ordered=False,
        )

    def test_pfs_group(self):
        self.assertQuerySetEqualAndNotEmpty(
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
        ("service_type",),
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
                vpn_id="18001",
            )
            models.VPN.objects.create(
                name="VPN Filter VPLS",
                service_type=choices.VPNServiceTypeChoices.TYPE_VPLS,
                status=active,
                vpn_id="18002",
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
        ("source_ipaddress", "source_ipaddress__id"),
        ("source_fqdn",),
        ("endpoint_a_vpn_tunnels", "endpoint_a_vpn_tunnels__id"),
        ("endpoint_a_vpn_tunnels", "endpoint_a_vpn_tunnels__name"),
        ("endpoint_z_vpn_tunnels", "endpoint_z_vpn_tunnels__id"),
        ("endpoint_z_vpn_tunnels", "endpoint_z_vpn_tunnels__name"),
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        endpoints_with_ip = models.VPNTunnelEndpoint.objects.filter(source_ipaddress__isnull=False)
        needed = 3 - endpoints_with_ip.count()
        if needed > 0:
            candidates = list(
                models.VPNTunnelEndpoint.objects.filter(source_interface__isnull=False, source_ipaddress__isnull=True)[
                    :needed
                ]
            )
            available_ips = list(
                IPAddress.objects.exclude(
                    id__in=models.VPNTunnelEndpoint.objects.filter(source_ipaddress__isnull=False).values_list(
                        "source_ipaddress_id", flat=True
                    )
                )[:needed]
            )
            for endpoint, ip in zip(candidates, available_ips):
                endpoint.source_interface.add_ip_addresses(ip)
                endpoint.source_ipaddress = ip
                endpoint.save()

    def test_source_ipaddress(self):
        endpoints = models.VPNTunnelEndpoint.objects.filter(source_ipaddress__isnull=False)
        ip1 = endpoints[0].source_ipaddress
        ip2 = endpoints[1].source_ipaddress

        # Test filtering by address string
        self.assertQuerySetEqualAndNotEmpty(
            self.filterset({"source_ipaddress": [str(ip1.address)]}, self.queryset).qs,
            self.queryset.filter(source_ipaddress=ip1),
            ordered=False,
        )
        # Test filtering by host string
        self.assertQuerySetEqualAndNotEmpty(
            self.filterset({"source_ipaddress": [str(ip1.host)]}, self.queryset).qs,
            self.queryset.filter(source_ipaddress=ip1),
            ordered=False,
        )
        # Test filtering by mixed address string and PK
        self.assertQuerySetEqualAndNotEmpty(
            self.filterset({"source_ipaddress": [str(ip1.address), str(ip2.pk)]}, self.queryset).qs,
            self.queryset.filter(source_ipaddress__in=[ip1, ip2]),
            ordered=False,
        )


class VPNTerminationFilterTestCase(FilterTestCases.FilterTestCase):
    """VPNTermination filter tests."""

    queryset = models.VPNTermination.objects.all()
    filterset = filters.VPNTerminationFilterSet
    generic_filter_tests = (
        ("vpn", "vpn__id"),
        ("vpn", "vpn__name"),
        ("vlan", "vlan__id"),
        ("interface", "interface__id"),
        ("vm_interface", "vm_interface__id"),
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        active = Status.objects.get(name="Active")
        active.content_types.add(ContentType.objects.get_for_model(models.VPN))
        cls.vpns = [
            models.VPN.objects.create(
                name=f"VPN Termination Filter Test {index}",
                service_type=choices.VPNServiceTypeChoices.TYPE_VXLAN,
                status=active,
                vpn_id=f"1500{index}",
            )
            for index in range(3)
        ]
        cls.terminations = []
        for target_type in ("vlan", "interface", "vm_interface"):
            for vpn in cls.vpns:
                cls.terminations.append(vpn_factory.VPNTerminationFactory.create(vpn=vpn, target_type=target_type))

    def test_search_filter(self):
        queryset = models.VPNTermination.objects.all()
        filtered_qs = filters.VPNTerminationFilterSet({"q": self.vpns[0].name}, queryset).qs
        self.assertTrue(filtered_qs.filter(vpn=self.vpns[0]).exists())


class VPNProfilePhase1PolicyAssignmentFilterTestCase(FilterTestCases.FilterTestCase):
    """VPNProfilePhase1PolicyAssignmentFilterSet Test Case."""

    queryset = models.VPNProfilePhase1PolicyAssignment.objects.all()
    filterset = filters.VPNProfilePhase1PolicyAssignmentFilterSet
    generic_filter_tests = (
        ("vpn_profile", "vpn_profile__id"),
        ("vpn_profile", "vpn_profile__name"),
        ("vpn_phase1_policy", "vpn_phase1_policy__id"),
        ("vpn_phase1_policy", "vpn_phase1_policy__name"),
    )


class VPNProfilePhase2PolicyAssignmentFilterTestCase(FilterTestCases.FilterTestCase):
    """VPNProfilePhase2PolicyAssignmentFilterSet Test Case."""

    queryset = models.VPNProfilePhase2PolicyAssignment.objects.all()
    filterset = filters.VPNProfilePhase2PolicyAssignmentFilterSet
    generic_filter_tests = (
        ("vpn_profile", "vpn_profile__id"),
        ("vpn_profile", "vpn_profile__name"),
        ("vpn_phase2_policy", "vpn_phase2_policy__id"),
        ("vpn_phase2_policy", "vpn_phase2_policy__name"),
    )
