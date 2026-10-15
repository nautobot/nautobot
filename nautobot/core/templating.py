"""Jinja2 environment used to render user-authored templates.

Nautobot renders user-authored Jinja2 templates (Custom Links, Computed Fields, Export Templates,
Webhooks, Job Buttons, Secret parameters, data validation rules, etc.) with a live model instance
in the template context. The stock `jinja2.sandbox.SandboxedEnvironment` only blocks
underscore/dunder attributes and callables marked `alters_data`/`@unsafe`, which leaves the
Django ORM's chain from a model instance to a raw database cursor reachable. It also enforces its
`is_safe_callable` check only for calls compiled to `environment.call()`, not for calls made
directly through `Context.call()`.

This environment also denies access to any field a model declares in `sensitive_fields`, as an
attribute, as a named queryset projection, and as a projection that names no fields at all,
which is narrowed to the model's non-sensitive fields.

To prevent templates from executing arbitrary SQL with database-level privileges, we block access
to Python modules and app configs, restrict the `meta` filter from returning them, and refuse any
query expression containing author-supplied SQL.
"""

from types import ModuleType

from django.apps.config import AppConfig
from django.apps.registry import Apps
from django.contrib.contenttypes.models import ContentType
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorDebugWrapper, CursorWrapper
from django.db.models import Model
from django.db.models.expressions import BaseExpression, RawSQL
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
    NO_NARROWING,
    non_sensitive_field_names,
    SENSITIVE_FIELD_ALIAS_PREFIX,
)

# Types that templates must not introspect. Attribute access is denied both on these objects and on any
# value resolving to them, and the `meta` template filter refuses to return one.
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
    ModuleType,
    AppConfig,
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

# Expression classes whose constructor takes a SQL string outright.
RAW_SQL_EXPRESSION_TYPES = (RawSQL,)

# Constructor keywords that put a caller-supplied SQL format string inside an expression.
SQL_TEMPLATE_KWARGS = frozenset(
    {
        "template",
        "function",
        "arg_joiner",
    }
)

# How far to walk a nested expression tree looking for the above. Deeper than any expression a template
# can plausibly compose, and bounded so a cyclic tree cannot spin.
MAX_EXPRESSION_DEPTH = 32

# Projection methods that select every concrete column when called with no field names.
BARE_PROJECTION_ATTRS = frozenset(
    {
        "values",
        "values_list",
        "distinct_values_list",
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


def projection_model(owner):
    """Given an `owner`, return the model whose fields would be selected in a query, or None if not applicable.

    A `Manager`'s own `model` attribute is not reliable for this, because a related manager is free to
    set it to the model it hangs off rather than the one it yields; django-taggit's does, so
    `obj.tags.model` is the tagged model while its queryset yields `Tag`. Ask the queryset, which is what
    the projection actually runs against, so the field names are checked against the right model's
    `sensitive_fields`.

    `Manager.values()`, `values_list()`, `distinct_values_list()` and similar projection methods build
    the same queryset before doing anything else, so a manager whose `get_queryset()` raises would have
    raised on the call being guarded here regardless.

    Returns:
        (type | None): The model whose columns would be projected, or None when `owner` is not a queryset
            or manager, which is the ordinary case for most calls a template makes.
    """
    if isinstance(owner, QuerySet):
        return owner.model
    if isinstance(owner, BaseManager):
        return owner.get_queryset().model
    return None


def deny_sensitive_field_arguments(obj, args):
    """Raise `SecurityError` if a Manager/QuerySet method is called with a sensitive field's lookup path.

    Covers the projection route into a sensitive value, `{{ obj.tokens.values_list('key') }}`, which the
    attribute check cannot see because the value is produced by the query rather than read off an instance.

    Only positional arguments are examined. Keyword arguments to a queryset method are overwhelmingly
    filter predicates, whose *values* are supplied by the template author and would produce false
    positives if treated as lookup paths; filtering by a sensitive field is permitted in any case.

    A projection that names no fields has nothing here to inspect; `narrow_bare_projection_arguments()`
    covers that case.
    """
    model = projection_model(getattr(obj, "__self__", None))
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


def narrow_bare_projection_arguments(obj, args):
    """Return the positional arguments to call `obj` with, narrowing a projection that names no fields.

    `values()`/`values_list()` called with no field names select every concrete column, including any the
    model declares sensitive, so for those calls the empty argument list is replaced with the model's
    non-sensitive field names. Every other call gets its arguments back unchanged.

    `deny_sensitive_field_arguments()` cannot catch this, as there is no argument for it to inspect, and
    neither can `deny_sensitive_field_attribute()`, because each row comes back as a plain dict or tuple
    rather than a model instance.

    Naming the non-sensitive fields is preferred to refusing the call outright: it is the documented
    behavior of such a projection, and it is what the ORM itself does for the same call under
    `STRICT_SENSITIVE_FIELDS`. Unlike the ORM's version this is not gated on that setting, because a
    template is untrusted input and is denied a sensitive field unconditionally.
    """
    if getattr(obj, "__name__", None) not in BARE_PROJECTION_ATTRS:
        return args
    # A call that already names fields is `deny_sensitive_field_arguments()`'s to check, not this one's.
    if any(isinstance(arg, str) for arg in args):
        return args
    model = projection_model(getattr(obj, "__self__", None))
    if model is None:
        return args
    narrowed = non_sensitive_field_names(model)
    return args if narrowed is NO_NARROWING else tuple(narrowed)


def deny_caller_supplied_sql(obj, args, kwargs):
    """Raise `SecurityError` if a query expression carrying caller-written SQL is built or passed to a call.

    This is a defense-in-depth check that runs before any other checks, including the ones that
    prevent a template from accessing a sensitive field.

    Allows `annotate()`, `alias()`, `aggregate()`, and `order_by()` in templates based on field references,
    but blocks any argument or expression that introduces caller-written SQL—since that code would run with
    application DB privileges and bypass field-level checks.

    Instead of class lists (which may miss new cases), this blocks known SQL-supplying keywords inside expressions,
    including recursively nested ones. Reinforces `DANGEROUS_TYPES`, preventing any template route to raw SQL.
    """
    if isinstance(obj, type) and issubclass(obj, BaseExpression):
        if issubclass(obj, RAW_SQL_EXPRESSION_TYPES):
            raise SecurityError(f"{obj.__name__} builds a query from raw SQL and cannot be used in a template.")
        supplied = SQL_TEMPLATE_KWARGS.intersection(kwargs)
        if supplied:
            raise SecurityError(
                f"{obj.__name__} cannot be given {', '.join(sorted(supplied))} from a Jinja template, "
                f"as that supplies the SQL it generates."
            )
    for value in (*args, *kwargs.values()):
        _deny_nested_caller_supplied_sql(value)


def _deny_nested_caller_supplied_sql(value, _depth=0):
    """Raise `SecurityError` if `value` is, or contains, an expression carrying caller-written SQL."""
    # Only instances (not classes) can carry or be evaluated for SQL by the ORM; exit early for classes.
    if isinstance(value, type):
        return
    if isinstance(value, RAW_SQL_EXPRESSION_TYPES):
        raise SecurityError(f"{type(value).__name__} builds a query from raw SQL and cannot be used in a template.")
    if isinstance(value, BaseExpression):
        # `extra` holds the keywords Django did not recognize, which is where a supplied SQL format string
        # lands; the instance dictionary covers one assigned directly rather than through the constructor.
        supplied = SQL_TEMPLATE_KWARGS.intersection(
            getattr(value, "extra", None) or ()
        ) | SQL_TEMPLATE_KWARGS.intersection(vars(value))
        if supplied:
            raise SecurityError(
                f"{type(value).__name__} carries {', '.join(sorted(supplied))}, which supplies the SQL it "
                f"generates, and cannot be used from a Jinja template."
            )
    # Bounded so a self-referential or pathologically nested expression cannot spin here.
    if _depth >= MAX_EXPRESSION_DEPTH or not hasattr(value, "get_source_expressions"):
        return
    for source_expression in value.get_source_expressions():
        if source_expression is not None:
            _deny_nested_caller_supplied_sql(source_expression, _depth + 1)


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
        # Check caller-supplied SQL before arg narrowing below, so it checks the original args.
        deny_caller_supplied_sql(__obj, args, kwargs)
        deny_sensitive_field_arguments(__obj, args)
        args = narrow_bare_projection_arguments(__obj, args)
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
