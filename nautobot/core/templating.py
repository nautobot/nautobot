"""Jinja2 environment used to render user-authored templates.

Nautobot renders user-authored Jinja2 templates (Custom Links, Computed Fields, Export Templates,
Webhooks, Job Buttons, Secret parameters, data validation rules, etc.) with a live model instance
in the template context. The stock `jinja2.sandbox.SandboxedEnvironment` only blocks
underscore/dunder attributes and callables marked `alters_data`/`@unsafe`, which leaves the
Django ORM's chain from a model instance to a raw database cursor reachable. It also enforces its
`is_safe_callable` check only for calls compiled to `environment.call()`, not for calls made
directly through `Context.call()`.

This environment also denies access to any field a model declares in `sensitive_fields`, both as an
attribute (`{{ obj.tokens.first().key }}`) and as a queryset projection (`{{ obj.tokens.values_list('key') }}`).
"""

from django.apps.registry import Apps
from django.contrib.contenttypes.models import ContentType
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorDebugWrapper, CursorWrapper
from django.db.models import Model
from django.db.models.manager import BaseManager, Manager
from django.db.models.options import Options
from django.db.models.query import QuerySet, RawQuerySet
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.query import Query
from django.db.utils import ConnectionHandler
from jinja2.exceptions import SecurityError
from jinja2.runtime import Context
from jinja2.sandbox import SandboxedEnvironment

from nautobot.core.exceptions import SensitiveFieldError
from nautobot.core.models.sensitive_fields import (
    check_lookup_path,
    get_sensitive_field_names,
    is_possibly_sensitive_field_name,
    SENSITIVE_FIELD_ALIAS_PREFIX,
)

# Types that templates must not introspect. Attribute access is denied both on these objects and on any value resolving to them.
# Excludes BaseManager and QuerySet, as these are commonly and legitimately used in templates.
DANGEROUS_TYPES = (
    Query,
    SQLCompiler,
    BaseDatabaseWrapper,
    CursorWrapper,
    CursorDebugWrapper,
    Options,
    Apps,
    ConnectionHandler,
    RawQuerySet,
)

# Allowed read/navigation methods for Django's Manager/QuerySet in templates.
# Only attributes listed here are permitted for stock classes.
# Custom (non-stock) methods remain subject to alters_data and DANGEROUS_TYPES above.
MANAGER_QUERYSET_SAFE_STOCK_ATTRS = frozenset(
    {
        "aggregate",
        "alias",
        "all",
        "annotate",
        "contains",
        "count",
        "dates",
        "datetimes",
        "defer",
        "difference",
        "distinct",
        "earliest",
        "exclude",
        "exists",
        "explain",
        "filter",
        "first",
        "get",
        "intersection",
        "iterator",
        "last",
        "latest",
        "none",
        "only",
        "order_by",
        "ordered",
        "prefetch_related",
        "reverse",
        "select_related",
        "union",
        "values",
        "values_list",
    }
)

STOCK_MANAGER_QUERYSET_ATTRS = frozenset(dir(QuerySet)) | frozenset(dir(BaseManager)) | frozenset(dir(Manager))

# Data-mutating / side-effecting method names denied on ANY Manager/QuerySet, stock or custom.
MANAGER_QUERYSET_WRITE_ATTRS = frozenset(
    {
        # M2M / related-manager and django-taggit mutators (not on the base QuerySet/Manager).
        "add",
        "set",
        "remove",
        "clear",
        "aadd",
        "aset",
        "aremove",
        "aclear",
        # CRUD writers (stock ones are already denied; listed so a custom manager that redefines one
        # without `alters_data` is still refused).
        "create",
        "delete",
        "update",
        "save",
        "get_or_create",
        "update_or_create",
        "bulk_create",
        "bulk_update",
        "acreate",
        "adelete",
        "aupdate",
        "aget_or_create",
        "aupdate_or_create",
        "abulk_create",
        "abulk_update",
        # Side-effecting cache flush on ContentTypeManager.
        "clear_cache",
    }
)

# ContentType instance methods that pivot to an arbitrary model's UNRESTRICTED manager.
CONTENT_TYPE_PIVOT_ATTRS = frozenset(
    {
        "model_class",
        "get_object_for_this_type",
        "get_all_objects_for_this_type",
    }
)

# The explicit opt-in API for reading a sensitive field. First-party code uses these deliberately; a
# template calling one would sidestep the sensitive-field denial entirely, so they are blocked outright.
SENSITIVE_FIELD_OPT_IN_ATTRS = frozenset(
    {
        "get_sensitive_field",
        "with_sensitive_fields",
    }
)


def deny_sensitive_field_attribute(obj, attribute):
    """Raise `SecurityError` for template access to a sensitive field, or to the API that opts in to one."""
    if not isinstance(attribute, str):
        return
    # The opt-in API is for first-party code deciding to disclose a value. A template reaching it would
    # bypass every other check here, so the methods themselves are unreachable from a template.
    if attribute in SENSITIVE_FIELD_OPT_IN_ATTRS and isinstance(obj, (Model, BaseManager, QuerySet)):
        raise SecurityError(f"{attribute}() opts in to sensitive field values and cannot be called from a template.")
    # Cheap pre-filter first: this runs for every attribute access in every rendered template, and almost
    # none of them name a field that any model has declared sensitive.
    if not is_possibly_sensitive_field_name(attribute):
        return
    if isinstance(obj, Model) and attribute in get_sensitive_field_names(type(obj)):
        raise SecurityError(
            f"{obj._meta.label}.{attribute} is a sensitive field and cannot be accessed from a template."
        )


def deny_sensitive_field_arguments(obj, args):
    """Raise `SecurityError` if a Manager/QuerySet method is called with a sensitive field's lookup path.

    Covers the projection route into a sensitive value, `{{ obj.tokens.values_list('key') }}`, which the
    attribute check cannot see because the value is produced by the query rather than read off an instance.

    Only positional arguments are examined. Keyword arguments to a queryset method are overwhelmingly
    filter predicates, whose *values* are supplied by the template author and would produce false
    positives if treated as lookup paths; filtering by a sensitive field is permitted in any case.
    """
    owner = getattr(obj, "__self__", None)
    if not isinstance(owner, (BaseManager, QuerySet)):
        return
    model = getattr(owner, "model", None)
    if model is None:
        return
    for arg in args:
        if not isinstance(arg, str):
            continue
        # `with_sensitive_fields()` carries an opted-in value as an annotation under this prefix. The name
        # is not a model field, so the lookup-path walk below would not recognize it.
        if arg.startswith(SENSITIVE_FIELD_ALIAS_PREFIX):
            raise SecurityError(f"{arg} refers to a sensitive field value and cannot be selected in a template.")
        try:
            check_lookup_path(model, arg)
        except SensitiveFieldError as exc:
            # Re-raised as SecurityError so a template author sees the sandbox's normal refusal, and so
            # that callers already handling template security failures keep working.
            raise SecurityError(str(exc)) from exc


class NautobotSandboxedContext(Context):
    """Context that re-applies the sandbox's checks on the Context.call() path.

    This is the single enforcement point for calls. `SandboxedEnvironment.call()` ends by delegating to
    `Context.call()`, so a call compiled to the environment path arrives here too, while a call made
    directly through `Context.call()` (which stock Jinja leaves unchecked) arrives here only.
    """

    # Double-underscore parameter names mirror Jinja's Context.call so proxied kwargs can't collide.
    def call(__self, __obj, *args, **kwargs):  # pylint: disable=no-self-argument
        environment = __self.environment
        if getattr(environment, "sandboxed", False) and not environment.is_safe_callable(__obj):
            raise SecurityError(f"{__obj!r} is not safely callable")
        deny_sensitive_field_arguments(__obj, args)
        return super().call(__obj, *args, **kwargs)


class NautobotSandboxedEnvironment(SandboxedEnvironment):
    """SandboxedEnvironment that also blocks Django ORM/DB internals used as Server-Side Template Injection (SSTI) gadgets."""

    context_class = NautobotSandboxedContext

    def is_safe_attribute(self, obj, attr, value):
        """Deny attribute access that would expose Django ORM/DB internals to a template."""
        if not super().is_safe_attribute(obj, attr, value):
            return False
        # Block all attribute access on DB/ORM-internal types.
        if isinstance(obj, DANGEROUS_TYPES):
            return False
        # Never hand back a DB/ORM-internal object, regardless of the attribute name used to reach it
        # (e.g. `.query` -> Query, `.connection` -> BaseDatabaseWrapper, `meta` filter -> Apps).
        if isinstance(value, DANGEROUS_TYPES):
            return False
        # Deny reaching a model *class*, whether it is the object being traversed or the value handed back.
        # Templates operate on model instances, not classes.
        if isinstance(obj, type) and issubclass(obj, Model):
            return False
        if isinstance(value, type) and issubclass(value, Model):
            return False
        # Deny the ContentType instance pivot methods, which return an unrestricted arbitrary-model queryset
        # without ever exposing the model class to the sandbox (so the guard above cannot catch them).
        if isinstance(obj, ContentType) and attr in CONTENT_TYPE_PIVOT_ATTRS:
            return False
        # On a Manager/QuerySet: deny data-mutating method names and then allow only vetted
        # stock read methods, denying every other stock attribute.
        # App-defined custom *read* methods are not stock attributes and pass through here.
        if isinstance(obj, (BaseManager, QuerySet)):
            if attr in MANAGER_QUERYSET_WRITE_ATTRS:
                return False
            if attr in STOCK_MANAGER_QUERYSET_ATTRS and attr not in MANAGER_QUERYSET_SAFE_STOCK_ATTRS:
                return False
        return True

    def getattr(self, obj, attribute):
        """Deny `{{ obj.sensitive_field }}` before Jinja resolves it.

        Also covers the `attr` filter, which ends by calling this rather than reading the attribute itself.
        """
        deny_sensitive_field_attribute(obj, attribute)
        return super().getattr(obj, attribute)

    def getitem(self, obj, argument):
        """Deny `{{ obj['sensitive_field'] }}`, which Jinja routes here rather than through `getattr()`.

        Also covers `map(attribute=...)`, whose attribute lookup is built on this rather than on `getattr()`.
        """
        deny_sensitive_field_attribute(obj, argument)
        return super().getitem(obj, argument)

    def is_safe_callable(self, obj):
        """Refuse to call a bound method whose owner is a Django ORM/DB internal (defense-in-depth)."""
        if not super().is_safe_callable(obj):
            return False
        if hasattr(obj, "__self__") and isinstance(obj.__self__, DANGEROUS_TYPES):
            return False
        return True
