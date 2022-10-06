from operator import attrgetter

from nautobot.ipam.models import IPAddress, Prefix
from nautobot.utilities.testing import TestCase


class OrderingTestBase(TestCase):
    fixtures = ("status",)

    def _compare(self, queryset, objectset):
        """
        Perform the comparison of the queryset object and the object used to instantiate the queryset.
        """
        for i, obj in enumerate(queryset):
            self.assertEqual(obj, objectset[i])

    def _compare_ne(self, queryset, objectset):
        """
        Perform the comparison of the queryset object and the object used to instantiate the queryset.
        """
        for i, obj in enumerate(queryset):
            self.assertNotEqual(obj, objectset[i])


class PrefixOrderingTestCase(OrderingTestBase):
    fixtures = ("status",)

    def test_prefix_vrf_ordering(self):
        """
        Test Prefix ordering (vrf.name, then network, then prefix_length)
        """
        prefixes = sorted(
            Prefix.objects.filter(vrf__isnull=True),
            key=attrgetter("prefix.network.packed", "prefix_length"),
        ) + sorted(
            Prefix.objects.filter(vrf__isnull=False),
            key=attrgetter("vrf.name", "prefix.network.packed", "prefix_length"),
        )
        self._compare(Prefix.objects.all(), prefixes)


class IPAddressOrderingTestCase(OrderingTestBase):
    fixtures = ("status",)

    def test_address_vrf_ordering(self):
        """
        This function tests IPAddress ordering (host, then prefix_length)
        """
        addresses = sorted(IPAddress.objects.all(), key=attrgetter("address.network.packed", "prefix_length"))
        self._compare(IPAddress.objects.all(), addresses)
