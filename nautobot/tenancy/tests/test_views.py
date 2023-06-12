from nautobot.core.testing import ViewTestCases
from nautobot.extras.models import Tag
from nautobot.tenancy.models import Tenant, TenantGroup


class TenantGroupTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = TenantGroup

    @classmethod
    def setUpTestData(cls):
        cls.form_data = {
            "name": "Tenant Group X",
            "description": "A new tenant group",
        }

        cls.csv_data = (
            "name,description",
            "Tenant Group 4,Fourth tenant group",
            "Tenant Group 5,Fifth tenant group",
            "Tenant Group 6,Sixth tenant group",
            "Tenant Group 7,Seventh tenant group",
        )


class TenantTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Tenant

    @classmethod
    def setUpTestData(cls):
        tenant_groups = TenantGroup.objects.all()[:2]
        Tenant.objects.create(name="New Tenant", tenant_group=tenant_groups[0])

        cls.form_data = {
            "name": "Tenant X",
            "tenant_group": tenant_groups[1].pk,
            "description": "A new tenant",
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(Tenant)],
        }

        cls.csv_data = (
            "name,description",
            "Tenant 4,A tenant",
            "Tenant 5,A tenant",
            "Tenant 6,A tenant",
            "Tenant 7,A tenant",
        )

        cls.bulk_edit_data = {
            "tenant_group": tenant_groups[1].pk,
        }
