from django import forms
from django.test import TestCase
from unittest import mock
from netaddr import IPNetwork

from nautobot.ipam.forms import IPAddressCSVForm, ServiceForm
from nautobot.ipam.models import IPAddress, Prefix
from nautobot.utilities.forms.fields import CSVDataField, DynamicModelMultipleChoiceField, NumericArrayField
from nautobot.utilities.forms.utils import (
    expand_alphanumeric_pattern,
    expand_ipaddress_pattern,
)
from nautobot.utilities.forms.forms import AddressFieldMixin, PrefixFieldMixin


class ExpandIPAddress(TestCase):
    """
    Validate the operation of expand_ipaddress_pattern().
    """

    def test_ipv4_range(self):
        input = "1.2.3.[9-10]/32"
        output = sorted(
            [
                "1.2.3.9/32",
                "1.2.3.10/32",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 4)), output)

    def test_ipv4_set(self):
        input = "1.2.3.[4,44]/32"
        output = sorted(
            [
                "1.2.3.4/32",
                "1.2.3.44/32",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 4)), output)

    def test_ipv4_multiple_ranges(self):
        input = "1.[9-10].3.[9-11]/32"
        output = sorted(
            [
                "1.9.3.9/32",
                "1.9.3.10/32",
                "1.9.3.11/32",
                "1.10.3.9/32",
                "1.10.3.10/32",
                "1.10.3.11/32",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 4)), output)

    def test_ipv4_multiple_sets(self):
        input = "1.[2,22].3.[4,44]/32"
        output = sorted(
            [
                "1.2.3.4/32",
                "1.2.3.44/32",
                "1.22.3.4/32",
                "1.22.3.44/32",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 4)), output)

    def test_ipv4_set_and_range(self):
        input = "1.[2,22].3.[9-11]/32"
        output = sorted(
            [
                "1.2.3.9/32",
                "1.2.3.10/32",
                "1.2.3.11/32",
                "1.22.3.9/32",
                "1.22.3.10/32",
                "1.22.3.11/32",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 4)), output)

    def test_ipv6_range(self):
        input = "fec::abcd:[9-b]/64"
        output = sorted(
            [
                "fec::abcd:9/64",
                "fec::abcd:a/64",
                "fec::abcd:b/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 6)), output)

    def test_ipv6_range_multichar_field(self):
        input = "fec::abcd:[f-11]/64"
        output = sorted(
            [
                "fec::abcd:f/64",
                "fec::abcd:10/64",
                "fec::abcd:11/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 6)), output)

    def test_ipv6_set(self):
        input = "fec::abcd:[9,ab]/64"
        output = sorted(
            [
                "fec::abcd:9/64",
                "fec::abcd:ab/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 6)), output)

    def test_ipv6_multiple_ranges(self):
        input = "fec::[1-2]bcd:[9-b]/64"
        output = sorted(
            [
                "fec::1bcd:9/64",
                "fec::1bcd:a/64",
                "fec::1bcd:b/64",
                "fec::2bcd:9/64",
                "fec::2bcd:a/64",
                "fec::2bcd:b/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 6)), output)

    def test_ipv6_multiple_sets(self):
        input = "fec::[a,f]bcd:[9,ab]/64"
        output = sorted(
            [
                "fec::abcd:9/64",
                "fec::abcd:ab/64",
                "fec::fbcd:9/64",
                "fec::fbcd:ab/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 6)), output)

    def test_ipv6_set_and_range(self):
        input = "fec::[dead,beaf]:[9-b]/64"
        output = sorted(
            [
                "fec::dead:9/64",
                "fec::dead:a/64",
                "fec::dead:b/64",
                "fec::beaf:9/64",
                "fec::beaf:a/64",
                "fec::beaf:b/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input, 6)), output)

    def test_invalid_address_family(self):
        with self.assertRaisesRegex(Exception, "Invalid IP address family: 5"):
            sorted(expand_ipaddress_pattern(None, 5))

    def test_invalid_non_pattern(self):
        with self.assertRaises(ValueError):
            sorted(expand_ipaddress_pattern("1.2.3.4/32", 4))

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            sorted(expand_ipaddress_pattern("1.2.3.[4-]/32", 4))

        with self.assertRaises(ValueError):
            sorted(expand_ipaddress_pattern("1.2.3.[-4]/32", 4))

        with self.assertRaises(ValueError):
            sorted(expand_ipaddress_pattern("1.2.3.[4--5]/32", 4))

    def test_invalid_range_bounds(self):
        self.assertEqual(sorted(expand_ipaddress_pattern("1.2.3.[4-3]/32", 6)), [])

    def test_invalid_set(self):
        with self.assertRaises(ValueError):
            sorted(expand_ipaddress_pattern("1.2.3.[4]/32", 4))

        with self.assertRaises(ValueError):
            sorted(expand_ipaddress_pattern("1.2.3.[4,]/32", 4))

        with self.assertRaises(ValueError):
            sorted(expand_ipaddress_pattern("1.2.3.[,4]/32", 4))

        with self.assertRaises(ValueError):
            sorted(expand_ipaddress_pattern("1.2.3.[4,,5]/32", 4))


class ExpandAlphanumeric(TestCase):
    """
    Validate the operation of expand_alphanumeric_pattern().
    """

    def test_range_numberic(self):
        input = "r[9-11]a"
        output = sorted(
            [
                "r9a",
                "r10a",
                "r11a",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input)), output)

    def test_range_alpha(self):
        input = "[r-t]1a"
        output = sorted(
            [
                "r1a",
                "s1a",
                "t1a",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input)), output)

    def test_set(self):
        input = "[r,t]1a"
        output = sorted(
            [
                "r1a",
                "t1a",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input)), output)

    def test_set_multichar(self):
        input = "[ra,tb]1a"
        output = sorted(
            [
                "ra1a",
                "tb1a",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input)), output)

    def test_multiple_ranges(self):
        input = "[r-t]1[a-b]"
        output = sorted(
            [
                "r1a",
                "r1b",
                "s1a",
                "s1b",
                "t1a",
                "t1b",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input)), output)

    def test_multiple_sets(self):
        input = "[ra,tb]1[ax,by]"
        output = sorted(
            [
                "ra1ax",
                "ra1by",
                "tb1ax",
                "tb1by",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input)), output)

    def test_set_and_range(self):
        input = "[ra,tb]1[a-c]"
        output = sorted(
            [
                "ra1a",
                "ra1b",
                "ra1c",
                "tb1a",
                "tb1b",
                "tb1c",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input)), output)

    def test_invalid_non_pattern(self):
        with self.assertRaises(ValueError):
            sorted(expand_alphanumeric_pattern("r9a"))

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            sorted(expand_alphanumeric_pattern("r[8-]a"))

        with self.assertRaises(ValueError):
            sorted(expand_alphanumeric_pattern("r[-8]a"))

        with self.assertRaises(ValueError):
            sorted(expand_alphanumeric_pattern("r[8--9]a"))

    def test_invalid_range_alphanumeric(self):
        self.assertEqual(sorted(expand_alphanumeric_pattern("r[9-a]a")), [])
        self.assertEqual(sorted(expand_alphanumeric_pattern("r[a-9]a")), [])

    def test_invalid_range_bounds(self):
        self.assertEqual(sorted(expand_alphanumeric_pattern("r[9-8]a")), [])
        self.assertEqual(sorted(expand_alphanumeric_pattern("r[b-a]a")), [])

    def test_invalid_range_len(self):
        with self.assertRaises(forms.ValidationError):
            sorted(expand_alphanumeric_pattern("r[a-bb]a"))

    def test_invalid_set(self):
        with self.assertRaises(ValueError):
            sorted(expand_alphanumeric_pattern("r[a]a"))

        with self.assertRaises(ValueError):
            sorted(expand_alphanumeric_pattern("r[a,]a"))

        with self.assertRaises(ValueError):
            sorted(expand_alphanumeric_pattern("r[,a]a"))

        with self.assertRaises(ValueError):
            sorted(expand_alphanumeric_pattern("r[a,,b]a"))


class CSVDataFieldTest(TestCase):
    def setUp(self):
        self.field = CSVDataField(from_form=IPAddressCSVForm)

    def test_clean(self):
        input = """
        address,status,vrf
        192.0.2.1/32,Active,Test VRF
        """
        output = (
            {"address": None, "status": None, "vrf": None},
            [{"address": "192.0.2.1/32", "status": "Active", "vrf": "Test VRF"}],
        )
        self.assertEqual(self.field.clean(input), output)

    def test_clean_invalid_header(self):
        input = """
        address,status,vrf,xxx
        192.0.2.1/32,Active,Test VRF,123
        """
        with self.assertRaises(forms.ValidationError):
            self.field.clean(input)

    def test_clean_missing_required_header(self):
        input = """
        status,vrf
        Active,Test VRF
        """
        with self.assertRaises(forms.ValidationError):
            self.field.clean(input)

    def test_clean_default_to_field(self):
        input = """
        address,status,vrf.name
        192.0.2.1/32,Active,Test VRF
        """
        output = (
            {"address": None, "status": None, "vrf": "name"},
            [{"address": "192.0.2.1/32", "status": "Active", "vrf": "Test VRF"}],
        )
        self.assertEqual(self.field.clean(input), output)

    def test_clean_pk_to_field(self):
        input = """
        address,status,vrf.pk
        192.0.2.1/32,Active,123
        """
        output = (
            {"address": None, "status": None, "vrf": "pk"},
            [{"address": "192.0.2.1/32", "status": "Active", "vrf": "123"}],
        )
        self.assertEqual(self.field.clean(input), output)

    def test_clean_custom_to_field(self):
        input = """
        address,status,vrf.rd
        192.0.2.1/32,Active,123:456
        """
        output = (
            {"address": None, "status": None, "vrf": "rd"},
            [{"address": "192.0.2.1/32", "status": "Active", "vrf": "123:456"}],
        )
        self.assertEqual(self.field.clean(input), output)

    def test_clean_invalid_to_field(self):
        input = """
        address,status,vrf.xxx
        192.0.2.1/32,Active,123:456
        """
        with self.assertRaises(forms.ValidationError):
            self.field.clean(input)

    def test_clean_to_field_on_non_object(self):
        input = """
        address,status.foo,vrf
        192.0.2.1/32,Bar,Test VRF
        """
        with self.assertRaises(forms.ValidationError):
            self.field.clean(input)


class DynamicModelMultipleChoiceFieldTest(TestCase):
    """Tests for DynamicModelMultipleChoiceField."""

    def setUp(self):
        self.field = DynamicModelMultipleChoiceField(queryset=IPAddress.objects.all())

    def test_prepare_value_single_str(self):
        """A single string (UUID) value should be treated as a single-entry list."""
        self.assertEqual(
            self.field.prepare_value("c671a001-4c17-4ca1-80fd-fe1609bcadec"),
            ["c671a001-4c17-4ca1-80fd-fe1609bcadec"],
        )

    def test_prepare_value_multiple_str(self):
        """A list of string (UUID) values should be handled as-is."""
        self.assertEqual(
            self.field.prepare_value(["c671a001-4c17-4ca1-80fd-fe1609bcadec", "097581e8-1fd5-444f-bbf4-46324e924826"]),
            ["c671a001-4c17-4ca1-80fd-fe1609bcadec", "097581e8-1fd5-444f-bbf4-46324e924826"],
        )

    def test_prepare_value_single_object(self):
        """A single object value should be translated to its corresponding PK."""
        address = IPAddress.objects.create(address="10.1.1.1/24")
        self.assertEqual(
            self.field.prepare_value(address),
            address.pk,
        )

    def test_prepare_value_multiple_object(self):
        """A list of object values should be translated to a list of PKs."""
        address_1 = IPAddress.objects.create(address="10.1.1.1/24")
        address_2 = IPAddress.objects.create(address="10.1.1.2/24")
        self.assertEqual(
            self.field.prepare_value([address_1, address_2]),
            [address_1.pk, address_2.pk],
        )


class NumericArrayFieldTest(TestCase):
    def setUp(self):
        super().setUp()
        self.field = ServiceForm().fields["ports"]

    def test_valid_input(self):
        # Mapping of input => expected
        tests = {
            "80,443-444": [80, 443, 444],
            "1024-1028,31337": [1024, 1025, 1026, 1027, 1028, 31337],
        }
        for test, expected in tests.items():
            self.assertEqual(self.field.clean(test), expected)

    def test_invalid_input(self):
        tests = [
            "pizza",
            "-41",
        ]
        for test in tests:
            with self.assertRaises(forms.ValidationError):
                self.field.clean(test)


class AddressFieldMixinTest(TestCase):
    """Test cases for the AddressFieldMixin."""

    def setUp(self):
        """Setting up shared variables for the AddressFieldMixin."""
        self.ip = IPAddress.objects.create(address="10.0.0.1/24")
        self.initial = {"address": self.ip.address}

    def test_address_initial(self):
        """Ensure initial kwargs for address is passed in."""
        with mock.patch("nautobot.utilities.forms.forms.forms.ModelForm.__init__") as mock_init:
            ip_none = IPAddress()
            AddressFieldMixin(initial=self.initial, instance=ip_none)
            mock_init.assert_called_with(initial=self.initial, instance=ip_none)

    def test_address_instance(self):
        """Ensure override with computed field when initial kwargs for address is not passed in."""

        # Mock the django.forms.ModelForm __init__ function used in nautobot.utilities.forms.forms
        with mock.patch("nautobot.utilities.forms.forms.forms.ModelForm.__init__") as mock_init:
            AddressFieldMixin(instance=self.ip)
            mock_init.assert_called_with(initial=self.initial, instance=self.ip)


class PrefixFieldMixinTest(TestCase):
    """Test cases for the PrefixFieldMixin."""

    def setUp(self):
        """Setting up shared variables for the PrefixFieldMixin."""
        self.prefix = Prefix.objects.create(prefix=IPNetwork("10.0.0.0/24"))
        self.initial = {"prefix": self.prefix.prefix}

    def test_prefix_initial(self):
        """Ensure initial kwargs for prefix is passed through."""
        with mock.patch("nautobot.utilities.forms.forms.forms.ModelForm.__init__") as mock_init:
            prefix_none = Prefix()
            PrefixFieldMixin(initial=self.initial, instance=prefix_none)
            mock_init.assert_called_with(initial=self.initial, instance=prefix_none)

    def test_prefix_instance(self):
        """Ensure override with computed field when initial kwargs for prefix is not passed in."""

        # Mock the django.forms.ModelForm __init__ function used in nautobot.utilities.forms.forms
        with mock.patch("nautobot.utilities.forms.forms.forms.ModelForm.__init__") as mock_init:
            PrefixFieldMixin(instance=self.prefix)
            mock_init.assert_called_with(initial=self.initial, instance=self.prefix)
