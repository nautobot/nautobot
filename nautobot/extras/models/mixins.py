"""
Class-modifying mixins that need to be standalone to avoid circular imports.
"""
import sys

from cacheops.utils import family_has_profile
from django.db.models import Q
from funcy import once_per

from nautobot.utilities.forms.fields import DynamicModelMultipleChoiceField


class DynamicGroupMixin:
    """
    Adds a `dynamic_groups` property that returns a queryset of `DynamicGroup` membership.
    """

    @property
    def dynamic_groups(self):
        """Return a `DynamicGroup` queryset for this instance."""
        from nautobot.extras.models.groups import DynamicGroup

        if not hasattr(self, "_dynamic_group_queryset"):
            queryset = DynamicGroup.objects.get_for_object(self)
            self._dynamic_group_queryset = queryset

        return self._dynamic_group_queryset


# 2.0 TODO: Remove after v2 since we will no longer care about backwards-incompatibility.
class TaggableManagerMonkeyMixin:
    """
    Dynamically-applied monkey-patch mixin that is used to replace any defined
    methods on eligible objects.

    Intended to be used on the right-hand side of `monkey_mix()` to overload the
    `formfield()` method.

    Usage:

        monkey_mix(TaggableManager, TaggableManagerMonkeyMixin)

    See: `nautobot.extras.apps.ready()`
    """

    @once_per("cls")
    def _install_hotfix(self, cls):
        # Install auto-created models as their module attributes to make them picklable
        module = sys.modules[cls.__module__]
        if not hasattr(module, cls.__name__):
            setattr(module, cls.__name__, cls)

    # This is probably still needed if models are created dynamically.
    def contribute_to_class(self, cls, name):
        self._no_monkey.contribute_to_class(self, cls, name)
        # Django migrations create lots of fake models, just skip them
        # NOTE: we make it here rather then inside _install_hotfix()
        #       because we don't want @once_per() to hold refs to all of them.
        if cls.__module__ != "__fake__" and family_has_profile(cls):
            self._install_hotfix(cls)

    def formfield(self, form_class=DynamicModelMultipleChoiceField, **kwargs):
        from nautobot.extras.models.tags import Tag

        queryset = Tag.objects.filter(
            Q(
                content_types__model=self.model._meta.model_name,
                content_types__app_label=self.model._meta.app_label,
            )
            | Q(content_types__isnull=True)
        )
        kwargs.setdefault("queryset", queryset)
        kwargs.setdefault("required", False)
        kwargs.setdefault("query_params", {"content_types": self.model._meta.label_lower})
        return self._no_monkey.formfield(self, form_class=form_class, **kwargs)
