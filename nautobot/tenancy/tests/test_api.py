from django.urls import reverse

from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.testing import APITestCase, APIViewTestCases


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("tenancy-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


class TenantGroupTest(APIViewTestCases.APIViewTestCase):
    model = TenantGroup
    brief_fields = ["_depth", "display", "id", "name", "slug", "tenant_count", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):
        cls.create_data = [
            {
                "name": "Tenant Group 4",
                "slug": "tenant-group-4",
                "parent": TenantGroup.objects.last().pk,
            },
            {
                "name": "Tenant Group 5",
                "slug": "tenant-group-5",
                "parent": TenantGroup.objects.last().pk,
            },
            {
                "name": "Tenant Group 6",
                "slug": "tenant-group-6",
            },
            {
                "name": "Tenant Group 7",
            },
        ]


class TenantTest(APIViewTestCases.APIViewTestCase):
    model = Tenant
    brief_fields = ["display", "id", "name", "slug", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):
        Tenant.objects.create(name="Delete Me 1")
        Tenant.objects.create(name="Delete Me 2")
        Tenant.objects.create(name="Delete Me 3")
        cls.create_data = [
            {
                "name": "Tenant 4",
                "slug": "tenant-4",
                "group": TenantGroup.objects.first().pk,
            },
            {
                "name": "Tenant 5",
                "slug": "tenant-5",
                "group": TenantGroup.objects.last().pk,
            },
            {
                "name": "Tenant 6",
                "slug": "tenant-6",
            },
            {
                "name": "Tenant 7",
            },
        ]
