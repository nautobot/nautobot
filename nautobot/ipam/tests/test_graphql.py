from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from nautobot.extras.models import Status
from nautobot.ipam.models import Prefix
from nautobot.utilities.testing import APITestCase


class TestPrefix(APITestCase):
    def setUp(self):
        super().setUp()
        self.api_url = reverse("graphql-api")
        self.statuses = Status.objects.get_for_model(Prefix)
        self.prefixv4 = Prefix.objects.create(prefix="10.0.0.0/24", status=self.statuses.get(slug="active"))
        self.prefixv6 = Prefix.objects.create(prefix="2001:DB8::/32", status=self.statuses.get(slug="active"))
        self.prefixv4.validated_save()
        self.prefixv6.validated_save()

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_prefix_family(self):
        """Test family is available for a Prefix via GraphQL."""
        get_prefixes_query = """
        query {
            prefixes {
                prefix
                prefix_length
                family
            }
        }
        """
        payload = {"query": get_prefixes_query}
        response = self.client.post(self.api_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prefixes = response.data["data"]["prefixes"]
        self.assertIsInstance(prefixes, list)
        self.assertGreater(len(prefixes), 0)

        for prefix in prefixes:
            self.assertIsInstance(prefix["prefix"], str)
            self.assertIsInstance(prefix["prefix_length"], int)
            self.assertIn(prefix["family"], [4, 6])
