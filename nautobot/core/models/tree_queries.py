from functools import cached_property

from django.core.cache import cache
from tree_queries.models import TreeNode
from tree_queries.query import TreeManager as TreeManager_, TreeQuerySet as TreeQuerySet_

from nautobot.core.models import BaseManager, querysets


class TreeQuerySet(TreeQuerySet_, querysets.RestrictedQuerySet):
    """
    Combine django-tree-queries' TreeQuerySet with our RestrictedQuerySet for permissions enforcement.
    """

    def ancestors(self, of, *, include_self=False):
        """Custom ancestors method for optimization purposes.

        Dynamically computes ancestors either through the tree or through the `parent` foreign key depending on whether
        tree fields are present on `of`.
        """
        # If `of` has `tree_depth` defined, i.e. if it was retrieved from the database on a queryset where tree fields
        # were enabled (see `TreeQuerySet.with_tree_fields` and `TreeQuerySet.without_tree_fields`), use the default
        # implementation from `tree_queries.query.TreeQuerySet`.
        # Furthermore, if `of` doesn't have a parent field we also have to defer to the tree-based implementation which
        # will then annotate the tree fields and proceed as usual.
        if hasattr(of, "tree_depth") or not hasattr(of, "parent"):
            return super().ancestors(of, include_self=include_self)
        # In the other case, traverse the `parent` foreign key until the root.
        ancestors = []
        if include_self:
            ancestors.append(of)
        while of := of.parent:
            # Insert in reverse order so that the root is the first element
            ancestors.insert(0, of)
        return ancestors

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

    @cached_property
    def max_depth(self):
        return self.max_tree_depth()


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
