from django.core.cache import cache

from tree_queries.models import TreeNode
from tree_queries.query import TreeManager as TreeManager_
from tree_queries.query import TreeQuerySet as TreeQuerySet_

from nautobot.core.models import querysets, BaseManager


class TreeQuerySet(TreeQuerySet_, querysets.RestrictedQuerySet):
    """
    Combine django-tree-queries' TreeQuerySet with our RestrictedQuerySet for permissions enforcement.
    """

    def max_tree_depth(self):
        """
        Get the maximum depth of any tree in this queryset.
        """
        deepest = self.with_tree_fields().extra(order_by=["-__tree.tree_depth"]).first()
        if deepest is not None:
            return deepest.tree_depth
        return 0


class TreeManager(TreeManager_, BaseManager.from_queryset(TreeQuerySet)):
    """
    Extend django-tree-queries' TreeManager to incorporate RestrictedQuerySet.
    """

    _with_tree_fields = True
    use_in_migrations = True


class TreeModel(TreeNode):
    """
    Nautobot-specific base class for models that exist in a self-referential tree.
    """

    objects = TreeManager()

    class Meta:
        abstract = True

    @property
    def display(self):
        """
        By default, TreeModels display their full ancestry for clarity.

        As this is an expensive thing to calculate, we cache it for a few seconds in the case of repeated lookups.
        """
        if not hasattr(self, "name"):
            raise NotImplementedError("default TreeModel.display implementation requires a `name` attribute!")
        cache_key = f"{self.__class__.__name__}.{self.id}.display"
        display_str = cache.get(cache_key, "")
        if display_str:
            return display_str
        try:
            if self.parent is not None:
                display_str = self.parent.display + " → "
        except self.DoesNotExist:
            # Expected to occur at times during bulk-delete operations
            pass
        finally:
            display_str += self.name
            cache.set(cache_key, display_str, 5)
            return display_str  # pylint: disable=lost-exception
