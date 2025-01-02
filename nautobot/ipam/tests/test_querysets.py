import re
from unittest import skipIf

from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
import netaddr

from nautobot.core.testing import TestCase
from nautobot.extras.models import Status
from nautobot.ipam import choices
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.users.models import ObjectPermission


class IPAddressQuerySet(TestCase):
    queryset = IPAddress.objects.all()

    @classmethod
    def setUpTestData(cls):
        cls.queryset.delete()
        cls.prefix_status = Status.objects.get_for_model(Prefix).first()
        cls.ipaddr_status = Status.objects.get_for_model(IPAddress).first()
        cls.namespace = Namespace.objects.create(name="IP Address Queryset Test")
        cls.namespace2 = Namespace.objects.create(name="IP Address Queryset Test 2")
        cls.prefix4 = Prefix.objects.create(prefix="10.0.0.0/8", namespace=cls.namespace, status=cls.prefix_status)
        cls.prefix4_2 = Prefix.objects.create(prefix="10.0.0.0/8", namespace=cls.namespace2, status=cls.prefix_status)
        cls.prefix6 = Prefix.objects.create(prefix="2001:db8::/64", namespace=cls.namespace, status=cls.prefix_status)
        cls.ips = {
            "10.0.0.1/24": IPAddress.objects.create(
                address="10.0.0.1/24", namespace=cls.namespace, tenant=None, status=cls.ipaddr_status
            ),
            "10.0.0.1/25": IPAddress.objects.create(
                address="10.0.0.1/25", namespace=cls.namespace2, tenant=None, status=cls.ipaddr_status
            ),
            "10.0.0.2/24": IPAddress.objects.create(
                address="10.0.0.2/24", namespace=cls.namespace, tenant=None, status=cls.ipaddr_status
            ),
            "10.0.0.3/24": IPAddress.objects.create(
                address="10.0.0.3/24", namespace=cls.namespace, tenant=None, status=cls.ipaddr_status
            ),
            "10.0.0.4/24": IPAddress.objects.create(
                address="10.0.0.4/24", namespace=cls.namespace, tenant=None, status=cls.ipaddr_status
            ),
            "2001:db8::1/64": IPAddress.objects.create(
                address="2001:db8::1/64", namespace=cls.namespace, tenant=None, status=cls.ipaddr_status
            ),
            "2001:db8::2/64": IPAddress.objects.create(
                address="2001:db8::2/64", namespace=cls.namespace, tenant=None, status=cls.ipaddr_status
            ),
            "2001:db8::3/64": IPAddress.objects.create(
                address="2001:db8::3/64", namespace=cls.namespace, tenant=None, status=cls.ipaddr_status
            ),
        }

    def test_net_host_contained(self):
        self.assertQuerysetEqualAndNotEmpty(
            self.queryset.net_host_contained(netaddr.IPNetwork("10.0.0.0/24")),
            [instance for ip, instance in self.ips.items() if "10.0" in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.queryset.net_host_contained(netaddr.IPNetwork("10.0.0.0/30")),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.0\.0\.[0-3]/", ip)],
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.queryset.net_host_contained(netaddr.IPNetwork("10.0.0.0/31")),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.0\.0\.[0-1]/", ip)],
        )
        self.assertQuerysetEqual(
            self.queryset.net_host_contained(netaddr.IPNetwork("10.0.10.0/24")),
            [],
        )

    def test_net_in(self):
        args = ["10.0.0.1/24"]
        self.assertQuerysetEqualAndNotEmpty(self.queryset.net_in(args), [self.ips["10.0.0.1/24"]])

        args = ["10.0.0.1"]
        self.assertQuerysetEqualAndNotEmpty(
            self.queryset.net_in(args), [self.ips["10.0.0.1/24"], self.ips["10.0.0.1/25"]]
        )

        args = ["10.0.0.1/24", "10.0.0.1/25"]
        self.assertQuerysetEqualAndNotEmpty(self.queryset.net_in(args), [self.ips[arg] for arg in args])

    def test_get_by_address(self):
        address = self.queryset.net_in(["10.0.0.1/24"])[0]
        self.assertEqual(self.queryset.get(address="10.0.0.1/24"), address)

    def test_filter_by_address(self):
        address = self.queryset.net_in(["10.0.0.1/24"])[0]
        self.assertEqual(self.queryset.filter(address="10.0.0.1/24")[0], address)
        self.assertEqual(self.queryset.count() - 1, self.queryset.exclude(address="10.0.0.1/24").count())
        self.assertNotIn(address, self.queryset.exclude(address="10.0.0.1/24"))

    def test__is_ambiguous_network_string(self):
        self.assertTrue(self.queryset._is_ambiguous_network_string("10"))
        self.assertTrue(self.queryset._is_ambiguous_network_string("123"))
        self.assertFalse(self.queryset._is_ambiguous_network_string("10."))
        self.assertFalse(self.queryset._is_ambiguous_network_string("b2a"))

    def test__safe_parse_network_string(self):
        fallback_ipv4 = netaddr.IPNetwork("0.0.0.0/32")
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
            # TODO refactor to be able to use assertQuerysetEqualAndNotEmpty()
            self.assertEqual(self.queryset.string_search(term).count(), cnt)

    def test_host_family(self):
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__family=4),
            [instance for ip, instance in self.ips.items() if "." in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__family=6),
            [instance for ip, instance in self.ips.items() if ":" in ip],
        )

    def test_host_net_host(self):
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_host="10.0.0.1"),
            [self.ips["10.0.0.1/24"], self.ips["10.0.0.1/25"]],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_host="10.0.0.2"),
            [self.ips["10.0.0.2/24"]],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__net_host="10.0.0.50"), [])
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_host="2001:db8::1"),
            [self.ips["2001:db8::1/64"]],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__net_host="2001:db8::5"), [])
        # https://github.com/nautobot/nautobot/issues/3480
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__net_host="10.0.0.1"),
            [self.ips["10.0.0.1/24"], self.ips["10.0.0.1/25"]],
        )

    def test_host_net_host_contained(self):
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24"),
            [instance for ip, instance in self.ips.items() if "10.0.0" in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_host_contained="10.0.0.0/30"),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.0\.0\.[0-3]/", ip)],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_host_contained="10.0.0.0/31"),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.0\.0\.[0-1]/", ip)],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_host_contained="10.0.0.2/31"),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.0\.0\.[2-3]/", ip)],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__net_host_contained="10.0.10.0/24"), [])
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_host_contained="2001:db8::/64"),
            [instance for ip, instance in self.ips.items() if "2001:db8:" in ip],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__net_host_contained="2222:db8::/64"), [])
        # https://github.com/nautobot/nautobot/issues/3480
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__net_host_contained="10.0.0.0/24"),
            [instance for ip, instance in self.ips.items() if "10.0.0" in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__net_host_contained="2001:db8::/64"),
            [instance for ip, instance in self.ips.items() if "2001:db8:" in ip],
        )

    def test_host_net_in(self):
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_in=["10.0.0.0/31", "10.0.0.2/31"]),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.0\.0\.[0-3]/", ip)],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_in=["10.0.0.0/24"]),
            [instance for ip, instance in self.ips.items() if "10.0.0" in ip],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__net_in=["172.16.0.0/24"]), [])
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_in=["2001:db8::/64"]),
            [instance for ip, instance in self.ips.items() if "2001:db8::" in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_in=["10.0.0.0/24", "2001:db8::/64"]),
            self.ips.values(),
        )

        Prefix.objects.create(prefix="192.168.0.0/24", namespace=self.namespace, status=self.prefix_status)
        extra_ip = IPAddress.objects.create(
            address="192.168.0.1/24", namespace=self.namespace, tenant=None, status=self.ipaddr_status
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__net_in=["192.168.0.0/31"]),
            [extra_ip],
        )

        # https://github.com/nautobot/nautobot/issues/3480
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__net_in=["10.0.0.0/24"]),
            [instance for ip, instance in self.ips.items() if "10.0.0" in ip],
        )

    def test_lookup_not_ambiguous(self):
        """Check for issues like https://github.com/nautobot/nautobot/issues/5166."""
        obj_perm = ObjectPermission.objects.create(name="Test Permission", constraints={}, actions=["view"])
        obj_perm.object_types.add(ContentType.objects.get_for_model(IPAddress))
        obj_perm.users.add(self.user)
        queryset = IPAddress.objects.select_related("parent", "nat_inside", "status")

        for permission_constraint in (
            {"host__family": 4},
            {"host__net_host": "10.0.0.1"},
            {"host__net_host_contained": "10.0.0.0/24"},
            {"host__net_in": ["10.0.0.0/24"]},
        ):
            with self.subTest(permission_type=next(iter(permission_constraint.keys()))):
                try:
                    with transaction.atomic():
                        obj_perm.constraints = permission_constraint
                        obj_perm.save()
                        list(queryset.restrict(self.user, "view"))
                finally:
                    delattr(self.user, "_object_perm_cache")

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_host_exact(self):
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__exact="10.0.0.1"),
            [instance for ip, instance in self.ips.items() if "10.0.0.1/" in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__exact="10.0.0.2"),
            [self.ips["10.0.0.2/24"]],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__exact="10.0.0.10"), [])
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__iexact="10.0.0.1"),
            [instance for ip, instance in self.ips.items() if "10.0.0.1/" in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__iexact="10.0.0.2"),
            [self.ips["10.0.0.2/24"]],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__iexact="10.0.0.10"), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__exact="2001:db8::1"),
            [self.ips["2001:db8::1/64"]],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__exact="2001:db8::5"), [])
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__iexact="2001:db8::1"),
            [self.ips["2001:db8::1/64"]],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__iexact="2001:db8::5"), [])

        # https://github.com/nautobot/nautobot/issues/3480
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__exact="10.0.0.1"),
            [instance for ip, instance in self.ips.items() if "10.0.0.1/" in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__iexact="2001:db8::1"),
            [self.ips["2001:db8::1/64"]],
        )

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_host_endswith(self):
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__endswith="0.2"),
            [instance for ip, instance in self.ips.items() if "0.2/" in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__endswith="0.1"),
            [instance for ip, instance in self.ips.items() if "0.1/" in ip],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__endswith="0.50"), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__iendswith="0.2"),
            [instance for ip, instance in self.ips.items() if "0.2/" in ip],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__iendswith="0.1"),
            [instance for ip, instance in self.ips.items() if "0.1/" in ip],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__iendswith="0.50"), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__endswith="8::1"),
            [instance for ip, instance in self.ips.items() if "8::1/" in ip],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__endswith="8::5"), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__iendswith="8::1"),
            [instance for ip, instance in self.ips.items() if "8::1/" in ip],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__iendswith="8::5"), [])

        # https://github.com/nautobot/nautobot/issues/3480
        self.assertEqual(IPAddress.objects.select_related("nat_inside").filter(host__endswith="0.1").count(), 2)
        self.assertEqual(IPAddress.objects.select_related("nat_inside").filter(host__iendswith="8::1").count(), 1)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_host_startswith(self):
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__startswith="10.0.0."),
            [instance for ip, instance in self.ips.items() if ip.startswith("10.0.0.")],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__startswith="10.0.0.1"),
            [instance for ip, instance in self.ips.items() if ip.startswith("10.0.0.1")],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__startswith="10.50.0."), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__istartswith="10.0.0."),
            [instance for ip, instance in self.ips.items() if ip.startswith("10.0.0.")],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__istartswith="10.0.0.1"),
            [instance for ip, instance in self.ips.items() if ip.startswith("10.0.0.1")],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__istartswith="10.50.0."), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__startswith="2001:db8::"),
            [instance for ip, instance in self.ips.items() if ip.startswith("2001:db8::")],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__startswith="2001:db8::1"),
            [instance for ip, instance in self.ips.items() if ip.startswith("2001:db8::1")],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__startswith="2001:db8::5"), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__istartswith="2001:db8::"),
            [instance for ip, instance in self.ips.items() if ip.startswith("2001:db8::")],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__istartswith="2001:db8::1"),
            [instance for ip, instance in self.ips.items() if ip.startswith("2001:db8::1")],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__istartswith="2001:db8::5"), [])

        # https://github.com/nautobot/nautobot/issues/3480
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__startswith="10.0"),
            [instance for ip, instance in self.ips.items() if ip.startswith("10.0")],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__istartswith="2001:db8::"),
            [instance for ip, instance in self.ips.items() if ip.startswith("2001:db8::")],
        )

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_host_regex(self):
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__regex=r"10\.(.*)\.1"),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.(.*)\.1", ip)],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__regex=r"10\.(.*)\.4"),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.(.*)\.4", ip)],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__regex=r"10\.(.*)\.50"), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__iregex=r"10\.(.*)\.1"),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.(.*)\.1", ip)],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__iregex=r"10\.(.*)\.4"),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.(.*)\.4", ip)],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__iregex=r"10\.(.*)\.50"), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__regex=r"2001(.*)1"),
            [instance for ip, instance in self.ips.items() if re.match(r"2001(.*)1", ip)],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__regex=r"2001(.*)5"), [])

        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.filter(host__iregex=r"2001(.*)1"),
            [instance for ip, instance in self.ips.items() if re.match(r"2001(.*)1", ip)],
        )
        self.assertQuerysetEqual(IPAddress.objects.filter(host__iregex=r"2001(.*)5"), [])

        # https://github.com/nautobot/nautobot/issues/3480
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__regex=r"10\.(.*)\.1"),
            [instance for ip, instance in self.ips.items() if re.match(r"10\.(.*)\.1", ip)],
        )
        self.assertQuerysetEqualAndNotEmpty(
            IPAddress.objects.select_related("nat_inside").filter(host__iregex=r"2001(.*)1"),
            [instance for ip, instance in self.ips.items() if re.match(r"2001(.*)1", ip)],
        )

    def test_get_or_create(self):
        # https://github.com/nautobot/nautobot/issues/6676
        ip_obj, created = IPAddress.objects.update_or_create(
            defaults={
                "status": self.ipaddr_status,
            },
            host="10.0.0.1",
            mask_length="24",
            namespace=self.namespace,
        )
        self.assertFalse(created)
        self.assertEqual(str(ip_obj.address), "10.0.0.1/24")
        self.assertEqual(ip_obj.parent.namespace, self.namespace)


class PrefixQuerysetTestCase(TestCase):
    queryset = Prefix.objects.all()

    @classmethod
    def setUpTestData(cls):
        # With advent of `Prefix.parent`, Prefixes can't just be bulk deleted without clearing their
        # `parent` first in an `update()` query which doesn't call `save()` or `fire `(pre|post)_save` signals.
        IPAddress.objects.all().delete()
        cls.queryset.update(parent=None)
        cls.queryset.delete()

        cls.status = Status.objects.get_for_model(Prefix).first()
        Prefix.objects.create(
            prefix=netaddr.IPNetwork("192.168.0.0/16"), status=cls.status, type=choices.PrefixTypeChoices.TYPE_CONTAINER
        )

        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.1.0/24"), status=cls.status)
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.2.0/24"), status=cls.status)
        Prefix.objects.create(
            prefix=netaddr.IPNetwork("192.168.3.0/24"), status=cls.status, type=choices.PrefixTypeChoices.TYPE_CONTAINER
        )

        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.192/28"), status=cls.status)
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.208/28"), status=cls.status)
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.224/28"), status=cls.status)

        Prefix.objects.create(
            prefix=netaddr.IPNetwork("fd78:da4f:e596:c217::/64"),
            status=cls.status,
            type=choices.PrefixTypeChoices.TYPE_CONTAINER,
        )
        Prefix.objects.create(
            prefix=netaddr.IPNetwork("fd78:da4f:e596:c217::/120"),
            status=cls.status,
            type=choices.PrefixTypeChoices.TYPE_CONTAINER,
        )
        Prefix.objects.create(prefix=netaddr.IPNetwork("fd78:da4f:e596:c217::/122"), status=cls.status)

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
        self.assertEqual(self.queryset.count() - 1, self.queryset.exclude(prefix="192.168.0.0/16").count())
        self.assertNotIn(prefix, self.queryset.exclude(prefix="192.168.0.0/16"))

    def test_string_search(self):
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

    def test_lookup_not_ambiguous(self):
        """Check for issues like https://github.com/nautobot/nautobot/issues/5166."""
        obj_perm = ObjectPermission.objects.create(name="Test Permission", constraints={}, actions=["view"])
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))
        obj_perm.users.add(self.user)
        queryset = Prefix.objects.select_related("parent", "rir", "role", "status", "namespace")

        for permission_constraint in (
            {"network__family": 4},
            {"network__net_equals": "192.168.0.0/16"},
            {"network__net_contained": "192.0.0.0/8"},
            {"network__net_contained_or_equal": "192.0.0.0/8"},
            {"network__net_contains": "192.168.3.192/32"},
            {"network__net_contains_or_equals": "192.168.3.192/32"},
        ):
            with self.subTest(permission_type=next(iter(permission_constraint.keys()))):
                try:
                    with transaction.atomic():
                        obj_perm.constraints = permission_constraint
                        obj_perm.save()
                        list(queryset.restrict(self.user, "view"))
                finally:
                    delattr(self.user, "_object_perm_cache")

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

    def test_get_closest_parent(self):
        """Test the PrefixQuerySet.get_closest_parent() method."""
        namespace = Namespace.objects.create(name="test_get_closest_parent")

        container = netaddr.IPNetwork("10.0.0.0/24")
        Prefix.objects.create(
            prefix=container,
            type=choices.PrefixTypeChoices.TYPE_CONTAINER,
            namespace=namespace,
            status=self.status,
        )

        # create prefixes with /25 through /32 lengths (10.0.0.1/32, 10.0.0.2/31, 10.0.0.4/30, etc.)
        for prefix_length in range(25, 33):
            network = list(container.subnet(prefix_length))[1]
            Prefix.objects.create(
                prefix=network,
                type=choices.PrefixTypeChoices.TYPE_NETWORK,
                namespace=namespace,
                status=self.status,
            )

        for last_octet in range(1, 255):
            ip = netaddr.IPAddress(f"10.0.0.{last_octet}")
            expected_prefix_length = 33 - len(bin(last_octet)[2:])  # [1] = 32, [2,3] = 31, [4,5,6,7] = 30, etc.
            with self.subTest(ip=ip, expected_prefix_length=expected_prefix_length):
                closest_parent = Prefix.objects.filter(namespace=namespace).get_closest_parent(ip, include_self=True)
                expected_parent = list(container.subnet(expected_prefix_length))[1]
                self.assertEqual(closest_parent.prefix, expected_parent)
                self.assertEqual(
                    closest_parent,
                    Prefix.objects.filter(
                        network__lte=ip.value,
                        broadcast__gte=ip.value,
                        namespace=namespace,
                    )
                    .order_by("-prefix_length")
                    .first(),
                )
