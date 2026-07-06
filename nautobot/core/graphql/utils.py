import inspect
import logging

from django_filters.filters import BooleanFilter, MultipleChoiceFilter, NumberFilter
import graphene

from nautobot.core.filters import (
    MultiValueBigNumberFilter,
    MultiValueDecimalFilter,
    MultiValueFloatFilter,
    MultiValueNumberFilter,
)
from nautobot.core.models.fields import slugify_dashes_to_underscores

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


def construct_resolver(model_name, resolver_type):
    """Constructs a resolve_[cable_peer|connected_endpoint]_<endpoint> function for a given model type.

    Args:
        model_name (str): Name of the model to construct a resolver function for (e.g. CircuitTermination).
        resolver_type (str): One of ['connected_endpoint', 'cable_peer']
    """
    if resolver_type == "cable_peer":

        def resolve_cable_peer(self, args):
            peer = self.get_cable_peer()
            if type(peer).__name__ == model_name:
                return peer
            return None

        return resolve_cable_peer

    if resolver_type == "connected_endpoint":

        def resolve_connected_endpoint(self, args):
            peer = self.connected_endpoint
            if type(peer).__name__ == model_name:
                return peer
            return None

        return resolve_connected_endpoint

    raise ValueError(f"resolver_type must be 'cable_peer' or 'connected_endpoint', not '{resolver_type}'")
