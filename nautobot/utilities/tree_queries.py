from django.db.models import Manager
from tree_queries.models import TreeNode
from tree_queries.query import TreeManager as TreeManager_
from tree_queries.query import TreeQuerySet as TreeQuerySet_

from nautobot.utilities import querysets


class TreeQuerySet(TreeQuerySet_, querysets.RestrictedQuerySet):
    """
    Combine django-tree-queries' TreeQuerySet with our RestrictedQuerySet for permissions enforcement.
    """

    def max_tree_depth(self):
        """
        Get the maximum depth of any tree in this queryset.
        """
        return self.with_tree_fields().extra(order_by=["-__tree.tree_depth"]).first().tree_depth


class TreeManager(Manager.from_queryset(TreeQuerySet), TreeManager_):
    """
    Extend django-tree-queries' TreeManager to incorporate RestrictedQuerySet.
    """

    _with_tree_fields = True


class TreeModel(TreeNode):
    """
    Nautobot-specific base class for models that exist in a self-referential tree.
    """

    objects = TreeManager()

    class Meta:
        abstract = True

    @property
    def display(self):
        """By default, TreeModels display their full ancestry for clarity."""
        if not hasattr(self, "name"):
            raise NotImplementedError("default TreeModel.display implementation requires a `name` attribute!")
        display_str = ""
        try:
            for ancestor in self.ancestors():
                display_str += ancestor.name + " → "
        except self.DoesNotExist:
            # Expected to occur at times during bulk-delete operations
            pass
        finally:
            display_str += self.name
            return display_str  # pylint: disable=lost-exception
