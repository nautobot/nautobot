from nautobot.extras.models import Tag
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.testing import ViewTestCases


class TenantGroupTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = TenantGroup

    @classmethod
    def setUpTestData(cls):
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

        tenant_groups = TenantGroup.objects.all()[:2]

        Tenant.objects.create(name="Tenant 8", group=tenant_groups[0])

        cls.form_data = {
            "name": "Tenant X",
            "slug": "tenant-x",
            "group": tenant_groups[1].pk,
            "description": "A new tenant",
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(Tenant)],
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

    def get_deletable_object_pks(self):
        tenants = [
            Tenant.objects.create(name="Deletable Tenant 1"),
            Tenant.objects.create(name="Deletable Tenant 2"),
            Tenant.objects.create(name="Deletable Tenant 3"),
        ]
        return [t.pk for t in tenants]
