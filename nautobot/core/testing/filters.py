import random

from django.db.models import Count
from django.test import tag

from nautobot.core.filters import RelatedMembershipBooleanFilter
from nautobot.core.models.generics import PrimaryModel
from nautobot.core.testing import views
from nautobot.tenancy import models


@tag("unit")
class FilterTestCases:
    class BaseFilterTestCase(views.TestCase):
        """Base class for testing of FilterSets."""

        def get_filterset_test_values(self, field_name, queryset=None):
            """Returns a list of distinct values from the requested queryset field to use in filterset tests.

            Returns a list for use in testing multiple choice filters. The size of the returned list is random
            but will contain at minimum 2 unique values. The list of values will match at least 2 instances when
            passed to the queryset's filter(field_name__in=[]) method but will fail to match at least one instance.

            Args:
                field_name (str): The name of the field to retrieve test values from.
                queryset (QuerySet): The queryset to retrieve test values. Defaults to `self.queryset`.

            Returns:
                (list): A list of unique values derived from the queryset.

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
                if value[field_name] and value["count"] < qs_count:
                    qs_count -= value["count"]
                    test_values.append(str(value[field_name]))

            if len(test_values) < 2:
                raise ValueError(
                    f"Cannot find enough valid test data for {queryset.model._meta.object_name} field {field_name} "
                    f"(found {len(test_values)} option(s): {test_values}) but need at least 2 of them"
                )
            return test_values

    class FilterTestCase(BaseFilterTestCase):
        """Add common tests for all FilterSets."""

        queryset = None
        filterset = None

        # list of filters to be tested by `test_filters_generic`
        # list of iterables with filter name and optional field name
        # example:
        #   generic_filter_tests = [
        #       ["filter1"],
        #       ["filter2", "field2__name"],
        #   ]
        generic_filter_tests = []

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

        def test_filters_generic(self):
            """Test all multiple choice filters declared in `self.generic_filter_tests`.

            This test uses `get_filterset_test_values()` to retrieve a valid set of test data and asserts
            that the filterset filter output matches the corresponding queryset filter.
            The majority of Nautobot filters use conjoined=False, so the extra logic to support conjoined=True has not
            been implemented here. TagFilter and similar "AND" filters are not supported.

            Examples:
                Multiple tests can be performed for the same filter by adding multiple entries in
                `generic_filter_tests` with explicit field names.
                For example, to test a NaturalKeyOrPKMultipleChoiceFilter, use:
                    generic_filter_tests = (
                        ["filter_name", "field_name__name"],
                        ["filter_name", "field_name__id"],
                    )

                If a field name is not declared, the filter name will be used for the field name:
                    generic_filter_tests = (
                        ["devices"],
                    )
                This expects a field named `devices` on the model and a filter named `devices` on the filterset.
            """
            if not self.generic_filter_tests:
                self.skipTest("No generic_filter_tests defined?")

            for test in self.generic_filter_tests:
                filter_name = test[0]
                field_name = test[-1]  # default to filter_name if a second list item was not supplied
                with self.subTest(f"{self.filterset.__name__} filter {filter_name} ({field_name})"):
                    test_data = self.get_filterset_test_values(field_name)
                    params = {filter_name: test_data}
                    filterset_result = self.filterset(params, self.queryset).qs
                    qs_result = self.queryset.filter(**{f"{field_name}__in": test_data}).distinct()
                    self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result, ordered=False)

        def test_boolean_filters_generic(self):
            """Test all `RelatedMembershipBooleanFilter` filters found in `self.filterset.get_filters()`
            except for the ones with custom filter logic defined in its `method` attribute.

            This test asserts that `filter=True` matches `self.queryset.filter(field__isnull=False)` and
            that `filter=False` matches `self.queryset.filter(field__isnull=True)`.
            """
            for filter_name, filter_object in self.filterset.get_filters().items():
                if not isinstance(filter_object, RelatedMembershipBooleanFilter):
                    continue
                if filter_object.method is not None:
                    continue
                field_name = filter_object.field_name
                with self.subTest(f"{self.filterset.__name__} RelatedMembershipBooleanFilter {filter_name} (True)"):
                    filterset_result = self.filterset({filter_name: True}, self.queryset).qs
                    qs_result = self.queryset.filter(**{f"{field_name}__isnull": False}).distinct()
                    self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)
                with self.subTest(f"{self.filterset.__name__} RelatedMembershipBooleanFilter {filter_name} (False)"):
                    filterset_result = self.filterset({filter_name: False}, self.queryset).qs
                    qs_result = self.queryset.filter(**{f"{field_name}__isnull": True}).distinct()
                    self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)

        def test_tags_filter(self):
            """Test the `tags` filter which should be present on all PrimaryModel filtersets."""
            if not issubclass(self.queryset.model, PrimaryModel):
                self.skipTest("Not a PrimaryModel")

            # Find an instance with at least two tags (should be common given our factory design)
            for instance in list(self.queryset):
                if len(instance.tags.all()) >= 2:
                    tags = list(instance.tags.all()[:2])
                    break
            else:
                self.fail(f"Couldn't find any {self.queryset.model._meta.object_name} with at least two Tags.")
            params = {"tags": [tags[0].name, tags[1].pk]}
            filterset_result = self.filterset(params, self.queryset).qs
            # Tags is an AND filter not an OR filter
            qs_result = self.queryset.filter(tags=tags[0]).filter(tags=tags[1]).distinct()
            self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)

    class NameOnlyFilterTestCase(FilterTestCase):
        """Add simple tests for filtering by name."""

        def test_name(self):
            """Verify that the filterset supports filtering by name."""
            params = {"name": list(self.queryset.values_list("name", flat=True)[:2])}
            filterset = self.filterset(params, self.queryset)
            self.assertTrue(filterset.is_valid())
            self.assertQuerysetEqualAndNotEmpty(
                filterset.qs.order_by("name"), self.queryset.filter(name__in=params["name"]).order_by("name")
            )

    class NameSlugFilterTestCase(NameOnlyFilterTestCase):
        """Add simple tests for filtering by name and by slug."""

        def test_slug(self):
            """Verify that the filterset supports filtering by slug."""
            params = {"slug": self.queryset.values_list("slug", flat=True)[:2]}
            filterset = self.filterset(params, self.queryset)
            self.assertTrue(filterset.is_valid())
            self.assertEqual(filterset.qs.count(), 2)

    class TenancyFilterTestCaseMixin(views.TestCase):
        """Add test cases for tenant and tenant-group filters."""

        tenancy_related_name = ""

        def test_tenant(self):
            tenants = list(models.Tenant.objects.filter(**{f"{self.tenancy_related_name}__isnull": False}))[:2]
            params = {"tenant_id": [tenants[0].pk, tenants[1].pk]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(tenant__in=tenants), ordered=False
            )
            params = {"tenant": [tenants[0].name, tenants[1].name]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs, self.queryset.filter(tenant__in=tenants), ordered=False
            )

        def test_tenant_group(self):
            tenant_groups = list(
                models.TenantGroup.objects.filter(
                    tenants__isnull=False, **{f"tenants__{self.tenancy_related_name}__isnull": False}
                )
            )[:2]
            tenant_groups_including_children = []
            for tenant_group in tenant_groups:
                tenant_groups_including_children += tenant_group.descendants(include_self=True)

            params = {"tenant_group": [tenant_groups[0].pk, tenant_groups[1].pk]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(tenant__tenant_group__in=tenant_groups_including_children),
                ordered=False,
            )

            params = {"tenant_group": [tenant_groups[0].name, tenant_groups[1].name]}
            self.assertQuerysetEqual(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(tenant__tenant_group__in=tenant_groups_including_children),
                ordered=False,
            )
