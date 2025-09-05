from unittest import mock

from django import forms as django_forms
from django.contrib.contenttypes.models import ContentType
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from netaddr import IPNetwork

from nautobot.core import filters, forms, testing
from nautobot.core.utils import requests
from nautobot.dcim import filters as dcim_filters, forms as dcim_forms, models as dcim_models
from nautobot.dcim.tests import test_views
from nautobot.extras import filters as extras_filters, models as extras_models
from nautobot.ipam import forms as ipam_forms, models as ipam_models


class SearchFormTestCase(TestCase):
    def test_q_placeholder(self):
        from nautobot.core.forms import SearchForm

        self.assertEqual(SearchForm().fields["q"].widget.attrs["placeholder"], "Search")

        # Assert the q field placeholder is overridden
        self.assertEqual(
            SearchForm(q_placeholder="Search Locations").fields["q"].widget.attrs["placeholder"], "Search Locations"
        )


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

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 4)), output)

    def test_ipv4_set(self):
        input_ = "1.2.3.[4,44]/32"
        output = sorted(
            [
                "1.2.3.4/32",
                "1.2.3.44/32",
            ]
        )

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 4)), output)

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

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 4)), output)

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

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 4)), output)

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

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 4)), output)

    def test_ipv6_range(self):
        input_ = "fec::abcd:[9-b]/64"
        output = sorted(
            [
                "fec::abcd:9/64",
                "fec::abcd:a/64",
                "fec::abcd:b/64",
            ]
        )

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 6)), output)

    def test_ipv6_range_multichar_field(self):
        input_ = "fec::abcd:[f-11]/64"
        output = sorted(
            [
                "fec::abcd:f/64",
                "fec::abcd:10/64",
                "fec::abcd:11/64",
            ]
        )

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 6)), output)

    def test_ipv6_set(self):
        input_ = "fec::abcd:[9,ab]/64"
        output = sorted(
            [
                "fec::abcd:9/64",
                "fec::abcd:ab/64",
            ]
        )

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 6)), output)

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

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 6)), output)

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

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 6)), output)

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

        self.assertEqual(sorted(forms.expand_ipaddress_pattern(input_, 6)), output)

    def test_invalid_address_version(self):
        with self.assertRaisesRegex(Exception, "Invalid IP address version: 5"):
            sorted(forms.expand_ipaddress_pattern(None, 5))

    def test_invalid_non_pattern(self):
        with self.assertRaises(ValueError):
            sorted(forms.expand_ipaddress_pattern("1.2.3.4/32", 4))

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            sorted(forms.expand_ipaddress_pattern("1.2.3.[4-]/32", 4))

        with self.assertRaises(ValueError):
            sorted(forms.expand_ipaddress_pattern("1.2.3.[-4]/32", 4))

        with self.assertRaises(ValueError):
            sorted(forms.expand_ipaddress_pattern("1.2.3.[4--5]/32", 4))

    def test_invalid_range_bounds(self):
        self.assertEqual(sorted(forms.expand_ipaddress_pattern("1.2.3.[4-3]/32", 6)), [])

    def test_invalid_set(self):
        with self.assertRaises(ValueError):
            sorted(forms.expand_ipaddress_pattern("1.2.3.[4]/32", 4))

        with self.assertRaises(ValueError):
            sorted(forms.expand_ipaddress_pattern("1.2.3.[4,]/32", 4))

        with self.assertRaises(ValueError):
            sorted(forms.expand_ipaddress_pattern("1.2.3.[,4]/32", 4))

        with self.assertRaises(ValueError):
            sorted(forms.expand_ipaddress_pattern("1.2.3.[4,,5]/32", 4))


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

        self.assertEqual(sorted(forms.expand_alphanumeric_pattern(input_)), output)

    def test_range_alpha(self):
        input_ = "[r-t]1a"
        output = sorted(
            [
                "r1a",
                "s1a",
                "t1a",
            ]
        )

        self.assertEqual(sorted(forms.expand_alphanumeric_pattern(input_)), output)

    def test_set(self):
        input_ = "[r,t]1a"
        output = sorted(
            [
                "r1a",
                "t1a",
            ]
        )

        self.assertEqual(sorted(forms.expand_alphanumeric_pattern(input_)), output)

    def test_set_multichar(self):
        input_ = "[ra,tb]1a"
        output = sorted(
            [
                "ra1a",
                "tb1a",
            ]
        )

        self.assertEqual(sorted(forms.expand_alphanumeric_pattern(input_)), output)

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

        self.assertEqual(sorted(forms.expand_alphanumeric_pattern(input_)), output)

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

        self.assertEqual(sorted(forms.expand_alphanumeric_pattern(input_)), output)

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

        self.assertEqual(sorted(forms.expand_alphanumeric_pattern(input_)), output)

    def test_invalid_non_pattern(self):
        with self.assertRaises(ValueError):
            sorted(forms.expand_alphanumeric_pattern("r9a"))

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            sorted(forms.expand_alphanumeric_pattern("r[8-]a"))

        with self.assertRaises(ValueError):
            sorted(forms.expand_alphanumeric_pattern("r[-8]a"))

        with self.assertRaises(ValueError):
            sorted(forms.expand_alphanumeric_pattern("r[8--9]a"))

    def test_invalid_range_alphanumeric(self):
        self.assertEqual(sorted(forms.expand_alphanumeric_pattern("r[9-a]a")), [])
        self.assertEqual(sorted(forms.expand_alphanumeric_pattern("r[a-9]a")), [])

    def test_invalid_range_bounds(self):
        self.assertEqual(sorted(forms.expand_alphanumeric_pattern("r[9-8]a")), [])
        self.assertEqual(sorted(forms.expand_alphanumeric_pattern("r[b-a]a")), [])

    def test_invalid_range_len(self):
        with self.assertRaises(django_forms.ValidationError):
            sorted(forms.expand_alphanumeric_pattern("r[a-bb]a"))

    def test_invalid_set(self):
        with self.assertRaises(ValueError):
            sorted(forms.expand_alphanumeric_pattern("r[a]a"))

        with self.assertRaises(ValueError):
            sorted(forms.expand_alphanumeric_pattern("r[a,]a"))

        with self.assertRaises(ValueError):
            sorted(forms.expand_alphanumeric_pattern("r[,a]a"))

        with self.assertRaises(ValueError):
            sorted(forms.expand_alphanumeric_pattern("r[a,,b]a"))


class AddFieldToFormClassTest(TestCase):
    def test_field_added(self):
        """
        Test adding of a new field to an existing form.
        """
        new_form_field = django_forms.CharField(required=False, label="Added Field Description")
        new_form_field_name = "added_form_field_name"
        self.assertNotIn(new_form_field_name, ipam_forms.ServiceFilterForm().fields.keys())
        forms.add_field_to_filter_form_class(ipam_forms.ServiceFilterForm, new_form_field_name, new_form_field)
        self.assertIn(new_form_field_name, ipam_forms.ServiceFilterForm().fields.keys())

    def test_field_validation(self):
        """
        Test that the helper function performs validation on field to be added:
            - Name collission not permitted
            - Field must be inheriting from django.forms.Field
        """
        with self.assertRaises(TypeError):
            forms.add_field_to_filter_form_class(
                ipam_forms.ServiceFilterForm, "my_custom_field_name", ipam_models.IPAddress
            )
        with self.assertRaises(AttributeError):
            forms.add_field_to_filter_form_class(
                ipam_forms.ServiceFilterForm,
                "ports",
                django_forms.CharField(required=False, label="Added Field Description"),
            )


class DynamicModelChoiceFieldTest(TestCase):
    """Tests for DynamicModelChoiceField."""

    def setUp(self):
        self.field = forms.DynamicModelChoiceField(queryset=ipam_models.IPAddress.objects.all())
        self.field_with_to_field_name = forms.DynamicModelChoiceField(
            queryset=ipam_models.IPAddress.objects.all(), to_field_name="address"
        )

    def test_prepare_value_invalid_uuid(self):
        """A nonexistent UUID PK value should be handled gracefully."""
        value = "c671a001-4c17-4ca1-80fd-fe1609bcadec"
        self.assertEqual(self.field.prepare_value(value), value)
        self.assertEqual(self.field_with_to_field_name.prepare_value(value), value)

    def test_prepare_value_valid_uuid(self):
        """A UUID PK referring to an actual object should be handled correctly."""
        ipaddr_status = extras_models.Status.objects.get_for_model(ipam_models.IPAddress).first()
        prefix_status = extras_models.Status.objects.get_for_model(ipam_models.Prefix).first()
        namespace = ipam_models.Namespace.objects.first()
        ipam_models.Prefix.objects.create(prefix="10.1.1.0/24", namespace=namespace, status=prefix_status)
        address = ipam_models.IPAddress.objects.create(address="10.1.1.1/24", namespace=namespace, status=ipaddr_status)
        self.assertEqual(self.field.prepare_value(address.pk), address.pk)
        self.assertEqual(self.field_with_to_field_name.prepare_value(address.pk), address.address)

    def test_prepare_value_valid_object(self):
        """An object reference should be handled correctly."""
        ipaddr_status = extras_models.Status.objects.get_for_model(ipam_models.IPAddress).first()
        prefix_status = extras_models.Status.objects.get_for_model(ipam_models.Prefix).first()
        namespace = ipam_models.Namespace.objects.first()
        ipam_models.Prefix.objects.create(prefix="10.1.1.0/24", namespace=namespace, status=prefix_status)
        address = ipam_models.IPAddress.objects.create(address="10.1.1.1/24", namespace=namespace, status=ipaddr_status)
        self.assertEqual(self.field.prepare_value(address), address.pk)
        self.assertEqual(self.field_with_to_field_name.prepare_value(address), address.address)


class DynamicModelMultipleChoiceFieldTest(TestCase):
    """Tests for DynamicModelMultipleChoiceField."""

    def setUp(self):
        self.field = forms.DynamicModelMultipleChoiceField(queryset=ipam_models.IPAddress.objects.all())
        self.field_with_to_field_name = forms.DynamicModelMultipleChoiceField(
            queryset=ipam_models.IPAddress.objects.all(), to_field_name="address"
        )

    def test_prepare_value_multiple_str(self):
        """A list of string (UUID) values should be handled as-is."""
        values = ["c671a001-4c17-4ca1-80fd-fe1609bcadec", "097581e8-1fd5-444f-bbf4-46324e924826"]
        self.assertEqual(self.field.prepare_value(values), values)
        self.assertEqual(self.field_with_to_field_name.prepare_value(values), values)

    def test_prepare_value_multiple_object(self):
        """A list of object values should be translated to a list of PKs."""
        ipaddr_status = extras_models.Status.objects.get_for_model(ipam_models.IPAddress).first()
        prefix_status = extras_models.Status.objects.get_for_model(ipam_models.Prefix).first()
        namespace = ipam_models.Namespace.objects.first()
        ipam_models.Prefix.objects.create(prefix="10.1.1.0/24", namespace=namespace, status=prefix_status)
        address_1 = ipam_models.IPAddress.objects.create(
            address="10.1.1.1/24", namespace=namespace, status=ipaddr_status
        )
        address_2 = ipam_models.IPAddress.objects.create(
            address="10.1.1.2/24", namespace=namespace, status=ipaddr_status
        )
        self.assertEqual(
            self.field.prepare_value([address_1, address_2]),
            [address_1.pk, address_2.pk],
        )
        self.assertEqual(
            self.field_with_to_field_name.prepare_value([address_1, address_2]),
            [address_1.address, address_2.address],
        )


class MultiValueCharFieldTest(TestCase):
    def setUp(self):
        self.filter = filters.MultiValueCharFilter()
        self.field = forms.MultiValueCharField()

    def test_field_class(self):
        """
        A MultiValueCharFilter should have a MultiValueCharField field_class attribute.
        """
        self.assertEqual(
            self.filter.field_class,
            forms.MultiValueCharField,
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
        # We need to use a field with required=False so we can test empty/None inputs
        self.field = dcim_forms.DeviceFilterForm().fields["device_redundancy_group_priority"]

    def test_valid_input(self):
        #  List of (input, expected output) tuples
        tests = [
            (None, []),
            ("", []),
            ("80,443-444", [80, 443, 444]),
            ("1024-1028,31337", [1024, 1025, 1026, 1027, 1028, 31337]),
            (["47-49", "103"], [47, 48, 49, 103]),
            ([231, 432, 313], [231, 313, 432]),
        ]
        for test, expected in tests:
            self.assertEqual(self.field.clean(test), expected)

    def test_invalid_input(self):
        tests = [
            "pizza",
            "-41",
            "[84,52,33]",
        ]
        for test in tests:
            with self.assertRaises(django_forms.ValidationError):
                self.field.clean(test)


class AddressFieldMixinTest(TestCase):
    """Test cases for the AddressFieldMixin."""

    def setUp(self):
        """Setting up shared variables for the AddressFieldMixin."""
        ipaddr_status = extras_models.Status.objects.get_for_model(ipam_models.IPAddress).first()
        prefix_status = extras_models.Status.objects.get_for_model(ipam_models.Prefix).first()
        self.namespace = ipam_models.Namespace.objects.first()
        self.prefix, _ = ipam_models.Prefix.objects.get_or_create(
            prefix="10.0.0.0/24", namespace=self.namespace, defaults={"status": prefix_status}
        )
        self.ip, _ = ipam_models.IPAddress.objects.get_or_create(
            address="10.0.0.1/32", parent=self.prefix, defaults={"status": ipaddr_status}
        )
        self.initial = {"address": self.ip.address}

        with mock.patch("nautobot.core.forms.forms.forms.ModelForm.__init__") as mock_init:
            ip_none = ipam_models.IPAddress()
            forms.AddressFieldMixin(initial=self.initial, instance=ip_none)
            mock_init.assert_called_with(initial=self.initial, instance=ip_none)

    def test_address_instance(self):
        """Ensure override with computed field when initial kwargs for address is not passed in."""

        # Mock the django.forms.ModelForm __init__ function used in nautobot.core.forms.forms
        with mock.patch("nautobot.core.forms.forms.forms.ModelForm.__init__") as mock_init:
            forms.AddressFieldMixin(instance=self.ip)
            mock_init.assert_called_with(initial=self.initial, instance=self.ip)


class PrefixFieldMixinTest(TestCase):
    """Test cases for the PrefixFieldMixin."""

    def setUp(self):
        """Setting up shared variables for the PrefixFieldMixin."""
        status = extras_models.Status.objects.get_for_model(ipam_models.Prefix).first()
        self.prefix = ipam_models.Prefix.objects.create(prefix=IPNetwork("10.0.0.0/24"), status=status)
        self.initial = {"prefix": self.prefix.prefix}

    def test_prefix_initial(self):
        """Ensure initial kwargs for prefix is passed through."""
        with mock.patch("nautobot.core.forms.forms.forms.ModelForm.__init__") as mock_init:
            prefix_none = ipam_models.Prefix()
            forms.PrefixFieldMixin(initial=self.initial, instance=prefix_none)
            mock_init.assert_called_with(initial=self.initial, instance=prefix_none)

    def test_prefix_instance(self):
        """Ensure override with computed field when initial kwargs for prefix is not passed in."""

        # Mock the django.forms.ModelForm __init__ function used in nautobot.core.forms.forms
        with mock.patch("nautobot.core.forms.forms.forms.ModelForm.__init__") as mock_init:
            forms.PrefixFieldMixin(instance=self.prefix)
            mock_init.assert_called_with(initial=self.initial, instance=self.prefix)


class JSONFieldTest(testing.TestCase):
    def test_no_exception_raised(self):
        """
        Demonstrate that custom fields with JSON type handle None values correctly
        """
        self.user.is_superuser = True
        self.user.save()
        test_views.create_test_device("Foo Device")
        custom_field = extras_models.CustomField(
            type="json",
            label="JSON Field",
            required=False,
        )
        custom_field.save()
        device_content_type = ContentType.objects.get_for_model(dcim_models.Device)
        custom_field.content_types.set([device_content_type])
        # Fetch URL with filter parameter
        response = self.client.get(f"{reverse('dcim:device_list')}?name=Foo%20Device")
        self.assertIn("Foo Device", str(response.content))

    def test_prepare_value_with_utf8(self):
        self.assertEqual('"I am UTF-8! 😀"', forms.JSONField().prepare_value("I am UTF-8! 😀"))


class MultiMatchModelMultipleChoiceFieldTest(TestCase):
    def test_clean(self):
        field = forms.MultiMatchModelMultipleChoiceField(
            queryset=ipam_models.VLANGroup.objects.all(), to_field_name="name"
        )
        vlan_groups = (
            ipam_models.VLANGroup.objects.create(name="VLAN Group 1"),
            ipam_models.VLANGroup.objects.create(name="VLAN Group 2"),
            ipam_models.VLANGroup.objects.create(name="VLAN Group 3"),
        )
        input_ = [vlan_groups[0].pk, vlan_groups[1].name]
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
            with self.assertRaises(django_forms.ValidationError):
                field.clean(value)


class WidgetsTest(TestCase):
    def test_api_select_add_query_param_with_utf8(self):
        widget = forms.APISelect()
        widget.add_query_param("utf8", "I am UTF-8! 😀")
        self.assertEqual('["I am UTF-8! 😀"]', widget.attrs["data-query-param-utf8"])


class DynamicFilterFormTest(TestCase):
    # TODO(timizuo): investigate why test fails on CI
    # def test_dynamic_filter_form_with_missing_attr(self):
    #     with self.assertRaises(AttributeError) as err:
    #         DynamicFilterForm()
    #     self.assertEqual("'DynamicFilterForm' object requires `filterset_class` attribute", str(err.exception))

    def test_dynamic_filter_form(self):
        form = forms.DynamicFilterForm(filterset=extras_filters.StatusFilterSet())
        location_form = forms.DynamicFilterForm(filterset=dcim_filters.LocationFilterSet())
        self.maxDiff = None

        with self.subTest("Assert get_lookup_field_choices"):
            self.assertEqual(
                form._get_lookup_field_choices(),
                [
                    ("color", "Color"),
                    ("contacts", "Contacts (name or ID)"),
                    ("content_types", "Content type(s)"),
                    ("created", "Created"),
                    ("dynamic_groups", "Dynamic groups (name or ID)"),
                    ("id", "Id"),
                    ("last_updated", "Last updated"),
                    ("name", "Name"),
                    ("teams", "Teams (name or ID)"),
                ],
            )
            self.assertEqual(
                location_form._get_lookup_field_choices(),
                [
                    ("asn", "ASN"),
                    ("child_location_type", "Child location type (name or ID)"),
                    ("circuit_terminations", "Circuit terminations"),
                    ("clusters", "Clusters (name or ID)"),
                    ("comments", "Comments"),
                    ("contact_email", "Contact E-mail"),
                    ("contact_name", "Contact name"),
                    ("contact_phone", "Contact phone"),
                    ("contacts", "Contacts (name or ID)"),
                    ("created", "Created"),
                    ("description", "Description"),
                    ("devices", "Devices (name or ID)"),
                    ("dynamic_groups", "Dynamic groups (name or ID)"),
                    ("cf_example_app_auto_custom_field", "Example App Automatically Added Custom Field"),
                    ("facility", "Facility"),
                    ("has_vlan_groups", "Has VLAN groups"),
                    ("has_vlans", "Has VLANs"),
                    ("has_circuit_terminations", "Has circuit terminations"),
                    ("has_clusters", "Has clusters"),
                    ("has_devices", "Has devices"),
                    ("has_power_panels", "Has power panels"),
                    ("has_prefixes", "Has prefixes"),
                    ("has_rack_groups", "Has rack groups"),
                    ("has_racks", "Has racks"),
                    ("id", "Id"),
                    ("last_updated", "Last updated"),
                    ("latitude", "Latitude"),
                    ("location_type", "Location type (name or ID)"),
                    ("subtree", "Location(s) and descendants thereof (name or ID)"),
                    ("longitude", "Longitude"),
                    ("name", "Name"),
                    ("content_type", "Object types allowed to be associated with this Location Type"),
                    ("parent", "Parent location (name or ID)"),
                    ("physical_address", "Physical address"),
                    ("power_panels", "Power panels (name or ID)"),
                    ("prefixes", "Prefixes"),
                    ("racks", "Rack (name or ID)"),
                    ("rack_groups", "Rack groups (name or ID)"),
                    ("shipping_address", "Shipping address"),
                    ("status", "Status (name or ID)"),
                    ("vlans", "Tagged VLANs (VID or ID)"),
                    ("tags", "Tags"),
                    ("teams", "Teams (name or ID)"),
                    ("tenant_id", 'Tenant (ID) (deprecated, use "tenant" filter instead)'),
                    ("tenant", "Tenant (name or ID)"),
                    ("tenant_group", "Tenant Group (name or ID)"),
                    ("time_zone", "Time zone"),
                    ("vlan_groups", "VLAN groups (name or ID)"),
                ],
            )

        with self.subTest(
            "Assert that the `filterset_filters` property of DynamicFilterForm instance "
            "gets the accurate `filterset_class` filters"
        ):

            def get_dict_of_field_and_value_class_from_filters(filters_dict):
                """return a dict of the filters' field and field value class.

                This is required because instantiated classes of the same type are not equal.
                For Example `Location()` != `Location()` but `Location().__class__` == `Location().__class__`
                """
                return {field: value.__class__ for field, value in filters_dict.items()}

            self.assertEqual(
                get_dict_of_field_and_value_class_from_filters(form.filterset_filters),
                get_dict_of_field_and_value_class_from_filters(extras_filters.StatusFilterSet().filters),
            )
            self.assertEqual(
                get_dict_of_field_and_value_class_from_filters(location_form.filterset_filters),
                get_dict_of_field_and_value_class_from_filters(dcim_filters.LocationFilterSet().filters),
            )

        with self.subTest("Assert lookup_field, lookup_value & lookup_type fields has accurate attributes"):
            self.assertEqual(
                form.fields["lookup_field"]._choices,
                [
                    (None, "---------"),
                    ("color", "Color"),
                    ("contacts", "Contacts (name or ID)"),
                    ("content_types", "Content type(s)"),
                    ("created", "Created"),
                    ("dynamic_groups", "Dynamic groups (name or ID)"),
                    ("id", "Id"),
                    ("last_updated", "Last updated"),
                    ("name", "Name"),
                    ("teams", "Teams (name or ID)"),
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
        request_querydict.setlistdefault("name__ic", ["Location"])
        request_querydict.setlistdefault("status", ["active"])
        request_querydict.setlistdefault("has_vlans", ["True"])
        request_querydict.setlistdefault("created__gte", ["2022-09-05 11:22:33"])
        request_querydict.setlistdefault("asn", ["4"])

        location_filterset = dcim_filters.LocationFilterSet()

        with self.subTest("Test for lookup_value with a CharField"):
            # If `lookup_field` value is a CharField and or `lookup_type` lookup expr is not `exact` or `in` then,
            # `lookup_value` field should be a CharField
            data = requests.convert_querydict_to_factory_formset_acceptable_querydict(
                request_querydict, location_filterset
            )
            form = forms.DynamicFilterForm(filterset=location_filterset, data=data, prefix="form-0")
            self.assertEqual(form.fields["lookup_type"]._choices, [("name__ic", "contains (ic)")])
            # Assert lookup_value is a CharField
            self.assertIsInstance(form.fields["lookup_value"], django_forms.CharField)

        with self.subTest("Test for lookup_value with a ChoiceField and APISelectMultiple widget"):
            # If `lookup_field` value is a relational field(ManyToMany, ForeignKey etc.) and `lookup_type` lookup expr is `exact` or `in` then,
            # `lookup_value` field should be a ChoiceField with APISelectMultiple widget
            form = forms.DynamicFilterForm(filterset=location_filterset, data=data, prefix="form-1")
            self.assertEqual(
                form.fields["lookup_type"].widget.attrs,
                {
                    "class": "nautobot-select2-api lookup_type-select",
                    "placeholder": None,
                    "data-query-param-field_name": '["$lookup_field"]',
                    "data-contenttype": "dcim.location",
                    "data-url": reverse("core-api:filtersetfield-list-lookupchoices"),
                },
            )
            self.assertIsInstance(form.fields["lookup_value"], django_forms.ChoiceField)
            self.assertIsInstance(form.fields["lookup_value"].widget, forms.APISelectMultiple)
            self.assertEqual(
                form.fields["lookup_value"].widget.attrs,
                {
                    "class": "form-control nautobot-select2-api lookup_value-input form-control",
                    "data-depth": 0,
                    "data-multiple": 1,
                    "data-query-param-content_types": '["dcim.location"]',
                    "data-query-param-exclude_m2m": '["true"]',
                    "display-field": "display",
                    "value-field": "name",
                },
            )

        with self.subTest("Test for lookup_value with a ChoiceField and StaticSelect2 widget"):
            # If `lookup_field` value is a boolean filter and `lookup_type` lookup expr is `exact`, then
            # `lookup_value` field should be a ChoiceField with StaticSelect2 widget
            form = forms.DynamicFilterForm(filterset=location_filterset, data=data, prefix="form-2")
            self.assertEqual(
                form.fields["lookup_type"].widget.attrs,
                {
                    "class": "nautobot-select2-api lookup_type-select",
                    "data-contenttype": "dcim.location",
                    "data-query-param-field_name": '["$lookup_field"]',
                    "data-url": reverse("core-api:filtersetfield-list-lookupchoices"),
                    "placeholder": None,
                },
            )
            self.assertIsInstance(form.fields["lookup_value"], django_forms.ChoiceField)
            self.assertEqual(
                form.fields["lookup_value"].widget.attrs,
                {"class": "form-control nautobot-select2-static lookup_value-input form-control"},
            )
            self.assertIsInstance(form.fields["lookup_value"].widget, forms.StaticSelect2)
            self.assertEqual(form.fields["lookup_value"].widget.choices, [("True", "Yes"), ("False", "No")])

        with self.subTest("Test for lookup_value with a DateTimeField"):
            form = forms.DynamicFilterForm(filterset=location_filterset, data=data, prefix="form-3")
            self.assertEqual(
                form.fields["lookup_type"].widget.attrs,
                {
                    "class": "nautobot-select2-api lookup_type-select",
                    "data-contenttype": "dcim.location",
                    "data-query-param-field_name": '["$lookup_field"]',
                    "data-url": reverse("core-api:filtersetfield-list-lookupchoices"),
                    "placeholder": None,
                },
            )
            self.assertIsInstance(form.fields["lookup_value"].widget, forms.DateTimePicker)

        with self.subTest("Test for lookup_value with an IntegerField"):
            form = forms.DynamicFilterForm(filterset=location_filterset, data=data, prefix="form-4")
            self.assertEqual(
                form.fields["lookup_type"].widget.attrs,
                {
                    "class": "nautobot-select2-api lookup_type-select",
                    "data-contenttype": "dcim.location",
                    "data-query-param-field_name": '["$lookup_field"]',
                    "data-url": reverse("core-api:filtersetfield-list-lookupchoices"),
                    "placeholder": None,
                },
            )
            self.assertIsInstance(form.fields["lookup_value"], django_forms.IntegerField)
