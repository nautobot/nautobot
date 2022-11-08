from django import forms
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from unittest import mock
from netaddr import IPNetwork

from nautobot.dcim.filters import SiteFilterSet
from nautobot.dcim.models import Device
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.extras.filters import StatusFilterSet
from nautobot.extras.models import CustomField
from nautobot.ipam.forms import IPAddressCSVForm, ServiceForm, ServiceFilterForm
from nautobot.ipam.models import IPAddress, Prefix, VLANGroup
from nautobot.utilities.filters import MultiValueCharFilter
from nautobot.utilities.forms.fields import (
    CSVDataField,
    DynamicModelMultipleChoiceField,
    JSONField,
    MultiMatchModelMultipleChoiceField,
    MultiValueCharField,
)
from nautobot.utilities.forms.utils import (
    expand_alphanumeric_pattern,
    expand_ipaddress_pattern,
    add_field_to_filter_form_class,
)
from nautobot.utilities.forms.widgets import APISelect, APISelectMultiple, DatePicker, StaticSelect2
from nautobot.utilities.forms.forms import AddressFieldMixin, DynamicFilterForm, PrefixFieldMixin
from nautobot.utilities.testing import TestCase as NautobotTestCase
from nautobot.utilities.utils import convert_querydict_to_factory_formset_acceptable_querydict


class ExpandIPAddress(TestCase):
    """
    Validate the operation of expand_ipaddress_pattern().
    """

    def test_ipv4_range(self):
        input_ = "1.2.3.[9-10]/32"
        output = sorted(
            [
                "1.2.3.9/32",
                "1.2.3.10/32",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 4)), output)

    def test_ipv4_set(self):
        input_ = "1.2.3.[4,44]/32"
        output = sorted(
            [
                "1.2.3.4/32",
                "1.2.3.44/32",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 4)), output)

    def test_ipv4_multiple_ranges(self):
        input_ = "1.[9-10].3.[9-11]/32"
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

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 4)), output)

    def test_ipv4_multiple_sets(self):
        input_ = "1.[2,22].3.[4,44]/32"
        output = sorted(
            [
                "1.2.3.4/32",
                "1.2.3.44/32",
                "1.22.3.4/32",
                "1.22.3.44/32",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 4)), output)

    def test_ipv4_set_and_range(self):
        input_ = "1.[2,22].3.[9-11]/32"
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

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 4)), output)

    def test_ipv6_range(self):
        input_ = "fec::abcd:[9-b]/64"
        output = sorted(
            [
                "fec::abcd:9/64",
                "fec::abcd:a/64",
                "fec::abcd:b/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 6)), output)

    def test_ipv6_range_multichar_field(self):
        input_ = "fec::abcd:[f-11]/64"
        output = sorted(
            [
                "fec::abcd:f/64",
                "fec::abcd:10/64",
                "fec::abcd:11/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 6)), output)

    def test_ipv6_set(self):
        input_ = "fec::abcd:[9,ab]/64"
        output = sorted(
            [
                "fec::abcd:9/64",
                "fec::abcd:ab/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 6)), output)

    def test_ipv6_multiple_ranges(self):
        input_ = "fec::[1-2]bcd:[9-b]/64"
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

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 6)), output)

    def test_ipv6_multiple_sets(self):
        input_ = "fec::[a,f]bcd:[9,ab]/64"
        output = sorted(
            [
                "fec::abcd:9/64",
                "fec::abcd:ab/64",
                "fec::fbcd:9/64",
                "fec::fbcd:ab/64",
            ]
        )

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 6)), output)

    def test_ipv6_set_and_range(self):
        input_ = "fec::[dead,beaf]:[9-b]/64"
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

        self.assertEqual(sorted(expand_ipaddress_pattern(input_, 6)), output)

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
        input_ = "r[9-11]a"
        output = sorted(
            [
                "r9a",
                "r10a",
                "r11a",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input_)), output)

    def test_range_alpha(self):
        input_ = "[r-t]1a"
        output = sorted(
            [
                "r1a",
                "s1a",
                "t1a",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input_)), output)

    def test_set(self):
        input_ = "[r,t]1a"
        output = sorted(
            [
                "r1a",
                "t1a",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input_)), output)

    def test_set_multichar(self):
        input_ = "[ra,tb]1a"
        output = sorted(
            [
                "ra1a",
                "tb1a",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input_)), output)

    def test_multiple_ranges(self):
        input_ = "[r-t]1[a-b]"
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

        self.assertEqual(sorted(expand_alphanumeric_pattern(input_)), output)

    def test_multiple_sets(self):
        input_ = "[ra,tb]1[ax,by]"
        output = sorted(
            [
                "ra1ax",
                "ra1by",
                "tb1ax",
                "tb1by",
            ]
        )

        self.assertEqual(sorted(expand_alphanumeric_pattern(input_)), output)

    def test_set_and_range(self):
        input_ = "[ra,tb]1[a-c]"
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

        self.assertEqual(sorted(expand_alphanumeric_pattern(input_)), output)

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


class AddFieldToFormClassTest(TestCase):
    def test_field_added(self):
        """
        Test adding of a new field to an existing form.
        """
        new_form_field = forms.CharField(required=False, label="Added Field Description")
        new_form_field_name = "added_form_field_name"
        self.assertNotIn(new_form_field_name, ServiceFilterForm().fields.keys())
        add_field_to_filter_form_class(ServiceFilterForm, new_form_field_name, new_form_field)
        self.assertIn(new_form_field_name, ServiceFilterForm().fields.keys())

    def test_field_validation(self):
        """
        Test that the helper function performs validation on field to be added:
            - Name collission not permitted
            - Field must be inheriting from django.forms.Field
        """
        with self.assertRaises(TypeError):
            add_field_to_filter_form_class(ServiceFilterForm, "my_custom_field_name", IPAddress)
        with self.assertRaises(AttributeError):
            add_field_to_filter_form_class(
                ServiceFilterForm, "port", forms.CharField(required=False, label="Added Field Description")
            )


class CSVDataFieldTest(TestCase):
    def setUp(self):
        self.field = CSVDataField(from_form=IPAddressCSVForm)

    def test_clean(self):
        input_ = """
        address,status,vrf
        192.0.2.1/32,Active,Test VRF
        """
        output = (
            {"address": None, "status": None, "vrf": None},
            [{"address": "192.0.2.1/32", "status": "Active", "vrf": "Test VRF"}],
        )
        self.assertEqual(self.field.clean(input_), output)

    def test_clean_invalid_header(self):
        input_ = """
        address,status,vrf,xxx
        192.0.2.1/32,Active,Test VRF,123
        """
        with self.assertRaises(forms.ValidationError):
            self.field.clean(input_)

    def test_clean_missing_required_header(self):
        input_ = """
        status,vrf
        Active,Test VRF
        """
        with self.assertRaises(forms.ValidationError):
            self.field.clean(input_)

    def test_clean_default_to_field(self):
        input_ = """
        address,status,vrf.name
        192.0.2.1/32,Active,Test VRF
        """
        output = (
            {"address": None, "status": None, "vrf": "name"},
            [{"address": "192.0.2.1/32", "status": "Active", "vrf": "Test VRF"}],
        )
        self.assertEqual(self.field.clean(input_), output)

    def test_clean_pk_to_field(self):
        input_ = """
        address,status,vrf.pk
        192.0.2.1/32,Active,123
        """
        output = (
            {"address": None, "status": None, "vrf": "pk"},
            [{"address": "192.0.2.1/32", "status": "Active", "vrf": "123"}],
        )
        self.assertEqual(self.field.clean(input_), output)

    def test_clean_custom_to_field(self):
        input_ = """
        address,status,vrf.rd
        192.0.2.1/32,Active,123:456
        """
        output = (
            {"address": None, "status": None, "vrf": "rd"},
            [{"address": "192.0.2.1/32", "status": "Active", "vrf": "123:456"}],
        )
        self.assertEqual(self.field.clean(input_), output)

    def test_clean_invalid_to_field(self):
        input_ = """
        address,status,vrf.xxx
        192.0.2.1/32,Active,123:456
        """
        with self.assertRaises(forms.ValidationError):
            self.field.clean(input_)

    def test_clean_to_field_on_non_object(self):
        input_ = """
        address,status.foo,vrf
        192.0.2.1/32,Bar,Test VRF
        """
        with self.assertRaises(forms.ValidationError):
            self.field.clean(input_)


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


class MultiValueCharFieldTest(TestCase):
    def setUp(self):
        self.filter = MultiValueCharFilter()
        self.field = MultiValueCharField()

    def test_field_class(self):
        """
        A MultiValueCharFilter should have a MultiValueCharField field_class attribute.
        """
        self.assertEqual(
            self.filter.field_class,
            MultiValueCharField,
        )

    def test_to_python_single_str(self):
        """
        A single str value should be converted to a list containing a single str value.
        """
        self.assertEqual(
            self.field.to_python("device-1"),
            ["device-1"],
        )

    def test_to_python_multiple_str(self):
        """
        Multiple str values in a list should be handled as is.
        """
        self.assertEqual(
            self.field.to_python(["device-1", "device-2", "rack-1"]),
            ["device-1", "device-2", "rack-1"],
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


class JSONFieldTest(NautobotTestCase):
    def test_no_exception_raised(self):
        """
        Demonstrate that custom fields with JSON type handle None values correctly
        """
        self.user.is_superuser = True
        self.user.save()
        create_test_device("Foo Device")
        custom_field = CustomField(
            type="json",
            name="json-field",
            required=False,
        )
        custom_field.save()
        device_content_type = ContentType.objects.get_for_model(Device)
        custom_field.content_types.set([device_content_type])
        # Fetch URL with filter parameter
        response = self.client.get(f'{reverse("dcim:device_list")}?name=Foo%20Device')
        self.assertIn("Foo Device", str(response.content))

    def test_prepare_value_with_utf8(self):
        self.assertEqual('"I am UTF-8! 😀"', JSONField().prepare_value("I am UTF-8! 😀"))


class MultiMatchModelMultipleChoiceFieldTest(TestCase):
    def test_clean(self):
        field = MultiMatchModelMultipleChoiceField(queryset=VLANGroup.objects.all())
        vlan_groups = (
            VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1"),
            VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2"),
            VLANGroup.objects.create(name="VLAN Group 3", slug="vlan-group-3"),
        )
        input_ = [vlan_groups[0].pk, vlan_groups[1].slug]
        qs = field.clean(input_)
        expected_output = [vlan_groups[0].pk, vlan_groups[1].pk]
        self.assertQuerysetEqual(qs, values=expected_output, transform=lambda x: x.pk)

        invalid_values = [
            "",
            [["test"]],
            ["test"],
            [vlan_groups[0].pk, "test"],
            [None],
            vlan_groups[0].pk,
        ]
        for value in invalid_values:
            with self.assertRaises(ValidationError):
                field.clean(value)


class WidgetsTest(TestCase):
    def test_api_select_add_query_param_with_utf8(self):
        widget = APISelect()
        widget.add_query_param("utf8", "I am UTF-8! 😀")
        self.assertEqual('["I am UTF-8! 😀"]', widget.attrs["data-query-param-utf8"])


class DynamicFilterFormTest(TestCase):
    # TODO(timizuo): investigate why test fails on CI
    # def test_dynamic_filter_form_with_missing_attr(self):
    #     with self.assertRaises(AttributeError) as err:
    #         DynamicFilterForm()
    #     self.assertEqual("'DynamicFilterForm' object requires `filterset_class` attribute", str(err.exception))

    def test_dynamic_filter_form(self):
        form = DynamicFilterForm(filterset_class=StatusFilterSet)
        site_form = DynamicFilterForm(filterset_class=SiteFilterSet)
        self.maxDiff = None

        with self.subTest("Assert capitalize"):
            self.assertEqual(form.capitalize("test"), "Test")
            self.assertEqual(form.capitalize("test_one"), "Test one")
            self.assertEqual(form.capitalize("tenant__group"), "Tenant group")
            self.assertEqual(form.capitalize("_custom_field_data__example_field"), "Example field")

        with self.subTest("Assert get_lookup_field_choices"):
            self.assertEqual(
                form._get_lookup_field_choices(),
                [
                    ("color", "Color"),
                    ("content_types", "Content type(s)"),
                    ("created", "Created"),
                    ("id", "Id"),
                    ("last_updated", "Last updated"),
                    ("name", "Name"),
                    ("slug", "Slug"),
                ],
            )
            self.assertEqual(
                site_form._get_lookup_field_choices(),
                [
                    ("asn", "ASN"),
                    ("cf_example_plugin_auto_custom_field", "Example Plugin Automatically Added Custom Field"),
                    ("circuit_terminations", "Circuit terminations"),
                    ("clusters", "Clusters"),
                    ("comments", "Comments"),
                    ("contact_email", "Contact E-mail"),
                    ("contact_name", "Contact name"),
                    ("contact_phone", "Contact phone"),
                    ("created", "Created"),
                    ("description", "Description"),
                    ("devices", "Devices (name or ID)"),
                    ("facility", "Facility"),
                    ("has_circuit_terminations", "Has circuit terminations"),
                    ("has_clusters", "Has clusters"),
                    ("has_devices", "Has devices"),
                    ("has_locations", "Has locations"),
                    ("has_power_panels", "Has power panels"),
                    ("has_prefixes", "Has prefixes"),
                    ("has_rack_groups", "Has rack groups"),
                    ("has_racks", "Has racks"),
                    ("has_vlan_groups", "Has vlan groups"),
                    ("has_vlans", "Has vlans"),
                    ("id", "Id"),
                    ("last_updated", "Last updated"),
                    ("latitude", "Latitude"),
                    ("locations", "Locations within this Site (slugs or IDs)"),
                    ("longitude", "Longitude"),
                    ("name", "Name"),
                    ("physical_address", "Physical address"),
                    ("power_panels", "Power panels (name or ID)"),
                    ("prefixes", "Prefixes"),
                    ("rack_groups", "Rack groups (slug or ID)"),
                    ("racks", "Racks"),
                    ("region", "Region (slug)"),
                    ("region_id", "Region (ID)"),
                    ("shipping_address", "Shipping address"),
                    ("slug", "Slug"),
                    ("status", "Status"),
                    ("tag", "Tags slug"),
                    ("tenant", "Tenant (slug or ID)"),
                    ("tenant_group", "Tenant Group (slug)"),
                    ("tenant_group_id", "Tenant Group (ID)"),
                    ("tenant_id", 'Tenant (ID) (deprecated, use "tenant" filter instead)'),
                    ("time_zone", "Time zone"),
                    ("vlan_groups", "Vlan groups (slug or ID)"),
                    ("vlans", "Vlans"),
                ],
            )

        with self.subTest(
            "Assert that the `filterset_filters` property of DynamicFilterForm instance gets the accurate `filterset_class` filters"
        ):

            def get_dict_of_field_and_value_class_from_filters(filters):
                """return a dict of the filters' field and field value class.

                This is required because instantiated classes of the same type are not equal.
                For Example `Site()` != `Site()` but `Site().__class__` == `Site().__class__`
                """
                return {field: value.__class__ for field, value in filters.items()}

            self.assertEqual(
                get_dict_of_field_and_value_class_from_filters(form.filterset_filters),
                get_dict_of_field_and_value_class_from_filters(StatusFilterSet().filters),
            )
            self.assertEqual(
                get_dict_of_field_and_value_class_from_filters(site_form.filterset_filters),
                get_dict_of_field_and_value_class_from_filters(SiteFilterSet().filters),
            )

        with self.subTest("Assert lookup_field, lookup_value & lookup_type fields has accurate attributes"):
            self.assertEqual(
                form.fields["lookup_field"]._choices,
                [
                    (None, "---------"),
                    ("color", "Color"),
                    ("content_types", "Content type(s)"),
                    ("created", "Created"),
                    ("id", "Id"),
                    ("last_updated", "Last updated"),
                    ("name", "Name"),
                    ("slug", "Slug"),
                ],
            )
            self.assertEqual(
                form.fields["lookup_field"].widget.attrs,
                {"class": "nautobot-select2-static lookup_field-select", "placeholder": "Field"},
            )

            self.assertEqual(
                form.fields["lookup_type"].widget.attrs,
                {
                    "class": "nautobot-select2-api lookup_type-select",
                    "placeholder": None,
                    "data-query-param-field_name": '["$lookup_field"]',
                    "data-contenttype": "extras.status",
                    "data-url": reverse("core-api:filtersetfield-list-lookupchoices"),
                },
            )

            self.assertEqual(
                form.fields["lookup_value"].widget.attrs,
                {"class": "form-control lookup_value-input form-control", "placeholder": "Value"},
            )

    def test_dynamic_filter_form_with_data_and_prefix(self):
        """Assert that lookup value implements the right field (CharField, ChoiceField etc.) and widget."""

        request_querydict = QueryDict(mutable=True)
        request_querydict.setlistdefault("name__ic", ["Site"])
        request_querydict.setlistdefault("slug", ["site-1"])
        request_querydict.setlistdefault("status", ["active"])
        request_querydict.setlistdefault("has_vlans", ["True"])
        request_querydict.setdefault("created", "2022-09-05")
        request_querydict.setlistdefault("asn", ["4"])

        with self.subTest("Test for lookup_value with a CharField"):
            # If `lookup_field` value is a CharField and or `lookup_type` lookup expr is not `exact` or `in` then,
            # `lookup_value` field should be a CharField
            data = convert_querydict_to_factory_formset_acceptable_querydict(request_querydict, SiteFilterSet)
            form = DynamicFilterForm(filterset_class=SiteFilterSet, data=data, prefix="form-0")
            self.assertEqual(form.fields["lookup_type"]._choices, [("name__ic", "contains (ic)")])
            # Assert lookup_value is a CharField
            self.assertIsInstance(form.fields["lookup_value"], forms.CharField)

            form = DynamicFilterForm(filterset_class=SiteFilterSet, data=data, prefix="form-1")
            self.assertEqual(form.fields["lookup_type"]._choices, [("slug", "exact")])
            self.assertIsInstance(form.fields["lookup_value"], forms.CharField)

        with self.subTest("Test for lookup_value with a ChoiceField and APISelectMultiple widget"):
            # If `lookup_field` value is a relational field(ManyToMany, ForeignKey etc.) and `lookup_type` lookup expr is `exact` or `in` then,
            # `lookup_value` field should be a ChoiceField with APISelectMultiple widget
            form = DynamicFilterForm(filterset_class=SiteFilterSet, data=data, prefix="form-2")
            self.assertEqual(
                form.fields["lookup_type"].widget.attrs,
                {
                    "class": "nautobot-select2-api lookup_type-select",
                    "placeholder": None,
                    "data-query-param-field_name": '["$lookup_field"]',
                    "data-contenttype": "dcim.site",
                    "data-url": reverse("core-api:filtersetfield-list-lookupchoices"),
                },
            )
            self.assertIsInstance(form.fields["lookup_value"], forms.ChoiceField)
            self.assertIsInstance(form.fields["lookup_value"].widget, APISelectMultiple)
            self.assertEqual(
                form.fields["lookup_value"].widget.attrs,
                {
                    "class": "form-control nautobot-select2-api lookup_value-input form-control",
                    "data-multiple": 1,
                    "data-query-param-content_types": '["dcim.site"]',
                    "display-field": "display",
                    "value-field": "slug",
                },
            )

        with self.subTest("Test for lookup_value with a ChoiceField and StaticSelect2 widget"):
            # If `lookup_field` value is a ChoiceField and `lookup_type` lookup expr is `exact` or `in` then,
            # `lookup_value` field should be a ChoiceField with StaticSelect2 widget
            form = DynamicFilterForm(filterset_class=SiteFilterSet, data=data, prefix="form-3")
            self.assertEqual(
                form.fields["lookup_type"].widget.attrs,
                {
                    "class": "nautobot-select2-api lookup_type-select",
                    "data-contenttype": "dcim.site",
                    "data-query-param-field_name": '["$lookup_field"]',
                    "data-url": reverse("core-api:filtersetfield-list-lookupchoices"),
                    "placeholder": None,
                },
            )
            self.assertIsInstance(form.fields["lookup_value"], forms.ChoiceField)
            self.assertEqual(
                form.fields["lookup_value"].widget.attrs,
                {"class": "form-control nautobot-select2-static lookup_value-input form-control"},
            )
            self.assertIsInstance(form.fields["lookup_value"].widget, StaticSelect2)
            self.assertEqual(form.fields["lookup_value"]._choices, [("True", "Yes"), ("False", "No")])

        with self.subTest("Test for lookup_value with a DateField"):
            form = DynamicFilterForm(filterset_class=SiteFilterSet, data=data, prefix="form-4")
            self.assertEqual(
                form.fields["lookup_type"].widget.attrs,
                {
                    "class": "nautobot-select2-api lookup_type-select",
                    "data-contenttype": "dcim.site",
                    "data-query-param-field_name": '["$lookup_field"]',
                    "data-url": reverse("core-api:filtersetfield-list-lookupchoices"),
                    "placeholder": None,
                },
            )
            self.assertIsInstance(form.fields["lookup_value"].widget, DatePicker)

        with self.subTest("Test for lookup_value with an IntegerField"):
            form = DynamicFilterForm(filterset_class=SiteFilterSet, data=data, prefix="form-5")
            self.assertEqual(
                form.fields["lookup_type"].widget.attrs,
                {
                    "class": "nautobot-select2-api lookup_type-select",
                    "data-contenttype": "dcim.site",
                    "data-query-param-field_name": '["$lookup_field"]',
                    "data-url": reverse("core-api:filtersetfield-list-lookupchoices"),
                    "placeholder": None,
                },
            )
            self.assertIsInstance(form.fields["lookup_value"], forms.IntegerField)
