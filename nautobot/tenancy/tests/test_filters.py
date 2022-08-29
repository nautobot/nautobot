from nautobot.dcim.models import Location, LocationType, Site
from nautobot.extras.models import Status
from nautobot.tenancy.filters import TenantGroupFilterSet, TenantFilterSet
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.testing import FilterTestCases


class TenantGroupTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = TenantGroup.objects.all()
    filterset = TenantGroupFilterSet

    @classmethod
    def setUpTestData(cls):

        parent_tenant_groups = (
            TenantGroup.objects.create(name="Parent Tenant Group 1", slug="parent-tenant-group-1"),
            TenantGroup.objects.create(name="Parent Tenant Group 2", slug="parent-tenant-group-2"),
            TenantGroup.objects.create(name="Parent Tenant Group 3", slug="parent-tenant-group-3"),
        )

        TenantGroup.objects.create(
            name="Tenant Group 1",
            slug="tenant-group-1",
            parent=parent_tenant_groups[0],
            description="A",
        )
        TenantGroup.objects.create(
            name="Tenant Group 2",
            slug="tenant-group-2",
            parent=parent_tenant_groups[1],
            description="B",
        )
        TenantGroup.objects.create(
            name="Tenant Group 3",
            slug="tenant-group-3",
            parent=parent_tenant_groups[2],
            description="C",
        )

    def test_description(self):
        params = {"description": ["A", "B"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_parent(self):
        parent_groups = TenantGroup.objects.filter(name__startswith="Parent")[:2]
        params = {"parent_id": [parent_groups[0].pk, parent_groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"parent": [parent_groups[0].slug, parent_groups[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class TenantTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Tenant.objects.all()
    filterset = TenantFilterSet

    @classmethod
    def setUpTestData(cls):

        tenant_groups = (
            TenantGroup.objects.create(name="Tenant Group 1", slug="tenant-group-1"),
            TenantGroup.objects.create(name="Tenant Group 2", slug="tenant-group-2"),
            TenantGroup.objects.create(name="Tenant Group 3", slug="tenant-group-3"),
        )

        tenants = (
            Tenant.objects.create(name="Tenant 1", slug="tenant-1", group=tenant_groups[0]),
            Tenant.objects.create(name="Tenant 2", slug="tenant-2", group=tenant_groups[1]),
            Tenant.objects.create(name="Tenant 3", slug="tenant-3", group=tenant_groups[2]),
        )

        active = Status.objects.get(name="Active")
        site = Site.objects.create(name="Site 1", status=active)
        location_type = LocationType.objects.create(name="Root Type")
        Location.objects.create(name="Root 1", location_type=location_type, site=site, status=active, tenant=tenants[0])
        Location.objects.create(name="Root 2", location_type=location_type, site=site, status=active, tenant=tenants[1])

    def test_group(self):
        group = TenantGroup.objects.all()[:2]
        params = {"group_id": [group[0].pk, group[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"group": [group[0].slug, group[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_locations(self):
        params = {"locations": [Location.objects.first().pk, Location.objects.last().slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_locations(self):
        params = {"has_locations": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"has_locations": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)
