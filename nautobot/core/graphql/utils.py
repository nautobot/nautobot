import functools
import inspect
import logging

from django.db import models
from django_filters.filters import BooleanFilter, MultipleChoiceFilter, NumberFilter
import graphene

from nautobot.core.filters import (
    MultiValueBigNumberFilter,
    MultiValueDecimalFilter,
    MultiValueFloatFilter,
    MultiValueNumberFilter,
)
from nautobot.core.models.fields import slugify_dashes_to_underscores
from nautobot.core.utils.permissions import permission_is_exempt, qs_filter_from_constraints

logger = logging.getLogger(__name__)


def _build_reserved_graphene_field_kwargs():
    """Build the set of filter names that must not be splatted as top-level `graphene.Field` kwargs.

    Filter arguments are passed into `graphene.List(schema_type, **search_params)` and mounted as a
    `graphene.Field`. Any filter whose name matches a reserved `graphene.Field.__init__` keyword
    argument would be consumed as that Field attribute instead of being mounted as a GraphQL argument.
    Such names are instead relocated into the nested `args` mapping.

    The set is derived dynamically from the signature so reserved kwargs added in future graphene
    releases are handled automatically (see #9021).
    """
    signature = inspect.signature(graphene.types.field.Field.__init__)
    params = {
        name
        for name, param in signature.parameters.items()
        if param.kind in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY)
    }
    excluded_names = {
        # `args` is the key of the nested GraphQL-arguments mapping itself (see `args = {"args": {}}`
        # below), so it must never be relocated -- doing so would pop that container mid-loop.
        "args",
        # Graphene already auto-handles `Argument` values for name and source, and relocating them would change
        # schema behavior for the many models that expose a `name` or `source` filter (and break existing tests).
        "name",
        "source",
    }
    # Any other reserved name that is probably not a real filter (e.g. `self`, `type_`, `_creation_counter`)
    # stays in the set but simply doesn't match; if one ever did, relocating it is the safer outcome.
    return params - excluded_names


RESERVED_GRAPHENE_FIELD_KWARGS = _build_reserved_graphene_field_kwargs()


def str_to_var_name(verbose_name):
    """Convert a string to a variable compatible name.

    Examples:
        IP Addresses > ip_addresses
    """
    return slugify_dashes_to_underscores(verbose_name)


def get_filtering_args_from_filterset(filterset_class):
    """Generate a list of filter arguments from a filterset.

    The FilterSet class will be instantiated before extracting the list of arguments to
    account for dynamic filters, inserted when the class is instantiated. (required for Custom Fields filters).

    Filter fields that are inheriting from BooleanFilter and NumberFilter will be converted
    to their appropriate type, everything else will be of type String.
    if the filter field is a subclass of MultipleChoiceFilter, the argument will be converted as a list

    Args:
        filterset_class (FilterSet): FilterSet class used to extract the argument

    Returns:
        (dict[graphene.Argument]): Filter Arguments organized in a dictionary
    """

    args = {"args": {}}
    instance = filterset_class()

    for filter_name, filter_field in instance.filters.items():
        # For general safety, but especially for the case of custom fields
        # (https://github.com/nautobot/nautobot/issues/464)
        # We don't have a way to map a GraphQL-sanitized filter name (such as "cf_my_custom_field") back to the
        # actual filter name (such as "cf_my-custom-field"), so if the sanitized filter name doesn't match the original
        # filter name, we just have to omit it for now. Better that than advertise a filter that doesn't actually work!
        if str_to_var_name(filter_name) != filter_name:
            logger.warning(
                'Filter "%s" on %s is not GraphQL safe, and will be omitted', filter_name, filterset_class.__name__
            )
            continue

        field_type = graphene.String
        filter_field_class = type(filter_field)

        if issubclass(filter_field_class, MultiValueBigNumberFilter):
            field_type = graphene.List(graphene.types.scalars.BigInt)
        elif issubclass(filter_field_class, (MultiValueFloatFilter, MultiValueDecimalFilter)):
            field_type = graphene.List(graphene.Float)
        elif issubclass(filter_field_class, MultiValueNumberFilter):
            field_type = graphene.List(graphene.Int)
        else:
            if issubclass(filter_field_class, BooleanFilter):
                field_type = graphene.Boolean
            elif issubclass(filter_field_class, NumberFilter):
                field_type = graphene.Int
            else:
                field_type = graphene.String

            if issubclass(filter_field_class, MultipleChoiceFilter):
                field_type = graphene.List(field_type)

        args[filter_name] = graphene.Argument(
            field_type,
            description=filter_field.label,
            required=False,
        )

    # Relocate filters whose names collide with reserved `graphene.Field.__init__` kwargs into the
    # nested `args` mapping (the field's GraphQL arguments) instead of letting them be splatted as
    # top-level kwargs, which graphene would otherwise consume as Field attributes.
    # Ref: https://docs.graphene-python.org/en/latest/types/objecttypes/#resolverparamgraphqlarguments
    for reserved_name in RESERVED_GRAPHENE_FIELD_KWARGS:
        if reserved_name in args:
            args["args"][reserved_name] = args.pop(reserved_name)

    if "type" in args:
        # for backwards compatibility with our filters in graphene v2 where `type` was a reserved keyword
        args["args"].update({"_type": args["type"]})

    return args


def get_permitted_pks(info, model):
    """Return the set of PKs of `model` that the requesting user is permitted to view.

    The result is cached on the request context so that restricting related/prefetched objects costs at
    most one query per model per GraphQL request, rather than one query per parent object. This lets
    callers keep a prefetched/`select_related` queryset intact and apply the permission constraints in
    Python afterwards, avoiding the N+1 regressions that a per-object `restrict()` would introduce.

    Args:
        info: GraphQL resolve info, whose `context.user` is the requesting user.
        model (Model): The related Django model whose objects are being exposed.

    Returns:
        None: The model is not restrictable, or the user has *unrestricted* view access (superuser, an
            exempt model, or a view permission with no constraints). Callers should not filter in this case.
        set: The PKs the user is permitted to view (may be empty, meaning "none permitted").
    """
    manager = getattr(model, "_default_manager", None)
    if manager is None or not hasattr(manager, "restrict"):
        return None

    user = info.context.user
    permission_required = f"{model._meta.app_label}.view_{model._meta.model_name}"

    # Fast path: superusers and exempt models have unrestricted access, so avoid materializing any PKs.
    if user.is_superuser or permission_is_exempt(permission_required):
        return None

    if not hasattr(info.context, "_gql_restrict_cache"):
        info.context._gql_restrict_cache = {}
    restrict_cache = info.context._gql_restrict_cache
    cache_key = model._meta.label
    if cache_key not in restrict_cache:
        if not user.is_authenticated or permission_required not in user.get_all_permissions():
            # No applicable permission at all -> the user may view none of these objects.
            restrict_cache[cache_key] = set()
        else:
            attrs = qs_filter_from_constraints(user._object_perm_cache[permission_required], {"$user": user})
            if not attrs:
                # Permission granted without constraints -> unrestricted; skip materializing PKs.
                restrict_cache[cache_key] = None
            else:
                restrict_cache[cache_key] = set(manager.filter(attrs).values_list("pk", flat=True))
    return restrict_cache[cache_key]


def filter_permitted_objects(info, value):
    """Filter `value` down to the related object(s) the requesting user is permitted to view.

    This is the shared primitive behind `permission_safe_resolver`. It handles the shapes a GraphQL resolver
    typically returns:

    - `None` -> `None`.
    - A single model instance -> the instance if permitted, else `None`.
    - An iterable of model instances (queryset, list, ...) -> a list containing only the permitted instances.

    Values that are not Nautobot model instances (or models without a `restrict()`-capable manager) pass
    through unchanged. Permission checks reuse the per-request cache in `get_permitted_pks`, so this does not
    add a query per object.
    """
    if value is None:
        return None
    if isinstance(value, models.Model):
        permitted = get_permitted_pks(info, value._meta.concrete_model)
        if permitted is None or value.pk in permitted:
            return value
        return None
    if isinstance(value, (str, bytes)):
        return value
    try:
        iterator = iter(value)
    except TypeError:
        return value
    permitted_by_model = {}
    result = []
    for obj in iterator:
        if not isinstance(obj, models.Model):
            result.append(obj)
            continue
        model = obj._meta.concrete_model
        if model not in permitted_by_model:
            permitted_by_model[model] = get_permitted_pks(info, model)
        permitted = permitted_by_model[model]
        if permitted is None or obj.pk in permitted:
            result.append(obj)
    return result


# Attribute set on resolver functions that enforce object-level view permissions on the related object(s)
# they return. The permission-enforcement coverage guard test relies on this to distinguish enforcing
# resolvers from ones that would leak related objects; all Nautobot-provided enforcing resolvers set it.
PERMISSION_ENFORCED_RESOLVER_ATTR = "_nautobot_permission_enforced"


def mark_permission_enforced(resolver):
    """Flag `resolver` as enforcing object-level view permissions on the related object(s) it returns.

    Set automatically by `permission_safe_resolver` / `permission_safe_attribute_resolver` and the
    auto-generated Nautobot resolvers. Apply it directly to a hand-written resolver that enforces
    permissions by some other means, so the coverage guard test recognizes it as safe.
    """
    setattr(resolver, PERMISSION_ENFORCED_RESOLVER_ATTR, True)
    return resolver


def permission_safe_resolver(resolver):
    """Decorator that enforces object-level view permissions on the related object(s) a resolver returns.

    Wrap any custom GraphQL resolver that returns related object(s) not already covered by the
    auto-generated resolvers (e.g. property-backed accessors such as `Device.all_interfaces`, or
    cable/path peer lookups). The wrapped resolver's return value is passed through
    `filter_permitted_objects`, so a non-viewable single object becomes `null` and non-viewable entries are
    dropped from returned lists.

    Example:
        ```python
        @permission_safe_resolver
        def resolve_dynamic_groups(self, info):
            return DynamicGroup.objects.get_for_object(self)
        ```
    """

    @functools.wraps(resolver)
    def wrapper(self, info, *args, **kwargs):
        return filter_permitted_objects(info, resolver(self, info, *args, **kwargs))

    return mark_permission_enforced(wrapper)


def permission_safe_attribute_resolver(attribute_name):
    """Build a permission-enforcing resolver that returns `getattr(root, attribute_name)`.

    Convenience for GraphQL fields backed by a model property/attribute (rather than a filterset, FK, or
    custom resolver), such as `Device.all_interfaces`. The attribute's value -- instance, iterable, or
    `None` -- is filtered to the objects the requesting user may view (see `permission_safe_resolver`).

    Example:
        ```python
        resolve_all_interfaces = permission_safe_attribute_resolver("all_interfaces")
        ```
    """

    @permission_safe_resolver
    def resolve(self, info, **kwargs):
        return getattr(self, attribute_name, None)

    return resolve


def construct_resolver(model_name, resolver_type):
    """Constructs a resolve_[cable_peer|connected_endpoint]_<endpoint> function for a given model type.

    The returned resolver enforces object-level view permissions on the peer object (see
    `permission_safe_resolver`), so a peer the requesting user is not permitted to view is returned as null.

    Args:
        model_name (str): Name of the model to construct a resolver function for (e.g. CircuitTermination).
        resolver_type (str): One of ['connected_endpoint', 'cable_peer']
    """
    if resolver_type == "cable_peer":

        def resolve_cable_peer(self, info):
            peer = self.get_cable_peer()
            if type(peer).__name__ == model_name:
                return filter_permitted_objects(info, peer)
            return None

        return mark_permission_enforced(resolve_cable_peer)

    if resolver_type == "connected_endpoint":

        def resolve_connected_endpoint(self, info):
            peer = self.connected_endpoint
            if type(peer).__name__ == model_name:
                return filter_permitted_objects(info, peer)
            return None

        return mark_permission_enforced(resolve_connected_endpoint)

    raise ValueError(f"resolver_type must be 'cable_peer' or 'connected_endpoint', not '{resolver_type}'")
