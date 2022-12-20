from django.db.models import Manager
from tree_queries.query import TreeManager as TreeManager_, TreeQuerySet as TreeQuerySet_

from nautobot.utilities import querysets


class TreeQuerySet(TreeQuerySet_, querysets.RestrictedQuerySet):
    """
    Combine django-tree-queries' TreeQuerySet with our RestrictedQuerySet for permissions enforcement.
    """


class TreeManager(Manager.from_queryset(TreeQuerySet), TreeManager_):
    """
    Extend django-tree-queries' TreeManager to incorporate RestrictedQuerySet.
    """

    _with_tree_fields = True
