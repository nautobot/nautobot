from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.testing import ViewTestCases


class TenantGroupTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = TenantGroup

    @classmethod
    def setUpTestData(cls):

        TenantGroup.objects.create(name="Tenant Group 1", slug="tenant-group-1")
        TenantGroup.objects.create(name="Tenant Group 2", slug="tenant-group-2")
        TenantGroup.objects.create(name="Tenant Group 3", slug="tenant-group-3")
        TenantGroup.objects.create(name="Tenant Group 8")

        cls.form_data = {
            "name": "Tenant Group X",
            "slug": "tenant-group-x",
            "description": "A new tenant group",
        }

        cls.csv_data = (
            "name,slug,description",
            "Tenant Group 4,tenant-group-4,Fourth tenant group",
            "Tenant Group 5,tenant-group-5,Fifth tenant group",
            "Tenant Group 6,tenant-group-6,Sixth tenant group",
            "Tenant Group 7,,Seventh tenant group",
        )
        cls.slug_source = "name"
        cls.slug_test_object = "Tenant Group 8"


class TenantTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Tenant

    @classmethod
    def setUpTestData(cls):

        tenant_groups = (
            TenantGroup.objects.create(name="Tenant Group 1", slug="tenant-group-1"),
            TenantGroup.objects.create(name="Tenant Group 2", slug="tenant-group-2"),
        )

        Tenant.objects.create(name="Tenant 1", slug="tenant-1", group=tenant_groups[0])
        Tenant.objects.create(name="Tenant 2", slug="tenant-2", group=tenant_groups[0])
        Tenant.objects.create(name="Tenant 3", slug="tenant-3", group=tenant_groups[0])
        Tenant.objects.create(name="Tenant 8", group=tenant_groups[0])

        tags = cls.create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "name": "Tenant X",
            "slug": "tenant-x",
            "group": tenant_groups[1].pk,
            "description": "A new tenant",
            "comments": "Some comments",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "name,slug",
            "Tenant 4,tenant-4",
            "Tenant 5,tenant-5",
            "Tenant 6,tenant-6",
            "Tenant 7,",
        )

        cls.bulk_edit_data = {
            "group": tenant_groups[1].pk,
        }
        cls.slug_source = "name"
        cls.slug_test_object = "Tenant 8"
