"""
Class-modifying mixins that need to be standalone to avoid circular imports.
"""
import sys

from cacheops.utils import family_has_profile
from django.db.models import Q
from django.urls import NoReverseMatch, reverse
from funcy import once_per

from nautobot.utilities.forms.fields import DynamicModelMultipleChoiceField
from nautobot.utilities.utils import get_route_for_model


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

    def get_dynamic_groups_url(self):
        """Return the dynamic groups URL for a given instance."""
        route = get_route_for_model(self, "dynamicgroups")

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None


class NotesMixin:
    """
    Adds a `notes` property that returns a queryset of `Notes` membership.
    """

    @property
    def notes(self):
        """Return a `Notes` queryset for this instance."""
        from nautobot.extras.models.models import Note

        if not hasattr(self, "_notes_queryset"):
            queryset = Note.objects.get_for_object(self)
            self._notes_queryset = queryset

        return self._notes_queryset

    def get_notes_url(self):
        """Return the notes URL for a given instance."""
        route = get_route_for_model(self, "notes")

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None


# 2.0 TODO: Remove after v2 since we will no longer care about backwards-incompatibility.
# - Remove the `monkey_mix` from `nautobot.core.apps.CoreConfig.ready()`
# - Convert this into a subclass instead of a mixin and move it to `nautobot.extras.models.managers.TaggableManager` (assuming this stays in `extras`)
# - Replace all `from taggit.managers import TaggableManager` references to `from nautobot.extras.models.managers import TaggableManager`
class TaggableManagerMonkeyMixin:
    """
    Dynamically-applied monkey-patch mixin that is used to replace any defined
    methods on eligible objects.

    Intended to be used on the right-hand side of `monkey_mix()` to overload the
    `formfield()` method.

    Usage:

        monkey_mix(TaggableManager, TaggableManagerMonkeyMixin)

    See: `nautobot.core.apps.ready()`
    """

    @once_per("cls")
    def _install_hotfix(self, cls):
        # Install auto-created models as their module attributes to make them picklable
        module = sys.modules[cls.__module__]
        if not hasattr(module, cls.__name__):
            setattr(module, cls.__name__, cls)

    # This is probably still needed if models are created dynamically.
    def contribute_to_class(self, cls, name):
        """
        Overload default so that we can assert that this is called when
        attached to any model that is using a `TaggableManager`.

        Using `.contribute_to_class()` is how field objects get added to the model
        at during the instance preparation. This is also where any custom model
        methods are hooked in. So in short this method asserts that any time a`
        `TaggableManager` is added to a model, that model also gets its methods
        monkey-mixed without having to define them on the model yourself.
        """

        self._no_monkey.contribute_to_class(self, cls, name)
        # Django migrations create lots of fake models, just skip them
        # NOTE: we make it here rather then inside _install_hotfix()
        #       because we don't want @once_per() to hold refs to all of them.
        # family_has_profile is fork-lifted from cacheops which
        # is used to identify "all proxy models, including subclasess, superclassses and siblings" for a model object.
        # See: https://github.com/Suor/django-cacheops/blob/ad83e51b6d82ba2bf4820953925ff889e4c4b840/cacheops/utils.py#L16-L27
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
