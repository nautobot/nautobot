from django.db import connection
from django.test.utils import CaptureQueriesContext

from nautobot.core.testing import TestCase
from nautobot.dcim.models import Location


class TestInvalidateMaxTreeDepthSignal(TestCase):
    """Tests for the max tree depth cache invalidation signal."""

    def test_invalidate_max_tree_depth_without_tree_fields(self):
        """Test that max tree depth is not calculated by the invalidate_max_tree_depth signal."""
        # Ensure that the max_depth hasn't already been cached
        Location.objects.__dict__.pop("max_depth", None)
        location = Location.objects.first()
        with self.assertNumQueries(1):
            location.save()


class QuerySetAncestorTests(TestCase):
    """Tests for custom `TreeQuerySet.ancestors` method."""

    def test_empty_ancestors(self):
        """Test that `TreeQuerySet.ancestors` works even when there are no ancestors."""
        base_location_with_tree_fields = (
            Location.objects.with_tree_fields().filter(location_type__name="Campus").first()
        )
        base_location_without_tree_fields = (
            Location.objects.without_tree_fields().filter(location_type__name="Campus").first()
        )

        self.assertQuerysetEqual(
            base_location_with_tree_fields.ancestors(),
            base_location_without_tree_fields.ancestors(),
            msg="`TreeQuerySet.ancestors()` output doesn't match between custom and original implementation for empty ancestors list",
        )

    def test_basic_path_comparison(self):
        """Test that the custom `TreeQuerySet.ancestors` implementation matches the behaviour of the original one."""
        base_location_with_tree_fields = Location.objects.with_tree_fields().filter(location_type__name="Aisle").first()
        base_location_without_tree_fields = (
            Location.objects.without_tree_fields().filter(location_type__name="Aisle").first()
        )

        self.assertQuerysetEqualAndNotEmpty(
            base_location_with_tree_fields.ancestors(),
            base_location_without_tree_fields.ancestors(),
            msg="`TreeQuerySet.ancestors()` output doesn't match between custom and original implementation",
        )

    def test_tree_annotations_not_present(self):
        """Test that using the custom `TreeQuerySet.ancestors` implementation the tree annotations aren't present."""
        base_location_without_tree_fields = (
            Location.objects.without_tree_fields().filter(location_type__name="Aisle").first()
        )
        ancestors_without_tree_fields = base_location_without_tree_fields.ancestors()
        self.assertFalse(
            hasattr(ancestors_without_tree_fields.first(), "tree_depth"), "Tree annotations should not be present."
        )


class QuerySetCountTests(TestCase):
    """Test for the custom `TreeQuerySet.count` method."""

    def test_basic(self):
        """Test that `TreeQuerySet.count` doesn't include the CTE in the query even with tree fields in the qs."""
        with CaptureQueriesContext(connection) as ctx:
            qs = Location.objects.with_tree_fields()
            qs.count()
        for query in ctx.captured_queries:
            # Guard clause in case there are ever any queries in this capture that are not the query corresponding to
            # the `count`.
            if 'SELECT COUNT(*) AS "__count" FROM "dcim_location"' not in query["sql"]:
                continue
            if "WITH RECURSIVE __tree" in query["sql"] or "WITH RECURSIVE __rank_table" in query["sql"]:
                self.fail(f"`TreeQuerySet.count` should not include the CTE in the query. Query:\n{query['sql']}")

        # Finally, we also want to make sure that tree fields are still present in the queryset after we have run count
        with CaptureQueriesContext(connection) as ctx:
            list(qs.all())
        found_cte = False
        for query in ctx.captured_queries:
            if "WITH RECURSIVE __tree" in query["sql"] or "WITH RECURSIVE __rank_table" in query["sql"]:
                found_cte = True
        if not found_cte:
            self.fail("`TreeQuerySet.count` failed to re-add tree fields ot the queryset after removing them")
