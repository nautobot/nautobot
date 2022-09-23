import netaddr

from nautobot.ipam.models import Prefix, Aggregate, IPAddress
from nautobot.utilities.testing import TestCase


class AggregateQuerysetTestCase(TestCase):
    queryset = Aggregate.objects.all()

    # Note: unlike Prefixes, Aggregates should never overlap; this is checked in Aggregate.clean().
    # A previous implementation of this test disregarded this restriction in order to test the Aggregate queryset
    # features more extensively, but this is shared logic between AggregateQueryset and PrefixQueryset and is
    # covered thoroughly by the PrefixQuerysetTestCase later in this file, so we can get adequate test coverage for
    # Aggregate querysets without violating the model's base assumptions.

    @classmethod
    def setUpTestData(cls):
        agg = cls.queryset.first()
        cls.exact_network = agg.prefix
        cls.parent_network = cls.exact_network.supernet()[-1]
        # Depending on random generation, parent_network *might* cover a second aggregate
        cls.parent_covers_second_aggregate = cls.queryset.net_equals(
            list(cls.parent_network.subnet(cls.exact_network.prefixlen))[1]
        ).exists()
        cls.child_network = list(cls.exact_network.subnet(cls.exact_network.prefixlen + 3))[0]

    def test_net_equals(self):
        self.assertEqual(self.queryset.net_equals(self.exact_network).count(), 1)
        self.assertEqual(self.queryset.net_equals(self.parent_network).count(), 0)
        self.assertEqual(self.queryset.net_equals(self.child_network).count(), 0)

    def test_net_contained(self):
        self.assertEqual(
            self.queryset.net_contained(self.parent_network).count(),
            1 if not self.parent_covers_second_aggregate else 2,
        )
        self.assertEqual(self.queryset.net_contained(self.exact_network).count(), 0)
        self.assertEqual(self.queryset.net_contained(self.child_network).count(), 0)

    def test_net_contained_or_equal(self):
        self.assertEqual(
            self.queryset.net_contained_or_equal(self.parent_network).count(),
            1 if not self.parent_covers_second_aggregate else 2,
        )
        self.assertEqual(self.queryset.net_contained_or_equal(self.exact_network).count(), 1)
        self.assertEqual(self.queryset.net_contained_or_equal(self.child_network).count(), 0)

    def test_net_contains(self):
        self.assertEqual(self.queryset.net_contains(self.parent_network).count(), 0)
        self.assertEqual(self.queryset.net_contains(self.exact_network).count(), 0)
        self.assertEqual(self.queryset.net_contains(self.child_network).count(), 1)

    def test_net_contains_or_equals(self):
        self.assertEqual(self.queryset.net_contains_or_equals(self.parent_network).count(), 0)
        self.assertEqual(self.queryset.net_contains_or_equals(self.exact_network).count(), 1)
        self.assertEqual(self.queryset.net_contains_or_equals(self.child_network).count(), 1)

    def test_get_by_prefix(self):
        prefix = self.queryset.net_equals(self.exact_network)[0]
        self.assertEqual(self.queryset.get(prefix=str(self.exact_network)), prefix)

    def test_get_by_prefix_fails(self):
        with self.assertRaises(Aggregate.DoesNotExist):
            self.queryset.get(prefix=self.parent_network)
        with self.assertRaises(Aggregate.DoesNotExist):
            self.queryset.get(prefix=self.child_network)

    def test_filter_by_prefix(self):
        prefix = self.queryset.net_equals(self.exact_network)[0]
        self.assertEqual(self.queryset.filter(prefix=self.exact_network)[0], prefix)


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
        self.assertEqual(self.queryset.net_host_contained(netaddr.IPNetwork("10.0.0.0/24")).count(), 5)
        self.assertEqual(self.queryset.net_host_contained(netaddr.IPNetwork("10.0.0.0/30")).count(), 4)
        self.assertEqual(self.queryset.net_host_contained(netaddr.IPNetwork("10.0.0.0/31")).count(), 2)
        self.assertEqual(self.queryset.net_host_contained(netaddr.IPNetwork("10.0.10.0/24")).count(), 0)

    def test_net_in(self):
        args = ["10.0.0.1/24"]
        self.assertEqual(self.queryset.net_in(args).count(), 1)

        args = ["10.0.0.1"]
        self.assertEqual(self.queryset.net_in(args).count(), 2)

        args = ["10.0.0.1/24", "10.0.0.1/25"]
        self.assertEqual(self.queryset.net_in(args).count(), 2)

    def test_get_by_address(self):
        address = self.queryset.net_in(["10.0.0.1/24"])[0]
        self.assertEqual(self.queryset.get(address="10.0.0.1/24"), address)

    def test_filter_by_address(self):
        address = self.queryset.net_in(["10.0.0.1/24"])[0]
        self.assertEqual(self.queryset.filter(address="10.0.0.1/24")[0], address)

    def test_string_search_parse_network_string(self):
        """
        Tests that the parsing underlying `string_search` behaves as expected.
        """
        tests = {
            "10": "10.0.0.0/8",
            "10.": "10.0.0.0/8",
            "10.0": "10.0.0.0/16",
            "10.0.0.4": "10.0.0.4/32",
            "10.0.0": "10.0.0.0/24",
            "10.0.0.4/24": "10.0.0.4/32",
            "2001": "2001::/16",
            "2001:": "2001::/16",
            "2001::": "2001::/16",
            "2001:db8": "2001:db8::/32",
            "2001:db8:": "2001:db8::/32",
            "2001:0db8::": "2001:db8::/32",
            "2001:db8:abcd:0012::0/64": "2001:db8:abcd:12::/128",
            "2001:db8::1/65": "2001:db8::1/128",
            "fe80": "fe80::/16",
            "fe80::": "fe80::/16",
            "fe80::46b:a212:1132:3615": "fe80::46b:a212:1132:3615/128",
            "fe80::76:88e9:12aa:334d": "fe80::76:88e9:12aa:334d/128",
        }

        for test, expected in tests.items():
            self.assertEqual(str(self.queryset.parse_network_string(test)), expected)

    def test_string_search(self):
        search_terms = {
            "10": 5,
            "10.0.0.1": 2,
            "10.0.0.1/24": 2,
            "10.0.0.1/25": 2,
            "10.0.0.2": 1,
            "11": 0,
            "2001": 3,
            "2001::": 3,
            "2001:db8": 3,
            "2001:db8:": 3,
            "2001:db8::": 3,
            "2001:db8::1": 1,
            "fe80::": 0,
        }
        for term, cnt in search_terms.items():
            self.assertEqual(self.queryset.string_search(term).count(), cnt)


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

        Prefix.objects.create(prefix=netaddr.IPNetwork("fd78:da4f:e596:c217::/64"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("fd78:da4f:e596:c217::/120"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("fd78:da4f:e596:c217::/122"))

    def test_net_equals(self):
        self.assertEqual(self.queryset.net_equals(netaddr.IPNetwork("192.168.0.0/16")).count(), 1)
        self.assertEqual(self.queryset.net_equals(netaddr.IPNetwork("192.1.0.0/16")).count(), 0)
        self.assertEqual(self.queryset.net_equals(netaddr.IPNetwork("192.1.0.0/32")).count(), 0)

    def test_net_contained(self):
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.0.0.0/8")).count(), 7)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.0.0/16")).count(), 6)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.3.0/24")).count(), 3)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.1.0/24")).count(), 0)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.3.192/28")).count(), 0)
        self.assertEqual(self.queryset.net_contained(netaddr.IPNetwork("192.168.3.192/32")).count(), 0)

    def test_net_contained_or_equal(self):
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.0.0.0/8")).count(), 7)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.0.0/16")).count(), 7)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.3.0/24")).count(), 4)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.1.0/24")).count(), 1)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.3.192/28")).count(), 1)
        self.assertEqual(self.queryset.net_contained_or_equal(netaddr.IPNetwork("192.168.3.192/32")).count(), 0)

    def test_net_contains(self):
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.0.0/8")).count(), 0)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.0.0/16")).count(), 0)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.0/24")).count(), 1)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.192/28")).count(), 2)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.192/30")).count(), 3)
        self.assertEqual(self.queryset.net_contains(netaddr.IPNetwork("192.168.3.192/32")).count(), 3)

    def test_net_contains_or_equals(self):
        self.assertEqual(self.queryset.net_contains_or_equals(netaddr.IPNetwork("192.168.0.0/8")).count(), 0)
        self.assertEqual(self.queryset.net_contains_or_equals(netaddr.IPNetwork("192.168.0.0/16")).count(), 1)
        self.assertEqual(self.queryset.net_contains_or_equals(netaddr.IPNetwork("192.168.3.0/24")).count(), 2)
        self.assertEqual(self.queryset.net_contains_or_equals(netaddr.IPNetwork("192.168.3.192/28")).count(), 3)
        self.assertEqual(self.queryset.net_contains_or_equals(netaddr.IPNetwork("192.168.3.192/30")).count(), 3)
        self.assertEqual(self.queryset.net_contains_or_equals(netaddr.IPNetwork("192.168.3.192/32")).count(), 3)

    def test_annotate_tree(self):
        self.assertEqual(self.queryset.annotate_tree().get(prefix="192.168.0.0/16").parents, 0)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="192.168.0.0/16").children, 6)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="192.168.3.0/24").parents, 1)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="192.168.3.0/24").children, 3)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="192.168.3.224/28").parents, 2)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="192.168.3.224/28").children, 0)

        self.assertEqual(self.queryset.annotate_tree().get(prefix="fd78:da4f:e596:c217::/64").parents, 0)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="fd78:da4f:e596:c217::/64").children, 2)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="fd78:da4f:e596:c217::/120").parents, 1)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="fd78:da4f:e596:c217::/120").children, 1)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="fd78:da4f:e596:c217::/122").parents, 2)
        self.assertEqual(self.queryset.annotate_tree().get(prefix="fd78:da4f:e596:c217::/122").children, 0)

    def test_get_by_prefix(self):
        prefix = self.queryset.net_equals(netaddr.IPNetwork("192.168.0.0/16"))[0]
        self.assertEqual(self.queryset.get(prefix="192.168.0.0/16"), prefix)

    def test_get_by_prefix_fails(self):
        _ = self.queryset.net_equals(netaddr.IPNetwork("192.168.0.0/16"))[0]
        with self.assertRaises(Prefix.DoesNotExist):
            self.queryset.get(prefix="192.168.3.0/16")

    def test_filter_by_prefix(self):
        prefix = self.queryset.net_equals(netaddr.IPNetwork("192.168.0.0/16"))[0]
        self.assertEqual(self.queryset.filter(prefix="192.168.0.0/16")[0], prefix)

    def test_string_search(self):
        # This test case also applies to Aggregate objects.
        search_terms = {
            "192": 7,
            "192.": 7,
            "192.168": 7,
            "192.168.": 7,
            "192.168.1": 2,
            "192.168.1.0": 2,
            "192.168.3": 5,
            "192.168.3.192/26": 3,
            "192.168.0.0/16": 1,
            "11": 0,
            "fd78": 3,
            "fd78::": 3,
            "fd78:da4f": 3,
            "fd78:da4f:": 3,
            "fd78:da4f:e596": 3,
            "fd78:da4f:e596:c217": 3,
            "fd78:da4f:e596:c217::": 3,
            "fd78:da4f:e596:c217::/64": 3,
            "fd78:da4f:e596:c217::/120": 3,
            "fd78:da4f:e596:c217::/122": 3,
            "fe80::": 0,
        }
        for term, cnt in search_terms.items():
            self.assertEqual(self.queryset.string_search(term).count(), cnt)
