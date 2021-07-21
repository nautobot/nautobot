"""Library of generators for GraphQL."""

import logging

import django_filters.fields
import graphene
from graphql import GraphQLError
from graphene_django import DjangoObjectType

from nautobot.core.graphql.utils import str_to_var_name, get_filtering_args_from_filterset
from nautobot.extras.choices import RelationshipSideChoices
from nautobot.extras.models import RelationshipAssociation
from nautobot.utilities.utils import get_filterset_for_model

logger = logging.getLogger("nautobot.graphql.generators")
RESOLVER_PREFIX = "resolve_"


def generate_restricted_queryset():
    """
    Generate a function to return a restricted queryset compatible with the internal permissions system.

    Note that for built-in models such as ContentType the queryset has no `restrict` method, so we have to
    fail gracefully in that case.
    """

    def get_queryset(queryset, info):
        if not hasattr(queryset, "restrict"):
            logger.debug(f"Queryset {queryset} is not restrictable")
            return queryset
        return queryset.restrict(info.context.user, "view")

    return get_queryset


def generate_null_choices_resolver(name, resolver_name):
    """
    Generate function to resolve appropriate type when a field has `null=False` (default), `blank=True`, and
    `choices` defined.

    Args:
        name (str): name of the field to resolve
        resolver_name (str): name of the resolver as declare in DjangoObjectType
    """

    def resolve_fields_w_choices(model, info, **kwargs):
        field_value = getattr(model, name)
        if field_value:
            return field_value
        return None

    resolve_fields_w_choices.__name__ = resolver_name
    return resolve_fields_w_choices


def generate_custom_field_resolver(name, resolver_name):
    """Generate function to resolve each custom field within each DjangoObjectType.

    Args:
        name (str): name of the custom field to resolve
        resolver_name (str): name of the resolver as declare in DjangoObjectType
    """

    def resolve_custom_field(self, info, **kwargs):
        return self.cf.get(name, None)

    resolve_custom_field.__name__ = resolver_name
    return resolve_custom_field


def generate_computed_field_resolver(name, resolver_name):
    """Generate an instance method for resolving an individual computed field within a given DjangoObjectType.

    Args:
        name (str): name of the computed field to resolve
        resolver_name (str): name of the resolver as declare in DjangoObjectType
    """

    def resolve_computed_field(self, info, **kwargs):
        return self.get_computed_field(slug=name)

    resolve_computed_field.__name__ = resolver_name
    return resolve_computed_field


def generate_relationship_resolver(name, resolver_name, relationship, side, peer_model):
    """Generate function to resolve each custom relationship within each DjangoObjectType.

    Args:
        name (str): name of the custom field to resolve
        resolver_name (str): name of the resolver as declare in DjangoObjectType
        relationship (Relationship): Relationship object to generate a resolver for
        site (site): side of the relationship to use for the resolver
        peer_model (Model): Django Model of the peer of this relationship
    """

    def resolve_relationship(self, info, **kwargs):
        """Return a queryset or an object depending on the type of the relationship."""
        peer_side = RelationshipSideChoices.OPPOSITE[side]
        query_params = {"relationship": relationship}
        query_params[f"{side}_id"] = self.pk
        queryset_ids = RelationshipAssociation.objects.filter(**query_params).values_list(f"{peer_side}_id", flat=True)

        if relationship.has_many(peer_side):
            return peer_model.objects.filter(id__in=queryset_ids)

        return peer_model.objects.filter(id__in=queryset_ids).first()

    resolve_relationship.__name__ = resolver_name
    return resolve_relationship


def generate_schema_type(app_name: str, model: object) -> DjangoObjectType:
    """
    Take a Django model and generate a Graphene Type class definition.

    Args:
        app_name (str): name of the application or plugin the Model is part of.
        model (object): Django Model

    Example:
        For a model with a name of "Device", the following class definition is generated:

        class DeviceType(DjangoObjectType):
            Meta:
                model = Device
                fields = ["__all__"]

        If a FilterSet exists for this model at
        '<app_name>.filters.<ModelName>FilterSet' the filterset will be stored in
        filterset_class as follows:

        class DeviceType(DjangoObjectType):
            Meta:
                model = Device
                fields = ["__all__"]
                filterset_class = DeviceFilterSet
    """

    main_attrs = {}
    meta_attrs = {"model": model, "fields": "__all__"}

    # We'll attempt to find a FilterSet corresponding to the model
    # Not all models have a FilterSet defined so the function return none if it can't find a filterset
    meta_attrs["filterset_class"] = get_filterset_for_model(model)

    main_attrs["Meta"] = type("Meta", (object,), meta_attrs)

    schema_type = type(f"{model.__name__}Type", (DjangoObjectType,), main_attrs)
    return schema_type


def generate_list_search_parameters(schema_type):
    """Generate list of query parameters for the list resolver based on a filterset."""

    search_params = {}
    if schema_type._meta.filterset_class is not None:
        search_params = get_filtering_args_from_filterset(
            schema_type._meta.filterset_class,
        )

    return search_params


def generate_single_item_resolver(schema_type, resolver_name):
    """Generate a resolver for a single element of schema_type

    Args:
        schema_type (DjangoObjectType): DjangoObjectType for a given model
        resolver_name (str): name of the resolver

    Returns:
        callable: Resolver function for a single element
    """
    model = schema_type._meta.model

    def single_resolver(self, info, **kwargs):

        obj_id = kwargs.get("id", None)
        if obj_id:
            return model.objects.restrict(info.context.user, "view").get(pk=obj_id)
        return None

    single_resolver.__name__ = resolver_name
    return single_resolver


def generate_list_resolver(schema_type, resolver_name):
    """
    Generate resolver for a list of schema_type.

    If a filterset_class is associated with the schema_type,
    the resolver will pass all arguments received to the FilterSet
    If not, it will return a restricted queryset for all objects

    Args:
        schema_type (DjangoObjectType): DjangoObjectType for a given model
        resolver_name (str): name of the resolver

    Returns:
        callable: Resolver function for list of element
    """
    model = schema_type._meta.model

    def list_resolver(self, info, **kwargs):
        filterset_class = schema_type._meta.filterset_class
        if filterset_class is not None:
            resolved_obj = filterset_class(kwargs, model.objects.restrict(info.context.user, "view").all())

            # Check result filter for errors.
            if resolved_obj.errors:
                errors = {}

                # Build error message from results
                # Error messages are collected from each filter object
                for key in resolved_obj.errors:
                    errors[key] = resolved_obj.errors[key]

                # Raising this exception will send the error message in the response of the GraphQL request
                raise GraphQLError(errors)

            return resolved_obj.qs.all()

        return model.objects.restrict(info.context.user, "view").all()

    list_resolver.__name__ = resolver_name
    return list_resolver


def generate_attrs_for_schema_type(schema_type):
    """Generate both attributes and resolvers for a given schema_type.

    Args:
        schema_type (DjangoObjectType): DjangoObjectType for a given model

    Returns:
        dict: Dict of attributes ready to merge into the QueryMixin class
    """
    attrs = {}
    model = schema_type._meta.model

    single_item_name = str_to_var_name(model._meta.verbose_name)
    list_name = str_to_var_name(model._meta.verbose_name_plural)

    # Define Attributes for single item and list with their search parameters
    search_params = generate_list_search_parameters(schema_type)
    attrs[single_item_name] = graphene.Field(schema_type, id=graphene.ID())
    attrs[list_name] = graphene.List(schema_type, **search_params)

    # Define Resolvers for both single item and list
    single_item_resolver_name = f"{RESOLVER_PREFIX}{single_item_name}"
    list_resolver_name = f"{RESOLVER_PREFIX}{list_name}"
    attrs[single_item_resolver_name] = generate_single_item_resolver(schema_type, single_item_resolver_name)
    attrs[list_resolver_name] = generate_list_resolver(schema_type, list_resolver_name)

    return attrs
