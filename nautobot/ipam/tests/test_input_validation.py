"""Regressions for prefix filters and allocation parameters."""

from unittest.mock import patch
from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import override_settings, TestCase
from django.urls import reverse
import netaddr
from rest_framework.test import APIClient

from nautobot.extras.models import Status
from nautobot.ipam.filters import MultiValuePrefixFilter
from nautobot.ipam.models import IPAddress, Namespace, Prefix


class IPAMInputValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="ipam-input-validation", is_superuser=True)
        cls.status = Status.objects.create(name="IPAM input validation status")
        cls.status.content_types.add(
            ContentType.objects.get_for_model(Prefix), ContentType.objects.get_for_model(IPAddress)
        )
        cls.namespace = Namespace.objects.create(name="IPAM input validation namespace")
        cls.prefix = Prefix.objects.create(prefix="192.0.2.0/24", namespace=cls.namespace, status=cls.status)
        cls.prefix6 = Prefix.objects.create(prefix="2001:db8::/64", namespace=cls.namespace, status=cls.status)
        cls.ip = IPAddress.objects.create(address="192.0.2.1/24", parent=cls.prefix, status=cls.status)

    def setUp(self):
        self.client = APIClient(HTTP_HOST="nautobot.example.com")
        self.client.force_authenticate(self.user)

    def test_invalid_prefix_filters_return_field_errors(self):
        for endpoint, fields in (
            ("prefix", ("prefix", "within", "within_include", "contains", "parent")),
            ("ipaddress", ("prefix",)),
            ("vrfprefixassignment", ("prefix",)),
            ("prefixlocationassignment", ("prefix",)),
        ):
            for field in fields:
                for value in ("bad-prefix", "192.0.2.0/33", "2001:db8::/129", str(uuid4())):
                    with self.subTest(endpoint=endpoint, field=field, value=value):
                        response = self.client.get(
                            reverse(f"ipam-api:{endpoint}-list"), {field: [str(self.prefix.pk), value]}
                        )
                        self.assertEqual(response.status_code, 400, response.content)
                        self.assertIn(field, response.data)

    def test_contains_does_not_ignore_invalid_values(self):
        for values in (["bad-prefix"], ["192.0.2.0/24", "bad-prefix"], ["192.0.2.1", "bad-prefix"]):
            with self.subTest(values=values):
                response = self.client.get(reverse("ipam-api:prefix-list"), {"contains": values})
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn("contains", response.data)

    def test_prefix_filters_preserve_literal_and_uuid_matches(self):
        child = Prefix.objects.create(prefix="192.0.2.0/25", namespace=self.namespace, status=self.status)
        for field, values, expected in (
            ("prefix", [str(self.prefix.pk)], {self.prefix.pk}),
            ("prefix", ["192.0.2.0/24", "2001:db8::/64"], {self.prefix.pk, self.prefix6.pk}),
            ("within", [str(self.prefix.pk)], {child.pk}),
            ("within_include", [str(self.prefix.pk)], {self.prefix.pk, child.pk}),
            ("contains", [str(child.pk)], {self.prefix.pk, child.pk}),
            ("contains", ["192.0.2.1", "2001:db8::1"], {self.prefix.pk, child.pk, self.prefix6.pk}),
            ("parent", [str(self.prefix.pk)], {child.pk}),
            ("parent", ["192.0.2.0/24"], {child.pk}),
        ):
            with self.subTest(field=field, values=values):
                response = self.client.get(
                    reverse("ipam-api:prefix-list"), {field: values, "namespace": str(self.namespace.pk)}
                )
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual({obj["id"] for obj in response.data["results"]}, {str(pk) for pk in expected})

    def test_ip_prefix_filter_preserves_literal_and_uuid_matches(self):
        for value in ("192.0.2.0/24", str(self.prefix.pk), " 192.0.2.0/24 "):
            with self.subTest(value=value):
                response = self.client.get(reverse("ipam-api:ipaddress-list"), {"prefix": value})
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual([obj["id"] for obj in response.data["results"]], [str(self.ip.pk)])

    def test_prefix_field_preserves_widget_and_query_cost(self):
        class FilterForm(forms.Form):
            prefix = MultiValuePrefixFilter().field

        with self.assertNumQueries(0):
            self.assertEqual(FilterForm.base_fields["prefix"].clean(["192.0.2.0/24", "  "]), ["192.0.2.0/24"])
        form = FilterForm({"prefix": [str(self.prefix.pk)]})
        with self.assertNumQueries(1):
            self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["prefix"], ["192.0.2.0/24"])
        rendered = str(form["prefix"])
        self.assertIn("nautobot-select2-multi-value-char", rendered)
        self.assertIn(f'value="{self.prefix.pk}" selected', rendered)
        with self.assertNumQueries(1), self.assertRaises(ValidationError):
            FilterForm.base_fields["prefix"].clean([str(uuid4())])

    def test_prefix_allocation_rejects_invalid_lengths_before_allocation(self):
        for parent, invalid_length in (
            (self.prefix, -1),
            (self.prefix, 33),
            (self.prefix6, 129),
            (self.prefix, True),
            (self.prefix, "26"),
            (self.prefix, 26.5),
            (self.prefix, None),
        ):
            for bulk in (False, True):
                with self.subTest(parent=str(parent), length=invalid_length, bulk=bulk):
                    payload = {"prefix_length": invalid_length, "status": str(self.status.pk)}
                    if bulk:
                        payload = [{"prefix_length": 26, "status": str(self.status.pk)}, payload]
                    with patch.object(Prefix, "get_available_prefixes") as available:
                        response = self.client.post(
                            reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": parent.pk}),
                            payload,
                            format="json",
                        )
                    self.assertEqual(response.status_code, 400, response.content)
                    self.assertIn("prefix_length", response.data)
                    available.assert_not_called()

    def test_prefix_allocation_requires_length(self):
        response = self.client.post(
            reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": self.prefix.pk}), {}, format="json"
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("prefix_length", response.data)

    def test_allocation_rejects_non_object_entries(self):
        for action, availability in (("prefixes", "get_available_prefixes"), ("ips", "get_available_ips")):
            for payload in ("bad", 5, [None], [{"prefix_length": 26, "status": str(self.status.pk)}, "bad"]):
                with self.subTest(action=action, payload=payload):
                    with patch.object(Prefix, availability) as available:
                        response = self.client.post(
                            reverse(f"ipam-api:prefix-available-{action}", kwargs={"pk": self.prefix.pk}),
                            payload,
                            format="json",
                        )
                    self.assertEqual(response.status_code, 400, response.content)
                    available.assert_not_called()

    def test_allocation_rejects_invalid_ranges_before_calculating_availability(self):
        for parent, params in (
            (self.prefix, {"range_start": "2001:db8::1"}),
            (self.prefix, {"range_end": "2001:db8::1"}),
            (self.prefix6, {"range_start": "192.0.2.1"}),
            (self.prefix6, {"range_end": "192.0.2.1"}),
            (self.prefix, {"range_start": "192.0.1.255"}),
            (self.prefix, {"range_end": "192.0.3.0"}),
            (self.prefix, {"range_start": "192.0.2.20", "range_end": "192.0.2.10"}),
        ):
            for method in ("get", "post"):
                with self.subTest(parent=str(parent), params=params, method=method):
                    url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": parent.pk})
                    url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
                    with patch.object(Prefix, "get_available_ips") as available:
                        response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 400, response.content)
                    available.assert_not_called()

    def test_low_ipv6_addresses_preserve_family(self):
        prefix = Prefix.objects.create(prefix="::/120", namespace=self.namespace, status=self.status)
        response = self.client.get(
            reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk}),
            {"range_start": "::2", "range_end": "::2"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([obj["address"] for obj in response.data], ["::2/120"])

    def test_available_ips_supports_head_requests(self):
        response = self.client.head(reverse("ipam-api:prefix-available-ips", kwargs={"pk": self.prefix6.pk}))
        self.assertEqual(response.status_code, 200, response.content)

    @override_settings(PAGINATE_COUNT=2, MAX_PAGE_SIZE=3)
    def test_available_ip_limits_preserve_parsing_and_use_finite_counts(self):
        for parent in (self.prefix, self.prefix6):
            for params, expected in (
                ({}, 2),
                ({"limit": "0"}, 3),
                ({"limit": "-1"}, 2),
                ({"limit": "-10"}, 2),
                ({"limit": ""}, 2),
                ({"limit": "bad"}, 2),
                ({"limit": "1.0"}, 2),
                ({"limit": "1.5"}, 2),
                ({"limit": "1"}, 1),
                ({"limit": "100"}, 3),
                ({"limit": "9" * 30}, 3),
                ({"limit": ["0", "1"]}, 1),
                ({"limit": ["1", "0"]}, 3),
            ):
                with self.subTest(parent=str(parent), params=params):
                    self.assert_available_ip_count(parent, params, expected)

    def test_available_ip_limits_remain_finite_without_positive_settings(self):
        for default, maximum, expected in (
            (2, 0, 2),
            (2, None, 2),
            (0, 0, 50),
            (-1, 0, 50),
            (0, 3, 3),
            (5, 3, 3),
        ):
            with override_settings(PAGINATE_COUNT=default, MAX_PAGE_SIZE=maximum):
                for params in ({}, {"limit": "0"}, {"limit": "-1"}, {"limit": "bad"}):
                    with self.subTest(default=default, maximum=maximum, params=params):
                        self.assert_available_ip_count(self.prefix6, params, expected)

    def assert_available_ip_count(self, prefix, params, expected):
        """Fail immediately if enumeration exceeds the expected count, even for a large IPv6 prefix."""

        def addresses():
            first = netaddr.IPAddress(prefix.prefix.first, version=prefix.ip_version)
            for offset in range(1, expected + 1):
                yield first + offset
            self.fail("The action enumerated more addresses than the expected limit.")

        with patch.object(Prefix, "get_available_ips", return_value=addresses()):
            response = self.client.get(reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk}), params)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.data), expected)

    def test_bulk_prefix_allocation_preserves_generated_fields(self):
        for parent, length in ((self.prefix, 32), (self.prefix6, 128)):
            with self.subTest(parent=str(parent)):
                response = self.client.post(
                    reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": parent.pk}),
                    [{"prefix_length": length, "status": str(self.status.pk), "description": "allocated"}] * 2,
                    format="json",
                )
                self.assertEqual(response.status_code, 201, response.content)
                self.assertEqual(len(response.data), 2)
                self.assertEqual({obj["prefix_length"] for obj in response.data}, {length})
                self.assertEqual({obj["description"] for obj in response.data}, {"allocated"})
