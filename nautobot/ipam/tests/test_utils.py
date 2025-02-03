from django.test import TestCase
import netaddr

from nautobot.core.forms.utils import parse_numeric_range
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, Namespace, Prefix, VLAN, VLANGroup
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

    def test_add_available_ipaddresses_ipv4(self):
        prefix = Prefix.objects.create(prefix="22.22.22.0/24", status=Status.objects.get_for_model(Prefix).first())
        ip_status = Status.objects.get_for_model(IPAddress).first()
        # .0 isn't available since this isn't a Pool prefix
        available_1 = (9, "22.22.22.1/24")
        ip_1 = IPAddress.objects.create(address="22.22.22.10/24", status=ip_status)
        available_2 = (10, "22.22.22.11/24")
        ip_2 = IPAddress.objects.create(address="22.22.22.21/24", status=ip_status)
        available_3 = (233, "22.22.22.22/24")
        # .255 isn't available since this isn't a Pool prefix
        self.assertEqual(
            add_available_ipaddresses(prefix=netaddr.IPNetwork(prefix.prefix), ipaddress_list=(ip_1, ip_2)),
            [available_1, ip_1, available_2, ip_2, available_3],
        )

    def test_add_available_ipaddresses_ipv6(self):
        namespace = Namespace.objects.create(name="add_available_ipv6")
        prefix = Prefix.objects.create(
            prefix="::/0", status=Status.objects.get_for_model(Prefix).first(), namespace=namespace
        )
        ip_status = Status.objects.get_for_model(IPAddress).first()
        # .0 is available in IPv6
        available_1 = (10, "::/0")
        ip_1 = IPAddress.objects.create(address="::a/0", status=ip_status, namespace=namespace)
        available_2 = (2**128 - 10 - 10 - 2, "::b/0")
        ip_2 = IPAddress.objects.create(
            address="ffff:ffff:ffff:ffff:ffff:ffff:ffff:fff5/0", status=ip_status, namespace=namespace
        )
        available_3 = (10, "ffff:ffff:ffff:ffff:ffff:ffff:ffff:fff6/0")
        self.assertEqual(
            add_available_ipaddresses(prefix=netaddr.IPNetwork(prefix.prefix), ipaddress_list=(ip_1, ip_2)),
            [available_1, ip_1, available_2, ip_2, available_3],
        )


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
