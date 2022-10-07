from django.test import tag
from nautobot.utilities.testing.views import TestCase

from nautobot.tenancy.models import Tenant, TenantGroup


@tag("unit")
class FilterTestCases:
    class FilterTestCase(TestCase):
        """Base class for testing of FilterSets."""

        queryset = None
        filterset = None

        def test_id(self):
            """Verify that the filterset supports filtering by id."""
            params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
            filterset = self.filterset(params, self.queryset)
            self.assertTrue(filterset.is_valid())
            self.assertEqual(filterset.qs.count(), 2)

        def test_invalid_filter(self):
            """Verify that the filterset reports as invalid when initialized with an unsupported filter parameter."""
            params = {"ice_cream_flavor": ["chocolate"]}
            self.assertFalse(self.filterset(params, self.queryset).is_valid())

    class NameSlugFilterTestCase(FilterTestCase):
        """Add simple tests for filtering by name and by slug."""

        def test_name(self):
            """Verify that the filterset supports filtering by name."""
            params = {"name": self.queryset.values_list("name", flat=True)[:2]}
            filterset = self.filterset(params, self.queryset)
            self.assertTrue(filterset.is_valid())
            self.assertEqual(filterset.qs.count(), 2)

        def test_slug(self):
            """Verify that the filterset supports filtering by slug."""
            params = {"slug": self.queryset.values_list("slug", flat=True)[:2]}
            filterset = self.filterset(params, self.queryset)
            self.assertTrue(filterset.is_valid())
            self.assertEqual(filterset.qs.count(), 2)

    class TenancyFilterTestCaseMixin(TestCase):
        """Add test cases for tenant and tenant-group filters."""

        tenancy_related_name = ""

        def test_tenant(self):
            tenants = list(Tenant.objects.filter(**{f"{self.tenancy_related_name}__isnull": False}))[:2]
            params = {"tenant_id": [tenants[0].pk, tenants[1].pk]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(tenant__in=tenants), ordered=False
            )
            params = {"tenant": [tenants[0].slug, tenants[1].slug]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(tenant__in=tenants), ordered=False
            )

        def test_tenant_group(self):
            tenant_groups = list(
                TenantGroup.objects.filter(
                    tenants__isnull=False, **{f"tenants__{self.tenancy_related_name}__isnull": False}
                )
            )[:2]
            tenant_groups_including_children = []
            for tenant_group in tenant_groups:
                tenant_groups_including_children += tenant_group.get_descendants(include_self=True)

            params = {"tenant_group_id": [tenant_groups[0].pk, tenant_groups[1].pk]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(tenant__group__in=tenant_groups_including_children),
                ordered=False,
            )

            params = {"tenant_group": [tenant_groups[0].slug, tenant_groups[1].slug]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(tenant__group__in=tenant_groups_including_children),
                ordered=False,
            )
