import netaddr

from nautobot.core.forms.utils import parse_numeric_range
from nautobot.core.testing import TestCase
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, IPAddressRange, Namespace, Prefix, VLAN, VLANGroup
from nautobot.ipam.utils import add_available_ipaddresses, add_available_vlans


class AddAvailableVlansTest(TestCase):
    """Tests for add_available_vlans()."""

    def test_add_available_vlans(self):
        vlan_group = VLANGroup.objects.create(name="VLAN Group 1", range="100-105,110-112,115")
        status = Status.objects.get_for_model(VLAN).first()
        vlan_100 = {"vid": 100, "available": 2, "range": "100-101"}
        vlan_102 = VLAN.objects.create(name="VLAN 102", vid=102, vlan_group=vlan_group, status=status)
        vlan_103 = VLAN.objects.create(name="VLAN 103", vid=103, vlan_group=vlan_group, status=status)
        vlan_104 = {"vid": 104, "available": 2, "range": "104-105"}
        vlan_110 = VLAN.objects.create(name="VLAN 110", vid=110, vlan_group=vlan_group, status=status)
        vlan_111 = VLAN.objects.create(name="VLAN 111", vid=111, vlan_group=vlan_group, status=status)
        vlan_112 = {"vid": 112, "available": 1, "range": "112"}
        vlan_115 = VLAN.objects.create(name="VLAN 115", vid=115, vlan_group=vlan_group, status=status)

        self.assertEqual(
            list(add_available_vlans(vlan_group=vlan_group, vlans=vlan_group.vlans.all())),
            [vlan_100, vlan_102, vlan_103, vlan_104, vlan_110, vlan_111, vlan_112, vlan_115],
        )


class AddAvailableIPsTest(TestCase):
    """Tests for add_available_ipaddresses()."""

    def setUp(self):
        self.namespace = Namespace.objects.create(name="add_available_ranges")
        self.prefix_status = Status.objects.get_for_model(Prefix).first()
        self.ip_status = Status.objects.get_for_model(IPAddress).first()
        self.range_status = Status.objects.get_for_model(IPAddressRange).first()

    def test_add_available_ipaddresses_ipv4(self):
        prefix = Prefix.objects.create(prefix="22.22.22.0/24", status=self.prefix_status)
        # .0 isn't available since this isn't a Pool prefix
        available_1 = (9, "22.22.22.1/24")
        ip_1 = IPAddress.objects.create(address="22.22.22.10/24", status=self.ip_status)
        available_2 = (10, "22.22.22.11/24")
        ip_2 = IPAddress.objects.create(address="22.22.22.21/24", status=self.ip_status)
        available_3 = (233, "22.22.22.22/24")
        # .255 isn't available since this isn't a Pool prefix
        self.assertEqual(
            add_available_ipaddresses(prefix=netaddr.IPNetwork(prefix.prefix), ipaddress_list=(ip_1, ip_2)),
            [available_1, ip_1, available_2, ip_2, available_3],
        )

    def test_add_available_ipaddresses_ipv6(self):
        namespace = Namespace.objects.create(name="add_available_ipv6")
        prefix = Prefix.objects.create(prefix="::/0", status=self.prefix_status, namespace=namespace)
        # .0 is available in IPv6
        available_1 = (10, "::/0")
        ip_1 = IPAddress.objects.create(address="::a/0", status=self.ip_status, namespace=namespace)
        available_2 = (2**128 - 10 - 10 - 2, "::b/0")
        ip_2 = IPAddress.objects.create(
            address="ffff:ffff:ffff:ffff:ffff:ffff:ffff:fff5/0", status=self.ip_status, namespace=namespace
        )
        available_3 = (10, "ffff:ffff:ffff:ffff:ffff:ffff:ffff:fff6/0")
        self.assertEqual(
            add_available_ipaddresses(prefix=netaddr.IPNetwork(prefix.prefix), ipaddress_list=(ip_1, ip_2)),
            [available_1, ip_1, available_2, ip_2, available_3],
        )

    def test_non_exclusive_range_keeps_interior_available(self):
        """A non-exclusive range shows its row plus the available space inside it, nested."""
        prefix = Prefix.objects.create(prefix="10.0.0.0/24", namespace=self.namespace, status=self.prefix_status)
        ip_12 = IPAddress.objects.create(address="10.0.0.12/24", namespace=self.namespace, status=self.ip_status)
        ip_range = IPAddressRange.objects.create(
            start_address="10.0.0.10",
            end_address="10.0.0.15",
            namespace=self.namespace,
            status=self.range_status,
        )

        result = add_available_ipaddresses(
            prefix=netaddr.IPNetwork(prefix.prefix), ipaddress_list=(ip_12,), ip_ranges=[ip_range]
        )

        self.assertEqual(
            result,
            [
                (9, "10.0.0.1/24"),  # outer gap before the range
                ip_range,  # range row
                (2, "10.0.0.10/24", ip_range),  # nested available: .10-.11
                ip_12,  # address inside the range
                (3, "10.0.0.13/24", ip_range),  # nested available: .13-.15
                (239, "10.0.0.16/24"),  # trailing outer gap
            ],
        )
        self.assertIs(ip_12.containing_ip_range, ip_range)
        # a nested available block follows .12 in the same range -> draws ├─
        self.assertTrue(ip_12.range_has_next_sibling)

    def test_last_child_in_range_has_no_sibling(self):
        """The last child of a range draws └─: nothing nested follows it."""
        prefix = Prefix.objects.create(prefix="10.0.0.0/24", namespace=self.namespace, status=self.prefix_status)
        ip_12 = IPAddress.objects.create(address="10.0.0.12/24", namespace=self.namespace, status=self.ip_status)
        ip_range = IPAddressRange.objects.create(
            start_address="10.0.0.10",
            end_address="10.0.0.12",  # .12 is the final host of the range
            namespace=self.namespace,
            status=self.range_status,
        )

        result = add_available_ipaddresses(
            prefix=netaddr.IPNetwork(prefix.prefix), ipaddress_list=(ip_12,), ip_ranges=[ip_range]
        )

        self.assertEqual(
            result,
            [
                (9, "10.0.0.1/24"),
                ip_range,
                (2, "10.0.0.10/24", ip_range),
                ip_12,
                (242, "10.0.0.13/24"),  # trailing outer gap (NOT part of the range)
            ],
        )
        self.assertFalse(ip_12.range_has_next_sibling)

    def test_exclusive_range_consumes_its_span(self):
        """An exclusive range shows only its row; its span is removed from the pool (no interior)."""
        prefix = Prefix.objects.create(prefix="10.0.0.0/24", namespace=self.namespace, status=self.prefix_status)
        ip_range = IPAddressRange.objects.create(
            start_address="10.0.0.10",
            end_address="10.0.0.15",
            namespace=self.namespace,
            status=self.range_status,
            is_exclusive=True,
        )

        result = add_available_ipaddresses(
            prefix=netaddr.IPNetwork(prefix.prefix), ipaddress_list=(), ip_ranges=[ip_range]
        )

        self.assertEqual(
            result,
            [
                (9, "10.0.0.1/24"),
                ip_range,
                (239, "10.0.0.16/24"),
            ],
        )

    def test_show_available_false_hides_gaps_only(self):
        """show_available=False drops the available-gap rows but keeps ranges and addresses."""
        prefix = Prefix.objects.create(prefix="10.0.0.0/24", namespace=self.namespace, status=self.prefix_status)
        ip_12 = IPAddress.objects.create(address="10.0.0.12/24", namespace=self.namespace, status=self.ip_status)
        ip_range = IPAddressRange.objects.create(
            start_address="10.0.0.10",
            end_address="10.0.0.15",
            namespace=self.namespace,
            status=self.range_status,
        )

        result = add_available_ipaddresses(
            prefix=netaddr.IPNetwork(prefix.prefix),
            ipaddress_list=(ip_12,),
            ip_ranges=[ip_range],
            show_available=False,
        )

        self.assertEqual(result, [ip_range, ip_12])
        self.assertIs(ip_12.containing_ip_range, ip_range)

    def test_is_pool_includes_network_and_broadcast(self):
        """A pool prefix offers the whole range, including .0 and .255 (no DB objects needed)."""
        result = add_available_ipaddresses(prefix=netaddr.IPNetwork("10.0.0.0/24"), ipaddress_list=(), is_pool=True)

        self.assertEqual(result, [(256, "10.0.0.0/24")])

    def test_free_address_and_range_interleave(self):
        """A free address and a range are ordered together by position, each with its own gaps."""
        prefix = Prefix.objects.create(prefix="10.0.0.0/24", namespace=self.namespace, status=self.prefix_status)
        ip_5 = IPAddress.objects.create(address="10.0.0.5/24", namespace=self.namespace, status=self.ip_status)
        ip_12 = IPAddress.objects.create(address="10.0.0.12/24", namespace=self.namespace, status=self.ip_status)
        ip_range = IPAddressRange.objects.create(
            start_address="10.0.0.10",
            end_address="10.0.0.15",
            namespace=self.namespace,
            status=self.range_status,
        )

        result = add_available_ipaddresses(
            prefix=netaddr.IPNetwork(prefix.prefix), ipaddress_list=(ip_5, ip_12), ip_ranges=[ip_range]
        )

        self.assertEqual(
            result,
            [
                (4, "10.0.0.1/24"),  # gap before the free address
                ip_5,
                (4, "10.0.0.6/24"),  # gap between the free address and the range
                ip_range,
                (2, "10.0.0.10/24", ip_range),
                ip_12,
                (3, "10.0.0.13/24", ip_range),
                (239, "10.0.0.16/24"),
            ],
        )
        self.assertIsNone(ip_5.containing_ip_range)
        self.assertIs(ip_12.containing_ip_range, ip_range)


class ParseNumericRangeTest(TestCase):
    """Tests for add_available_vlans()."""

    def test_parse(self):
        self.assertEqual(parse_numeric_range(input_string="5"), [5])
        self.assertEqual(parse_numeric_range(input_string="5-5"), [5])
        self.assertEqual(parse_numeric_range(input_string="5-5,5,5"), [5])
        self.assertEqual(parse_numeric_range(input_string="1-5"), [1, 2, 3, 4, 5])
        self.assertEqual(parse_numeric_range(input_string="1,2,3,4,5"), [1, 2, 3, 4, 5])
        self.assertEqual(parse_numeric_range(input_string="5,4,3,1,2"), [1, 2, 3, 4, 5])
        self.assertEqual(parse_numeric_range(input_string="1-5,10"), [1, 2, 3, 4, 5, 10])
        self.assertEqual(parse_numeric_range(input_string="1,5,10-11"), [1, 5, 10, 11])
        self.assertEqual(parse_numeric_range(input_string="10-11,1,5"), [1, 5, 10, 11])
        self.assertEqual(parse_numeric_range(input_string="a", base=16), [10])
        self.assertEqual(parse_numeric_range(input_string="a,b", base=16), [10, 11])
        self.assertEqual(parse_numeric_range(input_string="9-c,f", base=16), [9, 10, 11, 12, 15])
        self.assertEqual(parse_numeric_range(input_string="15-19", base=16), [21, 22, 23, 24, 25])
        self.assertEqual(parse_numeric_range(input_string="fa-ff", base=16), [250, 251, 252, 253, 254, 255])

    def test_invalid_input(self):
        invalid_inputs = [
            [1, 2, 3],
            None,
            1,
            "",
            "3-",
        ]

        for x in invalid_inputs:
            with self.assertRaises(TypeError) as exc:
                parse_numeric_range(input_string=x)
            self.assertEqual(str(exc.exception), "Input value must be a string using a range format.")
