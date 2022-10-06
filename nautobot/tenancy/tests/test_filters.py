from nautobot.dcim.models import Location, LocationType, Site
from nautobot.extras.models import Status
from nautobot.tenancy.filters import TenantGroupFilterSet, TenantFilterSet
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.testing import FilterTestCases


class TenantGroupTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = TenantGroup.objects.all()
    filterset = TenantGroupFilterSet

    def test_description(self):
        params = {
            "description": TenantGroup.objects.exclude(description__exact="").values_list("description", flat=True)[:2]
        }
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_parent(self):
        parent_groups = TenantGroup.objects.filter(children__isnull=False)
        params = {"parent_id": [parent_groups[0].pk, parent_groups[1].pk]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            TenantGroup.objects.filter(parent__in=[parent_groups[0], parent_groups[1]]).count(),
        )
        params = {"parent": [parent_groups[0].slug, parent_groups[1].slug]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            TenantGroup.objects.filter(parent__in=[parent_groups[0], parent_groups[1]]).count(),
        )


class TenantTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Tenant.objects.all()
    filterset = TenantFilterSet
    fixtures = ("status",)

    @classmethod
    def setUpTestData(cls):
        active = Status.objects.get(name="Active")
        site = Site.objects.create(name="Site 1", status=active)
        location_type = LocationType.objects.create(name="Root Type")
        Location.objects.create(
            name="Root 1", location_type=location_type, site=site, status=active, tenant=cls.queryset[0]
        )
        Location.objects.create(
            name="Root 2", location_type=location_type, site=site, status=active, tenant=cls.queryset[1]
        )

    def test_group(self):
        groups = list(TenantGroup.objects.filter(tenants__isnull=False))[:2]
        params = {"group_id": [groups[0].pk, groups[1].pk]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(group__in=groups).count(),
        )
        params = {"group": [groups[0].slug, groups[1].slug]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(group__in=groups).count(),
        )

    def test_locations(self):
        params = {"locations": [Location.objects.first().pk, Location.objects.last().slug]}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(locations__in=[Location.objects.first(), Location.objects.last()]).count(),
        )

    def test_has_locations(self):
        params = {"has_locations": True}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(locations__isnull=False).count(),
        )
        params = {"has_locations": False}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            self.queryset.filter(locations__isnull=True).count(),
        )

    def test_search(self):
        params = {"q": self.queryset.first().name}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset(params, self.queryset).qs.first(), self.queryset.first())
