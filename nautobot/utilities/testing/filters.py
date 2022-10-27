import random

from django.db.models import Count
from django.test import tag
from nautobot.utilities.testing.views import TestCase

from nautobot.tenancy.models import Tenant, TenantGroup


@tag("unit")
class FilterTestCases:
    class BaseFilterTestCase(TestCase):
        """Base class for testing of FilterSets."""

        def get_filterset_test_values(self, field_name, queryset=None):
            """Returns a list of distinct values from the requested queryset field to use in filterset tests.

            Returns a list for use in testing multiple choice filters. The size of the returned list is random
            but will contain at minimum 2 unique values. The list of values will match at least 2 instances when
            passed to the queryset's filter(field_name__in=[]) method but will fail to match at least one instance.

            Args:
                field_name: The name of the field to retrieve test values from.
                queryset: The queryset to retrieve test values. Defaults to `self.queryset`.

            Returns:
                list: A list of unique values derived from the queryset.

            Raises:
                ValueError: Raised if unable to find a combination of 2 or more unique values
                    to filter the queryset to a subset of the total instances.
            """
            test_values = []
            if queryset is None:
                queryset = self.queryset
            qs_count = queryset.count()
            values_with_count = queryset.values(field_name).annotate(count=Count(field_name)).order_by("count")
            for value in values_with_count:
                # randomly break out of loop after 2 values have been selected
                if len(test_values) > 1 and random.choice([True, False]):
                    break
                if value["count"] < qs_count:
                    qs_count -= value["count"]
                    test_values.append(value[field_name])

            if len(test_values) < 2:
                raise ValueError(
                    f"Cannot find valid test data for {queryset.model._meta.object_name} field {field_name}"
                )
            return test_values

    class FilterTestCase(BaseFilterTestCase):
        """Add common tests for all FilterSets."""

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
