from django.urls import reverse

from nautobot.core.testing import APITestCase, APIViewTestCases
from nautobot.tenancy.models import Tenant, TenantGroup


class AppTest(APITestCase):
    def test_root(self):
        url = reverse("tenancy-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


class TenantGroupTest(APIViewTestCases.APIViewTestCase, APIViewTestCases.TreeModelAPIViewTestCaseMixin):
    model = TenantGroup
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        cls.create_data = [
            {
                "name": "Tenant Group 4",
                "parent": TenantGroup.objects.last().pk,
            },
            {
                "name": "Tenant Group 5",
                "parent": TenantGroup.objects.last().pk,
            },
            {
                "name": "Tenant Group 6",
            },
            {
                "name": "Tenant Group 7",
            },
        ]


class TenantTest(APIViewTestCases.APIViewTestCase):
    model = Tenant
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        Tenant.objects.create(name="Delete Me 1")
        Tenant.objects.create(name="Delete Me 2")
        Tenant.objects.create(name="Delete Me 3")
        cls.create_data = [
            {
                "name": "Tenant 4",
                "tenant_group": TenantGroup.objects.first().pk,
            },
            {
                "name": "Tenant 5",
                "tenant_group": TenantGroup.objects.last().pk,
            },
            {
                "name": "Tenant 6",
            },
            {
                "name": "Tenant 7",
            },
        ]
