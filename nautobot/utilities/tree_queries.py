from django.db.models import Manager
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
