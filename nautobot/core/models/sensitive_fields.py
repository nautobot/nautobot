"""Support for declaring model fields that must never be retrieved from the database through the ORM.

A model opts in by declaring `sensitive_fields` on the model class:

    class Token(BaseModel):
        key = models.CharField(max_length=40, unique=True)

        sensitive_fields = ("key",)

Reading such a field is then blocked on two independent paths, because Django resolves "give me this
instance's column value" and "project this column into the result set" through entirely different code:

1. `BaseModel.from_db()` drops the value so it never lands in `instance.__dict__`, and the descriptor
   installed here raises when the missing attribute is read. Every database-to-instance path funnels
   through `Model.from_db()`, so this covers plain fetches, `only()`, `select_related()`,
   `prefetch_related()`, `in_bulk()`, `raw()`, `refresh_from_db()`, and the `_base_manager` paths.
2. `SensitiveFieldsQuerySetMixin` checks the lookup paths handed to the projection methods
   (`values()`, `values_list()`, `annotate()`, and friends), which never build instances at all.

Both of those paths are gated on `settings.STRICT_SENSITIVE_FIELDS`, which defaults to False so that
existing code reading such a field keeps working. User-authored Jinja2 templates are a separate case: the
sandbox denies sensitive fields unconditionally, because a template is untrusted input rather than
first-party code that can be migrated to the opt-in methods. The checker functions here are therefore
unconditional, and it is their callers that consult the setting.

Filtering is deliberately still permitted. The contract is "the value is never returned", not "the column
is unmentionable", and API token authentication depends on being able to look a token up by its key.

This is defense in depth against accidental exposure through generic machinery, not a sandbox: any caller
who can execute arbitrary Python can reach the column through raw SQL.
"""

import contextlib
import threading

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Combinable, F
from django.db.models.query_utils import DeferredAttribute
from django.db.models.signals import class_prepared

from nautobot.core.exceptions import SensitiveFieldError

# Set while a block of code has declared itself exempt from the strict behavior. Thread-local so that
# exempting one operation cannot affect a request being served on another thread.
_exemption = threading.local()


@contextlib.contextmanager
def sensitive_fields_exempt():
    """Suspend strict sensitive-field enforcement for the calling thread.

    Intended for management commands that already require a level of access which makes the protection
    moot, `dumpdata` being the case in point: anyone who can run a management command can equally open a
    Nautobot shell and read the column directly, so refusing to serialize it protects nothing and only
    breaks the tool.

    This is not a general-purpose escape hatch, and app or view code should not use it. Reading a single
    value on purpose is what `with_sensitive_fields()` and `get_sensitive_field()` are for; those name the
    field they disclose, whereas this suspends the protection wholesale.
    """
    previous = getattr(_exemption, "active", False)
    _exemption.active = True
    try:
        yield
    finally:
        _exemption.active = previous


def strict_sensitive_fields_enabled():
    """Return whether the ORM should refuse to return sensitive field values.

    Read through `getattr` with a default so that the mechanism still behaves sanely if it is exercised
    before or without a fully configured settings module.
    """
    if getattr(_exemption, "active", False):
        return False
    return getattr(settings, "STRICT_SENSITIVE_FIELDS", False)


# Prefix for the query annotation that carries an opted-in value past the `from_db()` scrub.
SENSITIVE_FIELD_ALIAS_PREFIX = "_sensitive_field_"

# Every field name declared sensitive by any model, used only as a fast-path filter so that the
# lookup-path walk is skipped entirely for the overwhelming majority of queries. Membership here does
# *not* mean a given path is sensitive: the walk still resolves each name against its owning model, so
# an unrelated model with a same-named field is unaffected.
_ALL_SENSITIVE_FIELD_NAMES = set()

# Shared empty result for the overwhelmingly common "this model declares nothing" case.
_NO_SENSITIVE_FIELDS = frozenset()


# Attributes holding a model's resolved sensitive-field names. `install_sensitive_fields()` is the only
# writer and sets both together, including for a model that declares nothing, so that the getters below are
# a single dict lookup on the path `Model.from_db()` runs for every row of every model.
#
# `class_prepared` covers every model prepared after this module is imported. The handful prepared before it
# (Django and third-party contrib models, none of which declare anything) are resolved by the getters on
# first use and cached from then on.
#
# `RESOLVED_ATTR` holds every declared name that resolved to a real protectable field. `WITHHELD_ATTR` holds
# the subset of those actually removed from a database-loaded instance, kept separately so `from_db()` reads
# exactly the set it needs with no set arithmetic per row.
RESOLVED_ATTR = "_sensitive_field_names"
WITHHELD_ATTR = "_sensitive_field_names_withheld"


def get_sensitive_field_names(model):
    """Return the set of field names declared sensitive on `model`, as a frozenset of strings.

    This is the raw declaration narrowed to the names that resolved to a real protectable field, which is
    why resolving is `install_sensitive_fields()`'s job and not this function's: doing it here would mean a
    `_meta.get_field()` per declared name per call, and re-logging every rejected name, on a path that runs
    for every row of every model.

    `class_prepared` resolves every model as it is prepared, so the lookup below is normally a hit. It can
    miss only for a model prepared before this module was imported, which is a model that does not inherit
    `BaseModel`; resolving such a model on first use keeps template and query-projection enforcement working
    for it, and leaves exactly one definition of what the resolved set contains.

    Takes any model class, including ones outside Nautobot's hierarchy (`auth.Group`, third-party models).
    """
    resolved = model.__dict__.get(RESOLVED_ATTR)
    if resolved is None:
        resolved = install_sensitive_fields(model)
    return resolved


def get_instance_kept_sensitive_field_names(model):
    """Return the sensitive field names `model` keeps on its instances, as a frozenset of strings.

    A field named in `sensitive_fields_kept_on_instance` is still refused to templates and still refused
    in query projections, but its value is left on a database-loaded instance and Python may read the
    attribute normally. That is the right shape for a field the framework itself reads constantly:
    `User.password`, for example, is read by Django on every session-authenticated request, so
    withholding it would mean re-fetching it per request for no security benefit that the template and
    projection checks do not already provide.

    Such a field must be a subset of `sensitive_fields`; a name here that is not declared sensitive has
    no effect.
    """
    declared = getattr(model, "sensitive_fields_kept_on_instance", None)
    if not declared:
        return _NO_SENSITIVE_FIELDS
    return frozenset(declared)


def get_withheld_sensitive_field_names(model):
    """Return the sensitive field names `model` removes from a database-loaded instance.

    This is `sensitive_fields` minus `sensitive_fields_kept_on_instance`, resolved once by
    `install_sensitive_fields()`, because `Model.from_db()` consults it for every row of every model and so
    must not do set arithmetic or allocate. As with `get_sensitive_field_names()`, a miss means the model
    was prepared before this module was imported and is resolved on first use.
    """
    withheld = model.__dict__.get(WITHHELD_ATTR)
    if withheld is None:
        install_sensitive_fields(model)
        withheld = model.__dict__[WITHHELD_ATTR]
    return withheld


def sensitive_field_alias(field_name):
    """Return the query annotation name used to carry an opted-in value for `field_name`."""
    return f"{SENSITIVE_FIELD_ALIAS_PREFIX}{field_name}"


def is_possibly_sensitive_field_name(name):
    """Return whether `name` is declared sensitive by *any* model, as a cheap pre-filter.

    True does not mean the name is sensitive on a given model; it only means the more expensive
    per-model resolution is worth doing. Intended for hot paths such as template attribute access.
    """
    return name in _ALL_SENSITIVE_FIELD_NAMES


class SensitiveFieldDescriptor(DeferredAttribute):
    """Field descriptor that refuses to load a sensitive field's value from the database.

    Must remain a *non-data* descriptor (no `__set__`), for two reasons. Python only consults a non-data
    descriptor when the attribute is absent from the instance's `__dict__`, which is exactly the
    distinction wanted here: a value assigned in Python stays readable, while a value scrubbed out of a
    database-loaded instance is not. And Django reads these attributes back through `getattr` in
    `Field.pre_save`, `Model.clean_fields`, and `Field.value_from_object`, so routing every read and
    write through Python would put all of those on the descriptor path.
    """

    def __get__(self, instance, cls=None):
        if instance is None:
            # Class-level access, e.g. `getattr(Token, "key")`. Generic introspection relies on this
            # returning the descriptor rather than raising.
            return self
        attname = self.field.attname
        data = instance.__dict__
        if attname in data:
            # Assigned in Python (a newly constructed or just-saved instance), so it was never withheld.
            return data[attname]
        alias = sensitive_field_alias(attname)
        if alias in data:
            # Retrieved through an explicit `with_sensitive_fields()` opt-in.
            return data[alias]
        if not strict_sensitive_fields_enabled():
            # Non-strict mode. The value is absent either because the caller deferred it explicitly or
            # because a strict-mode queryset built this instance, so fall back to Django's lazy load.
            return super().__get__(instance, cls)
        raise SensitiveFieldError(
            f"{instance._meta.label}.{self.field.name} is a sensitive field and is not returned by the ORM. "
            f'Use `.with_sensitive_fields("{self.field.name}")` on the queryset, or '
            f'`instance.get_sensitive_field("{self.field.name}")`, to opt in explicitly.'
        )


def install_sensitive_fields(model):
    """Resolve `model`'s declared sensitive fields, install the raising descriptor for each, and return them.

    The single writer of `RESOLVED_ATTR` and `WITHHELD_ATTR`, and the single definition of what "resolved"
    means; the getters above read what this stores rather than recomputing it.

    Idempotent, so re-running it for a model that is already set up is harmless.

    A declared name that does not resolve to a protectable field raises `ImproperlyConfigured` from
    `class_prepared`, which aborts startup. Failing here is deliberate: the alternative is a model that
    claims to protect a field and silently does not, which is the worst outcome for a security control and
    is precisely what a typo produces. `ImproperlyConfigured` rather than `SensitiveFieldError` because the
    latter subclasses `FieldError`, which generic code catches and degrades from; a misdeclaration is a
    developer error that must not be degraded past.
    """
    field_names = frozenset(getattr(model, "sensitive_fields", ()) or ())
    kept_on_instance = get_instance_kept_sensitive_field_names(model)
    resolved = set()
    for field_name in field_names:
        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist as exc:
            raise ImproperlyConfigured(
                f"{model._meta.label}.sensitive_fields names {field_name!r}, which is not a field on that model."
            ) from exc
        if not field.concrete or field.is_relation or field.primary_key:
            raise ImproperlyConfigured(
                f"{model._meta.label}.sensitive_fields names {field_name!r}, which is not a concrete, "
                f"non-relational, non-primary-key field. Only such a field holds a value the ORM can withhold."
            )
        # Install the raising descriptor, unless the field is kept on the instance. A kept field's value is
        # never removed from `__dict__`, so Django's own descriptor returns it and a raising one would never
        # fire anyway. Registering the name below still refuses a kept field to templates and to query
        # projections, which is the whole protection it needs.
        if field_name not in kept_on_instance and not isinstance(
            model.__dict__.get(field.attname), SensitiveFieldDescriptor
        ):
            setattr(model, field.attname, SensitiveFieldDescriptor(field))
        # A concrete non-relational field always has `name == attname`, but record both so callers can
        # use either spelling without having to know that.
        resolved.add(field.name)
        resolved.add(field.attname)
    _ALL_SENSITIVE_FIELD_NAMES.update(resolved)
    # Store per-class resolved/withheld field sets (never inherited).
    # All models get a value, even if empty, for uniform access in getters.
    resolved = frozenset(resolved) if resolved else _NO_SENSITIVE_FIELDS
    setattr(model, RESOLVED_ATTR, resolved)
    setattr(model, WITHHELD_ATTR, resolved - kept_on_instance if resolved else _NO_SENSITIVE_FIELDS)
    return resolved


def sensitive_fields_class_prepared(sender, **kwargs):
    """Signal receiver installing sensitive-field descriptors as each model class is prepared."""
    install_sensitive_fields(sender)


# Connected at this module's scope rather than from an AppConfig, for two reasons.
#
# It cannot go in an AppConfig module: those are imported during `nautobot-server` startup before Django
# settings are configured, and importing `nautobot.core.models` that early is circular with ContentType.
#
# It does not need to go anywhere else either. `nautobot.core.models` reaches this module by way of
# `nautobot.core.models.querysets`, and that same package is where `BaseModel` is defined, so a model can
# only subclass `BaseModel` once this receiver is already connected. Every model the mechanism applies to
# is therefore guaranteed to be covered, with no need to sweep for stragglers afterwards. Models prepared
# before this point are ones that do not inherit `BaseModel`, which never get the `from_db()` scrub and so
# cannot be protected regardless.
class_prepared.connect(sensitive_fields_class_prepared, dispatch_uid="nautobot_install_sensitive_fields")


def check_lookup_path(model, lookup_path, allowed=frozenset()):
    """Raise `SensitiveFieldError` if `lookup_path` resolves to a sensitive field on any model it traverses.

    Args:
        model (type): The model the lookup path starts from, which is not necessarily the model that owns
            the sensitive field: `User.objects.values_list("tokens__key")` starts on `User`.
        lookup_path (str): A `__`-separated lookup path, possibly ending in a transform or lookup, and
            possibly prefixed with `-` for descending order. Anything a projection method accepts may be
            passed; a non-string is not this function's to check and is skipped (see below).
        allowed (frozenset): Field names the caller has explicitly opted in to, from `with_sensitive_fields()`.

    Unresolvable path components are ignored rather than raising, so that a genuinely bad field name still
    produces Django's own `FieldError` with its "Choices are: ..." message instead of a misleading one here.
    """
    # Non-string values (i.e., query expressions) are handled by check_expression(), so skip them here.
    if not isinstance(lookup_path, str):
        return
    parts = lookup_path.lstrip("-").split(LOOKUP_SEP)
    if not _ALL_SENSITIVE_FIELD_NAMES.intersection(parts):
        return
    opts = model._meta
    for part in parts:
        if opts is None:
            return
        name = opts.pk.name if part == "pk" else part
        try:
            field = opts.get_field(name)
        except (FieldDoesNotExist, AttributeError):
            # A transform, lookup, or annotation alias rather than a field. Nothing further to resolve.
            return
        if name in get_sensitive_field_names(field.model) and name not in allowed:
            raise SensitiveFieldError(
                f"{field.model._meta.label}.{name} is a sensitive field and cannot be retrieved via "
                f'"{lookup_path}". Use `.with_sensitive_fields("{name}")` to opt in explicitly.'
            )
        related_model = getattr(field, "related_model", None)
        opts = related_model._meta if related_model is not None else None


def check_expression(model, expression, allowed=frozenset()):
    """Raise `SensitiveFieldError` if `expression` references a sensitive field anywhere in its tree.

    Recurses through `get_source_expressions()` so that nested constructs (`Max("key")`,
    `Concat("key", Value(""))`, `Case(When(then=F("key")))`, `Subquery`) are all covered. Bare string
    arguments are reached as well, because `Func._parse_expressions` coerces them to `F` instances.
    """
    if isinstance(expression, str):
        check_lookup_path(model, expression, allowed)
        return
    if isinstance(expression, F):
        check_lookup_path(model, expression.name, allowed)
        return
    # Not an expression tree; only `Q` really gets here, which is allowed since filtering on sensitive fields is permitted.
    if not isinstance(expression, Combinable) and not hasattr(expression, "get_source_expressions"):
        return
    for source_expression in expression.get_source_expressions():
        if source_expression is not None:
            check_expression(model, source_expression, allowed)
