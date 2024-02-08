from nautobot.core.testing import TestCase
from nautobot.dcim.models import Location


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

        self.assertEqual(
            list(base_location_with_tree_fields.ancestors()),
            (base_location_without_tree_fields.ancestors()),
            "`TreeQuerySet.ancestors()` output doesn't match between custom and original implementation for empty ancestors list",
        )

    def test_basic_path_comparison(self):
        """Test that the custom `TreeQuerySet.ancestors` implementation matches the behaviour of the original one."""
        base_location_with_tree_fields = Location.objects.with_tree_fields().filter(location_type__name="Aisle").first()
        base_location_without_tree_fields = (
            Location.objects.without_tree_fields().filter(location_type__name="Aisle").first()
        )

        self.assertEqual(
            list(base_location_with_tree_fields.ancestors()),
            (base_location_without_tree_fields.ancestors()),
            "`TreeQuerySet.ancestors()` output doesn't match between custom and original implementation",
        )

    def test_tree_annotations_not_present(self):
        """Test that using the custom `TreeQuerySet.ancestors` implementation the tree annotations aren't present."""
        base_location_without_tree_fields = (
            Location.objects.without_tree_fields().filter(location_type__name="Aisle").first()
        )
        self.assertFalse(
            hasattr(base_location_without_tree_fields, "tree_depth"), "Tree annotations should not be present."
        )
