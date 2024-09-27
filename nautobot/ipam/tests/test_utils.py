from django.test import TestCase

from nautobot.core.forms.utils import parse_numeric_range
from nautobot.extras.models import Status
from nautobot.ipam.models import VLAN, VLANGroup
from nautobot.ipam.utils import add_available_vlans


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
