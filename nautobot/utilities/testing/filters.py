from django.test import tag
from nautobot.utilities.testing.views import TestCase


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
