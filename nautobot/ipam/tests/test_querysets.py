import netaddr

from nautobot.ipam.models import Prefix, Aggregate, IPAddress, RIR
from nautobot.utilities.testing import TestCase


class AggregateQuerysetTestCase(TestCase):
    queryset = Aggregate.objects.all()

    @classmethod
    def setUpTestData(cls):

        rir = RIR.objects.create(name="RIR 1", slug="rir-1")

        Aggregate.objects.create(prefix=netaddr.IPNetwork("192.168.0.0/16"), rir=rir)

        Aggregate.objects.create(prefix=netaddr.IPNetwork("192.168.1.0/24"), rir=rir)
        Aggregate.objects.create(prefix=netaddr.IPNetwork("192.168.2.0/24"), rir=rir)
        Aggregate.objects.create(prefix=netaddr.IPNetwork("192.168.3.0/24"), rir=rir)

        Aggregate.objects.create(prefix=netaddr.IPNetwork("192.168.3.192/28"), rir=rir)
        Aggregate.objects.create(prefix=netaddr.IPNetwork("192.168.3.208/28"), rir=rir)
        Aggregate.objects.create(prefix=netaddr.IPNetwork("192.168.3.224/28"), rir=rir)

    def test_net_equals(self):
        self.assertEqual(self.queryset.net_equals(netaddr.IPNetwork("192.168.0.0/16")).count(), 1)
        self.assertEqual(self.queryset.net_equals(netaddr.IPNetwork("192.1.0.0/16")).count(), 0)

    def test_net_contained(self):
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.0.0.0/8")).count(), 7)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.0.0/16")).count(), 6)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.3.0/24")).count(), 3)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.1.0/24")).count(), 0)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.3.192/28")).count(), 0)

    def test_net_contained_or_equal(self):
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.0.0.0/8")).count(), 7)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.0.0/16")).count(), 7)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.3.0/24")).count(), 4)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.1.0/24")).count(), 1)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.3.192/28")).count(), 1)

    def test_net_contains(self):
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.0.0/8")).count(), 0)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.0.0/16")).count(), 0)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.0/24")).count(), 1)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.192/28")).count(), 2)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.192/30")).count(), 3)

    def test_net_contains_or_equal(self):
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.0.0/8")).count(), 0)
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.0.0/16")).count(), 1)
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.3.0/24")).count(), 2)
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.3.192/28")).count(), 3)
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.3.192/30")).count(), 3)


class IPAddressQuerySet(TestCase):
    queryset = IPAddress.objects.all()

    @classmethod
    def setUpTestData(cls):

        IPAddress.objects.create(address="10.0.0.1/24", vrf=None, tenant=None)
        IPAddress.objects.create(address="10.0.0.2/24", vrf=None, tenant=None)
        IPAddress.objects.create(address="10.0.0.3/24", vrf=None, tenant=None)
        IPAddress.objects.create(address="10.0.0.4/24", vrf=None, tenant=None)
        IPAddress.objects.create(address="10.0.0.1/25", vrf=None, tenant=None)
        IPAddress.objects.create(address="2001:db8::1/64", vrf=None, tenant=None)
        IPAddress.objects.create(address="2001:db8::2/64", vrf=None, tenant=None)
        IPAddress.objects.create(address="2001:db8::3/64", vrf=None, tenant=None)

    def test_ip_family(self):
        self.assertEqual(self.queryset.ip_family(4).count(), 5)
        self.assertEqual(self.queryset.ip_family(6).count(), 3)

    def test_net_host_contained(self):
        pass

    def test_net_contained_or_equal(self):
        pass

    def test_net_in(self):
        args = ["10.0.0.1/24"]
        self.assertEqual(self.queryset.net_in(args).count(), 1)

        args = ["10.0.0.1"]
        self.assertEqual(self.queryset.net_in(args).count(), 2)

        args = ["10.0.0.1/24", "10.0.0.1/25"]
        self.assertEqual(self.queryset.net_in(args).count(), 2)


class PrefixQuerysetTestCase(TestCase):
    queryset = Prefix.objects.all()

    @classmethod
    def setUpTestData(cls):

        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.0.0/16"))

        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.1.0/24"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.2.0/24"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.0/24"))

        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.192/28"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.208/28"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.224/28"))

    def test_net_equals(self):
        self.assertEqual(self.queryset.net_equals(netaddr.IPNetwork("192.168.0.0/16")).count(), 1)
        self.assertEqual(self.queryset.net_equals(netaddr.IPNetwork("192.1.0.0/16")).count(), 0)

    def test_net_contained(self):
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.0.0.0/8")).count(), 7)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.0.0/16")).count(), 6)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.3.0/24")).count(), 3)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.1.0/24")).count(), 0)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.3.192/28")).count(), 0)

    def test_net_contained_or_equal(self):
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.0.0.0/8")).count(), 7)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.0.0/16")).count(), 7)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.3.0/24")).count(), 4)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.1.0/24")).count(), 1)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.3.192/28")).count(), 1)

    def test_net_contains(self):
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.0.0/8")).count(), 0)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.0.0/16")).count(), 0)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.0/24")).count(), 1)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.192/28")).count(), 2)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.192/30")).count(), 3)

    def test_net_contains_or_equal(self):
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.0.0/8")).count(), 0)
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.0.0/16")).count(), 1)
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.3.0/24")).count(), 2)
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.3.192/28")).count(), 3)
        self.assertEqual(self.queryset.net_contains_or_equal(netaddr.IPNetwork("192.168.3.192/30")).count(), 3)
