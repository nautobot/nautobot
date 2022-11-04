from unittest import skipIf

import netaddr
from django.db import connection

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
        cls.parent_covers_second_aggregate = (
            cls.queryset.net_equals(list(cls.parent_network.subnet(cls.exact_network.prefixlen))[0]).exists()
            and cls.queryset.net_equals(list(cls.parent_network.subnet(cls.exact_network.prefixlen))[1]).exists()
        )
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

        cls.queryset.delete()

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

    def test__is_ambiguous_network_string(self):
        self.assertTrue(self.queryset._is_ambiguous_network_string("10"))
        self.assertTrue(self.queryset._is_ambiguous_network_string("123"))
        self.assertFalse(self.queryset._is_ambiguous_network_string("10."))
        self.assertFalse(self.queryset._is_ambiguous_network_string("b2a"))

    def test__safe_parse_network_string(self):
        fallback_ipv4 = netaddr.IPNetwork("0/32")
        fallback_ipv6 = netaddr.IPNetwork("::/128")

        self.assertEqual(self.queryset._safe_parse_network_string("taco", 4), fallback_ipv4)
        self.assertEqual(self.queryset._safe_parse_network_string("taco", 6), fallback_ipv6)

        self.assertEqual(self.queryset._safe_parse_network_string("10.", 4), netaddr.IPNetwork("10.0.0.0/8"))
        self.assertEqual(self.queryset._safe_parse_network_string("10:", 6), netaddr.IPNetwork("10::/16"))

        self.assertEqual(self.queryset._safe_parse_network_string("10.0.0.4", 4), netaddr.IPNetwork("10.0.0.4/32"))
        self.assertEqual(
            self.queryset._safe_parse_network_string("2001:db8:abcd:0012::0", 6),
            netaddr.IPNetwork("2001:db8:abcd:12::/128"),
        )

    def test__check_and_prep_ipv6(self):
        self.assertEqual(self.queryset._check_and_prep_ipv6("10"), "10::")
        self.assertEqual(self.queryset._check_and_prep_ipv6("b2a"), "b2a::")
        self.assertEqual(self.queryset._check_and_prep_ipv6("10:"), "10::")
        self.assertEqual(self.queryset._check_and_prep_ipv6("b2a:"), "b2a::")
        self.assertEqual(self.queryset._check_and_prep_ipv6("10::"), "10::")
        self.assertEqual(self.queryset._check_and_prep_ipv6("b2a::"), "b2a::")

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

    def test_host_family(self):
        self.assertEqual(IPAddress.objects.filter(host__family=4).count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__family=6).count(), 3)

    def test_host_net_host(self):
        self.assertEqual(IPAddress.objects.filter(host__net_host="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__net_host="10.0.0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__net_host="10.0.0.50").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__net_host="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__net_host="2001:db8::5").count(), 0)

    def test_host_net_host_contained(self):
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24").count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.0.0/30").count(), 4)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.0.0/31").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.0.2/31").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.10.0/24").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="2001:db8::/64").count(), 3)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="2222:db8::/64").count(), 0)

    def test_host_net_in(self):
        self.assertEqual(IPAddress.objects.filter(host__net_in=["10.0.0.0/31", "10.0.0.2/31"]).count(), 4)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["10.0.0.0/24"]).count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["172.16.0.0/24"]).count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["2001:db8::/64"]).count(), 3)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["10.0.0.0/24", "2001:db8::/64"]).count(), 8)

        IPAddress.objects.create(address="192.168.0.1/24", vrf=None, tenant=None)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["192.168.0.0/31"]).count(), 1)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_host_exact(self):
        self.assertEqual(IPAddress.objects.filter(host__exact="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__exact="10.0.0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__exact="10.0.0.10").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iexact="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__iexact="10.0.0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iexact="10.0.0.10").count(), 0)

        self.assertEqual(IPAddress.objects.filter(host__exact="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__exact="2001:db8::5").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iexact="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iexact="2001:db8::5").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_host_endswith(self):
        self.assertEqual(IPAddress.objects.filter(host__endswith="0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__endswith="0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__endswith="0.50").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="0.50").count(), 0)

        self.assertEqual(IPAddress.objects.filter(host__endswith="8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__endswith="8::5").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="8::5").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_host_startswith(self):
        self.assertEqual(IPAddress.objects.filter(host__startswith="10.0.0.").count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__startswith="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__startswith="10.50.0.").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="10.0.0.").count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="10.50.0.").count(), 0)

        self.assertEqual(IPAddress.objects.filter(host__startswith="2001:db8::").count(), 3)
        self.assertEqual(IPAddress.objects.filter(host__startswith="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__startswith="2001:db8::5").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="2001:db8::").count(), 3)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="2001:db8::5").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_host_regex(self):
        self.assertEqual(IPAddress.objects.filter(host__regex=r"10\.(.*)\.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__regex=r"10\.(.*)\.4").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__regex=r"10\.(.*)\.50").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"10\.(.*)\.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"10\.(.*)\.4").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"10\.(.*)\.50").count(), 0)

        self.assertEqual(IPAddress.objects.filter(host__regex=r"2001(.*)1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__regex=r"2001(.*)5").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"2001(.*)1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"2001(.*)5").count(), 0)


class PrefixQuerysetTestCase(TestCase):
    queryset = Prefix.objects.all()

    @classmethod
    def setUpTestData(cls):

        cls.queryset.delete()

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

    def test_network_family(self):
        self.assertEqual(Prefix.objects.filter(network__family=4).count(), 7)
        self.assertEqual(Prefix.objects.filter(network__family=6).count(), 3)

    def test_network_net_equals(self):
        self.assertEqual(Prefix.objects.filter(network__net_equals="192.168.0.0/16").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_equals="192.1.0.0/16").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_equals="192.1.0.0/28").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_equals="192.1.0.0/32").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_equals="fd78:da4f:e596:c217::/64").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_equals="fd78:da4f:e596:c218::/122").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_equals="fd78:da4f:e596:c218::/64").count(), 0)

    def test_network_net_contained(self):
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.0.0.0/8").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.0.0/16").count(), 6)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.3.0/24").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.1.0/24").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.3.192/28").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.3.192/32").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__net_contained="fd78:da4f:e596:c217::/64").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contained="fd78:da4f:e596:c217::/120").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contained="fd78:da4f:e596:c218::/64").count(), 0)

    def test_network_net_contained_or_equal(self):
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.0.0.0/8").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.0.0/16").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.3.0/24").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.1.0/24").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.3.192/28").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.3.192/32").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="fd78:da4f:e596:c217::/64").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="fd78:da4f:e596:c217::/120").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="fd78:da4f:e596:c218::/64").count(), 0)

    def test_network_net_contains(self):
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.0.0.0/8").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.0.0/16").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.3.0/24").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.3.192/28").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.3.192/30").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.3.192/32").count(), 3)

        self.assertEqual(Prefix.objects.filter(network__net_contains="fd78:da4f:e596:c217::/64").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contains="fd78:da4f:e596:c217::/120").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contains="fd78:da4f:e596:c217::/122").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contains="fd78:da4f:e596:c218::/64").count(), 0)

    def test_network_net_contains_or_equals(self):
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.0.0.0/8").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.0.0/16").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.3.0/24").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.3.192/28").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.3.192/30").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.3.192/32").count(), 3)

        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="fd78:da4f:e596:c217::/64").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="fd78:da4f:e596:c217::/120").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="fd78:da4f:e596:c217::/122").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="fd78:da4f:e596:c218::/64").count(), 0)

    def test_network_get_by_prefix(self):
        prefix = Prefix.objects.filter(network__net_equals="192.168.0.0/16")[0]
        self.assertEqual(Prefix.objects.get(prefix="192.168.0.0/16"), prefix)

    def test_network_get_by_prefix_fails(self):
        _ = Prefix.objects.filter(network__net_equals="192.168.0.0/16")[0]
        with self.assertRaises(Prefix.DoesNotExist):
            Prefix.objects.get(prefix="192.168.3.0/16")

    def test_network_filter_by_prefix(self):
        prefix = Prefix.objects.filter(network__net_equals="192.168.0.0/16")[0]
        self.assertEqual(Prefix.objects.filter(prefix="192.168.0.0/16")[0], prefix)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_network_exact(self):
        self.assertEqual(Prefix.objects.filter(network__exact="192.168.0.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__exact="192.168.1.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__exact="192.168.50.0").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iexact="192.168.0.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__iexact="192.168.1.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__iexact="192.168.50.0").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__exact="fd78:da4f:e596:c217::").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__exact="fd78:da4f:e596:c218::").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iexact="fd78:da4f:e596:c217::").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__iexact="fd78:da4f:e596:c218::").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_network_endswith(self):
        self.assertEqual(Prefix.objects.filter(network__endswith=".224").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__endswith=".0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__endswith="0.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__iendswith=".224").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__iendswith=".0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__iendswith="0.0").count(), 1)

        self.assertEqual(Prefix.objects.filter(network__endswith="c217::").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__endswith="c218::").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iendswith="c217::").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__iendswith="c218::").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_network_startswith(self):
        self.assertEqual(Prefix.objects.filter(network__startswith="192.").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__startswith="192.168.3.").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__startswith="192.168.3.2").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__startswith="192.168.50").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__istartswith="192.").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__istartswith="192.168.3.").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__istartswith="192.168.3.2").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__istartswith="192.168.50").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__startswith="fd78:").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__startswith="fd79:").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__istartswith="fd78:").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__istartswith="fd79:").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_network_regex(self):
        self.assertEqual(Prefix.objects.filter(network__regex=r"192\.(.*)\.0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__regex=r"192\.\d+(.*)\.0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__regex=r"10\.\d+(.*)\.0").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"192\.(.*)\.0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"192\.\d+(.*)\.0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"10\.\d+(.*)\.0").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__regex=r"fd78(.*)c217(.*)").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__regex=r"fd78(.*)c218(.*)").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"fd78(.*)c217(.*)").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"fd78(.*)c218(.*)").count(), 0)
