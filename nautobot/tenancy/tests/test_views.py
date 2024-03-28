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

        cls.bulk_edit_data = {
            "tenant_group": tenant_groups[1].pk,
        }
