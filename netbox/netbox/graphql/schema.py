"""Schema module for GraphQL."""
import logging

from django.conf import settings
from django.db.models.fields import BinaryField
from django.contrib.contenttypes.models import ContentType

import graphene
from graphene_django.converter import convert_django_field
from graphene_django.types import ObjectType

from dcim.graphql.types import SiteType, DeviceType, InterfaceType, RackType, CableType, ConsoleServerPortType
from ipam.graphql.types import IPAddressType
from circuits.graphql.types import CircuitTerminationType
from extras.registry import registry
from extras.models import CustomField
from extras.choices import CustomFieldTypeChoices
from extras.graphql.types import TagType
from netbox.graphql.utils import str_to_var_name
from netbox.graphql.generators import (
    generate_schema_type,
    generate_custom_field_resolver,
    generate_restricted_queryset,
    generate_attrs_for_schema_type,
)

logger = logging.getLogger(__name__)

STATIC_TYPES = {
    "dcim.site": SiteType,
    "dcim.device": DeviceType,
    "dcim.interface": InterfaceType,
    "dcim.rack": RackType,
    "dcim.cable": CableType,
    "dcim.consoleserverport": ConsoleServerPortType,
    "ipam.ipaddress": IPAddressType,
    "circuits.circuittermination": CircuitTerminationType,
    "extras.tag": TagType
}

CUSTOM_FIELD_MAPPING = {
    CustomFieldTypeChoices.TYPE_INTEGER: graphene.Int(),
    CustomFieldTypeChoices.TYPE_TEXT: graphene.String(),
    CustomFieldTypeChoices.TYPE_BOOLEAN: graphene.Boolean(),
    CustomFieldTypeChoices.TYPE_DATE: graphene.Date(),
    CustomFieldTypeChoices.TYPE_URL: graphene.String(),
    CustomFieldTypeChoices.TYPE_SELECT: graphene.String(),
}


def extend_schema_type(schema_type, ext_queryset=True, ext_tags=True, ext_custom_fields=True):
    """Extend an existing schema type to add fields dynamically.

    The following type of dynamic fields/functions are currently supported:
     - Queryset, ensure a restricted queryset is always returned.
     - Custom Field, all custom field will be defined as a first level attribute
     - Tags, Tags will automatically be resolvable.

    To insert a new field dynamically,
     - The field must be declared in schema_type._meta.fields as a graphene.Field.mounted
     - A Callable attribute name "resolver_<field_name>" must be defined at the schema_type level
    """

    model = schema_type._meta.model
    fields_name = [field.name for field in model._meta.get_fields()]

    #
    # ID, Force Id as an Integer, currently it's recognized as a String
    #
    if "id" in schema_type._meta.fields:
        schema_type._meta.fields["id"] = graphene.Field.mounted(graphene.Int())

    #
    # Queryset,
    #
    if ext_queryset:
        setattr(schema_type, "get_queryset", generate_restricted_queryset())

    #
    # Custom Fields, Each custom field will be defined as a first level attribute
    #
    if ext_custom_fields:
        cfs = CustomField.objects.get_for_model(model)

        prefix = ""
        if settings.GRAPHQL_CUSTOM_FIELD_PREFIX and isinstance(settings.GRAPHQL_CUSTOM_FIELD_PREFIX, str):
            prefix = f"{settings.GRAPHQL_CUSTOM_FIELD_PREFIX}_"

        for field in cfs:
            field_name = f"{prefix}{str_to_var_name(field.name)}"
            resolver_name = f"resolve_{field_name}"

            if hasattr(schema_type, field_name):
                logger.debug(
                    f"Unable to add the custom field {field.name} to {schema_type._meta.name} "
                    f"because there is already an attribute with the same name ({field_name})"
                )
                continue

            setattr(schema_type, resolver_name, generate_custom_field_resolver(field.name, resolver_name))

            if field.type in CUSTOM_FIELD_MAPPING:
                schema_type._meta.fields[field_name] = graphene.Field.mounted(CUSTOM_FIELD_MAPPING[field.type])
            else:
                schema_type._meta.fields[field_name] = graphene.Field.mounted(graphene.String())

        if cfs:
            del(schema_type._meta.fields["custom_field_data"])

    #
    # Tags
    #
    if ext_tags and "tags" in fields_name:
        # For Tags we only need to define the resolver because the field itself is already defined.
        def resolve_tags(self, args):
            return self.tags.all()

        setattr(schema_type, "resolve_tags", resolve_tags)

    return schema_type


def generate_query_mixin():
    """Generates and returns a class definition representing a GraphQL schema."""

    class_attrs = {}

    def already_present(model):

        single_item_name = str_to_var_name(model._meta.verbose_name)
        list_name = str_to_var_name(model._meta.verbose_name_plural)

        if single_item_name in class_attrs:
            logger.warning(
                f"Unable to register the schema type '{single_item_name}' in GraphQL from '{app_name}':'{model_name}',"
                "there is already another type registered under this name"
            )
            return True

        if list_name in class_attrs:
            logger.warning(
                f"Unable to register the schema type '{list_name}' in GraphQL from '{app_name}':'{model_name}',"
                "there is already another type registered under this name"
            )
            return True

    # Generate Resolver for all SchemaType statically defined
    for schema_type in STATIC_TYPES.values():

        # Extend schema_type with dynamic attributes
        schema_type = extend_schema_type(schema_type)
        class_attrs.update(generate_attrs_for_schema_type(schema_type))

    # Generate SchemaType Dynamically for all Models registered in the model_features registry
    #  - Ensure an attribute/schematype with the same name doesn't already exist
    registered_models = registry.get("model_features", {}).get("graphql", {})
    for app_name, models in registered_models.items():
        for model_name in models:

            try:
                # Find the model class based on the content type
                ct = ContentType.objects.get(app_label=app_name, model=model_name)
                model = ct.model_class()
            except ContentType.DoesNotExist:
                logger.warning(
                    f"Unable to generate a schema type for the model '{app_name}.{model_name}' in GraphQL,"
                    "this model doesn't have an associated ContentType, please create the Object manually."
                )
                continue

            if f"{app_name}.{model_name}" in STATIC_TYPES.keys():
                # Skip models that have been added statically
                continue

            if already_present(model):
                continue

            schema_type = generate_schema_type(app_name=app_name, model=model)

            # Extend schema_type with dynamic attributes
            schema_type = extend_schema_type(schema_type)

            class_attrs.update(generate_attrs_for_schema_type(schema_type))

    # Generate Resolvers for all SchemaType present in the plugin registry
    for schema_type in registry["plugin_graphql_types"]:

        if already_present(schema_type._meta.model):
            continue

        # Extend schema_type with dynamic attributes
        schema_type = extend_schema_type(schema_type)
        class_attrs.update(generate_attrs_for_schema_type(schema_type))

    QueryMixin = type("QueryMixin", (object,), class_attrs)
    return QueryMixin


@convert_django_field.register(BinaryField)
def convert_field_to_string(field, registry=None):
    """Convert BinaryField to String."""
    return graphene.String()
