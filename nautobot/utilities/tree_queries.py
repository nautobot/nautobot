from django.core.cache import cache
from django.db.models import Manager, Case, When
from tree_queries.models import TreeNode
from tree_queries.query import TreeManager as TreeManager_, TreeQuerySet as TreeQuerySet_

from nautobot.utilities.querysets import RestrictedQuerySet


class TreeQuerySet(TreeQuerySet_, RestrictedQuerySet):
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
        model_class = of._meta.concrete_model
        ancestor_pks = []
        if include_self:
            ancestor_pks.append(of.pk)
        while of := of.parent:
            # Insert in reverse order so that the root is the first element
            ancestor_pks.insert(0, of.pk)
        # Maintain API compatibility by returning a queryset instead of a list directly.
        # Reference:
        # https://stackoverflow.com/questions/4916851/django-get-a-queryset-from-array-of-ids-in-specific-order
        preserve_order = Case(*[When(pk=pk, then=position) for position, pk in enumerate(ancestor_pks)])
        return model_class.objects.without_tree_fields().filter(pk__in=ancestor_pks).order_by(preserve_order)


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
