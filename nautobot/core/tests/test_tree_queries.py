from django.core.cache import cache
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

        with CaptureQueriesContext(connection) as ctx:
            location.save()
            captured_tree_cte_queries = [
                query["sql"] for query in ctx.captured_queries if "WITH RECURSIVE" in query["sql"]
            ]
        allowed_number_of_tree_queries = 0  # We don't expect any tree queries to be run
        _query_separator = "\n" + ("-" * 10) + "\n" + "NEXT QUERY" + "\n" + ("-" * 10)
        self.assertEqual(
            len(captured_tree_cte_queries),
            allowed_number_of_tree_queries,
            f"The CTE tree was calculated a different number of times ({len(captured_tree_cte_queries)})"
            f" than allowed ({allowed_number_of_tree_queries})."
            f" The following queries were used:\n{_query_separator.join(captured_tree_cte_queries)}",
        )


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


class TreeModelCachedDescendantsPKsTests(TestCase):
    """Tests for the custom `TreeModel.cached_descendants_pks` method."""

    def setUp(self):
        super().setUp()
        cache.delete_pattern("*cacheable_descendants_pks*")

    def tearDown(self):
        cache.delete_pattern("*cacheable_descendants_pks*")
        super().tearDown()

    def test_cache_usage(self):
        loc = Location.objects.without_tree_fields().exclude(children__isnull=True).first()
        self.add_permissions("dcim.view_location")
        # Force initial population of user permissions cache
        Location.objects.restrict(self.user, "view")

        for kwargs in [
            {"include_self": True},
            {"include_self": False},
            {"include_self": True, "restrict_to_user": self.user},
            {"include_self": False, "restrict_to_user": self.user},
        ]:
            with self.subTest(**kwargs):
                # Different kwargs, so should not hit the cache
                with self.assertNumQueries(1):
                    cacheable_descendants_pks = loc.cacheable_descendants_pks(**kwargs)
                self.assertNotEqual(cacheable_descendants_pks, [])
                # Same kwargs, should hit the cache
                with self.assertNumQueries(0):
                    cached_descendants_pks = loc.cacheable_descendants_pks(**kwargs)
                self.assertEqual(cacheable_descendants_pks, cached_descendants_pks)

    def test_cache_cleared_on_parent_change(self):
        loc = Location.objects.without_tree_fields().exclude(parent__isnull=True).exclude(children__isnull=True).first()
        old_parent = loc.parent

        with self.assertNumQueries(1):
            initial_old_parent_descendants_pks = old_parent.cacheable_descendants_pks()
        with self.assertNumQueries(1):
            initial_descendants_pks = loc.cacheable_descendants_pks()

        self.assertIn(loc.pk, initial_old_parent_descendants_pks)

        new_parent = (
            Location.objects.filter(location_type=old_parent.location_type)
            .exclude(pk__in=[old_parent.pk, loc.pk])
            .first()
        )
        self.assertIsNotNone(new_parent)
        with self.assertNumQueries(1):
            initial_new_parent_descendants_pks = new_parent.cacheable_descendants_pks()
        loc.parent = new_parent
        loc.save()

        with self.assertNumQueries(1):
            old_parent_descendants_pks = old_parent.cacheable_descendants_pks()
        self.assertNotIn(loc.pk, old_parent_descendants_pks)
        self.assertNotEqual(old_parent_descendants_pks, initial_old_parent_descendants_pks)

        with self.assertNumQueries(1):
            new_parent_descendants_pks = new_parent.cacheable_descendants_pks()
        self.assertIn(loc.pk, new_parent_descendants_pks)
        self.assertNotEqual(new_parent_descendants_pks, initial_new_parent_descendants_pks)

        with self.assertNumQueries(0):
            descendants_pks = loc.cacheable_descendants_pks()
        self.assertEqual(descendants_pks, initial_descendants_pks)
