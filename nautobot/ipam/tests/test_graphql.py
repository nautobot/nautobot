from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status

from nautobot.core.testing import APITestCase
from nautobot.extras.choices import DynamicGroupTypeChoices
from nautobot.extras.models import DynamicGroup
from nautobot.ipam.models import IPAddressRange


class TestPrefix(APITestCase):
    def setUp(self):
        super().setUp()
        self.api_url = reverse("graphql-api")
        self.add_permissions("ipam.view_prefix")

    def test_prefix_ip_version(self):
        """Test ip_version is available for a Prefix via GraphQL."""
        get_prefixes_query = """
        query {
            prefixes {
                prefix
                prefix_length
                ip_version
            }
        }
        """
        payload = {"query": get_prefixes_query}
        response = self.client.post(self.api_url, payload, format="json", **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prefixes = response.data["data"]["prefixes"]
        self.assertIsInstance(prefixes, list)
        self.assertGreater(len(prefixes), 0)

        for prefix in prefixes:
            self.assertIsInstance(prefix["prefix"], str)
            self.assertIsInstance(prefix["prefix_length"], int)
            self.assertIn(prefix["ip_version"], [4, 6])


class TestIPAddressRange(APITestCase):
    def setUp(self):
        super().setUp()
        self.api_url = reverse("graphql-api")
        self.add_permissions("ipam.view_ipaddressrange")

    def test_ip_address_range_fields(self):
        """Test start_address, end_address, and ip_version are available for an IPAddressRange via GraphQL."""
        get_ranges_query = """
        query {
            ip_address_ranges {
                start_address
                end_address
                ip_version
            }
        }
        """
        payload = {"query": get_ranges_query}
        response = self.client.post(self.api_url, payload, format="json", **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ranges = response.data["data"]["ip_address_ranges"]
        self.assertIsInstance(ranges, list)
        self.assertGreater(len(ranges), 0)

        for ip_range in ranges:
            self.assertIsInstance(ip_range["start_address"], str)
            self.assertIsInstance(ip_range["end_address"], str)
            self.assertIn(ip_range["ip_version"], [4, 6])

    def test_ip_address_range_dynamic_groups(self):
        """Test dynamic_groups resolver is available for an IPAddressRange via GraphQL."""
        ipaddressrange_ct = ContentType.objects.get_for_model(IPAddressRange)
        DynamicGroup.objects.create(
            name="DynamicGroup Test",
            content_type=ipaddressrange_ct,
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,
        )
        get_ranges_query = """
        query {
            ip_address_ranges {
                start_address
                dynamic_groups {
                    id
                    name
                }
            }
        }
        """
        payload = {"query": get_ranges_query}
        response = self.client.post(self.api_url, payload, format="json", **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ranges = response.data["data"]["ip_address_ranges"]
        self.assertIsInstance(ranges, list)

        for ip_range in ranges:
            self.assertIsInstance(ip_range["dynamic_groups"], list)
