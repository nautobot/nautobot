from unittest import skip
from operator import attrgetter

from nautobot.core.testing import TestCase
from nautobot.ipam.models import IPAddress, Prefix


class OrderingTestBase(TestCase):
    def _compare(self, queryset, objectset):
        """
        Perform the comparison of the queryset object and the object used to instantiate the queryset.
        """
        for i, obj in enumerate(queryset):
            self.assertEqual(obj, objectset[i])


@skip
class PrefixOrderingTestCase(OrderingTestBase):
    def test_prefix_vrf_ordering(self):
        """
        Test Prefix ordering (vrf.name, then network, then prefix_length)
        """
        prefixes = sorted(
            Prefix.objects.filter(vrf__isnull=True),
            key=attrgetter("prefix.network.packed", "prefix_length"),
        ) + sorted(
            Prefix.objects.filter(vrf__isnull=False),
            key=attrgetter("prefix.network.packed", "prefix_length"),
        )
        self._compare(Prefix.objects.all(), prefixes)


@skip("Problem with MySQL")
class IPAddressOrderingTestCase(OrderingTestBase):
    def test_address_vrf_ordering(self):
        """
        This function tests IPAddress ordering (host, then mask_length)
        """
        addresses = sorted(IPAddress.objects.all(), key=attrgetter("address.network.packed", "mask_length"))
        self._compare(IPAddress.objects.all(), addresses)
