from django.db.models import Manager
from tree_queries.query import TreeManager as TreeManager_
from tree_queries.query import TreeQuerySet as TreeQuerySet_

from nautobot.utilities import querysets


class TreeQuerySet(TreeQuerySet_, querysets.RestrictedQuerySet):
    """
    Combine django-tree-queries' TreeQuerySet with our querysets.RestrictedQuerySet for permissions enforcement.
    """


class TreeManager(Manager.from_queryset(TreeQuerySet), TreeManager_):
    """
    Extend django-tree-queries' TreeManager to incorporate querysets.RestrictedQuerySet.
    """

    _with_tree_fields = True
