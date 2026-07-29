"""Jinja2 environment used to render user-authored templates.

Nautobot renders user-authored Jinja2 templates (Custom Links, Computed Fields, Export Templates,
Webhooks, Job Buttons, Secret parameters, data validation rules, etc.) with a live model instance
in the template context. The stock `jinja2.sandbox.SandboxedEnvironment` only blocks
underscore/dunder attributes and callables marked `alters_data`/`@unsafe`, which leaves the
Django ORM's chain from a model instance to a raw database cursor reachable. It also enforces its
`is_safe_callable` check only for calls compiled to `environment.call()`, not for calls made
directly through `Context.call()`.
"""

from django.apps.registry import Apps
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import CursorDebugWrapper, CursorWrapper
from django.db.models.manager import BaseManager
from django.db.models.options import Options
from django.db.models.query import QuerySet
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.query import Query
from django.db.utils import ConnectionHandler
from jinja2.exceptions import SecurityError
from jinja2.runtime import Context
from jinja2.sandbox import SandboxedEnvironment

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
)

# Attribute names blocked only on Manager/QuerySet, to prevent raw SQL/model access (e.g. 'query', 'raw') while allowing safe use on models.
MANAGER_QUERYSET_UNSAFE_ATTRS = frozenset(
    {
        "query",
        "raw",
        "get_compiler",
        "db",
        "db_manager",
        "get_queryset",
        "model",
        "resolve_expression",
        "bulk_create",
        "bulk_update",
    }
)


class NautobotSandboxedContext(Context):
    """Context that re-applies the sandbox's is_safe_callable check on the Context.call() path."""

    # Double-underscore parameter names mirror Jinja's Context.call so proxied kwargs can't collide.
    def call(__self, __obj, *args, **kwargs):  # pylint: disable=no-self-argument
        environment = __self.environment
        if getattr(environment, "sandboxed", False) and not environment.is_safe_callable(__obj):
            raise SecurityError(f"{__obj!r} is not safely callable")
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
        # Narrow name block scoped to the one dangerous-container family users legitimately traverse.
        if isinstance(obj, (BaseManager, QuerySet)) and attr in MANAGER_QUERYSET_UNSAFE_ATTRS:
            return False
        return True

    def is_safe_callable(self, obj):
        """Refuse to call a bound method whose owner is a Django ORM/DB internal (defense-in-depth)."""
        if not super().is_safe_callable(obj):
            return False
        if hasattr(obj, "__self__") and isinstance(obj.__self__, DANGEROUS_TYPES):
            return False
        return True
