from django.db.models import Manager
from mptt.managers import TreeManager as TreeManager_
from mptt.querysets import TreeQuerySet as TreeQuerySet_

from nautobot.utilities import querysets


class TreeQuerySet(TreeQuerySet_, querysets.RestrictedQuerySet):
    """
    Mate django-mptt's TreeQuerySet with our RestrictedQuerySet for permissions enforcement.
    """


class TreeManager(Manager.from_queryset(TreeQuerySet), TreeManager_):
    """
    Extend django-mptt's TreeManager to incorporate RestrictedQuerySet().
    """
