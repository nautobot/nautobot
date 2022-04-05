"""Schema module for GraphQL."""
from collections import OrderedDict
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.reverse_related import ManyToOneRel, OneToOneRel

import graphene
from graphene.types import generic

from nautobot.circuits.graphql.types import CircuitTerminationType
from nautobot.core.graphql.utils import str_to_var_name
from nautobot.core.graphql.generators import (
    generate_attrs_for_schema_type,
    generate_computed_field_resolver,
    generate_custom_field_resolver,
    generate_filter_resolver,
    generate_list_search_parameters,
    generate_relationship_resolver,
    generate_restricted_queryset,
    generate_schema_type,
    generate_null_choices_resolver,
)
from nautobot.core.graphql.types import ContentTypeType
from nautobot.dcim.graphql.types import (
    CableType,
    CablePathType,
    ConsolePortType,
    ConsoleServerPortType,
    DeviceType,
    FrontPortType,
    InterfaceType,
    PowerFeedType,
    PowerOutletType,
    PowerPortType,
    RackType,
    RearPortType,
    SiteType,
)
from nautobot.extras.registry import registry
from nautobot.extras.models import ComputedField, CustomField, Relationship
from nautobot.extras.choices import CustomFieldTypeChoices, RelationshipSideChoices
from nautobot.extras.graphql.types import TagType
from nautobot.ipam.graphql.types import AggregateType, IPAddressType, PrefixType
from nautobot.virtualization.graphql.types import VirtualMachineType, VMInterfaceType

logger = logging.getLogger("nautobot.graphql.schema")

registry["graphql_types"] = OrderedDict()
registry["graphql_types"]["circuits.circuittermination"] = CircuitTerminationType
registry["graphql_types"]["contenttypes.contenttype"] = ContentTypeType
registry["graphql_types"]["dcim.cable"] = CableType
registry["graphql_types"]["dcim.cablepath"] = CablePathType
registry["graphql_types"]["dcim.consoleport"] = ConsolePortType
registry["graphql_types"]["dcim.consoleserverport"] = ConsoleServerPortType
registry["graphql_types"]["dcim.device"] = DeviceType
registry["graphql_types"]["dcim.frontport"] = FrontPortType
registry["graphql_types"]["dcim.interface"] = InterfaceType
registry["graphql_types"]["dcim.powerfeed"] = PowerFeedType
registry["graphql_types"]["dcim.poweroutlet"] = PowerOutletType
registry["graphql_types"]["dcim.powerport"] = PowerPortType
registry["graphql_types"]["dcim.rack"] = RackType
registry["graphql_types"]["dcim.rearport"] = RearPortType
registry["graphql_types"]["dcim.site"] = SiteType
registry["graphql_types"]["extras.tag"] = TagType
registry["graphql_types"]["ipam.aggregate"] = AggregateType
registry["graphql_types"]["ipam.ipaddress"] = IPAddressType
registry["graphql_types"]["ipam.prefix"] = PrefixType
registry["graphql_types"]["virtualization.virtualmachine"] = VirtualMachineType
registry["graphql_types"]["virtualization.vminterface"] = VMInterfaceType


STATIC_TYPES = registry["graphql_types"].keys()

CUSTOM_FIELD_MAPPING = {
    CustomFieldTypeChoices.TYPE_INTEGER: graphene.Int(),
    CustomFieldTypeChoices.TYPE_TEXT: graphene.String(),
    CustomFieldTypeChoices.TYPE_BOOLEAN: graphene.Boolean(),
    CustomFieldTypeChoices.TYPE_DATE: graphene.Date(),
    CustomFieldTypeChoices.TYPE_URL: graphene.String(),
    CustomFieldTypeChoices.TYPE_SELECT: graphene.String(),
}


def extend_schema_type(schema_type):
    """Extend an existing schema type to add fields dynamically.

    The following type of dynamic fields/functions are currently supported:
     - Queryset, ensure a restricted queryset is always returned.
     - Custom Field, all custom field will be defined as a first level attribute.
     - Tags, Tags will automatically be resolvable.
     - Config Context, add a config_context attribute and resolver.
     - Relationships, all relationships will be defined as a first level attribute.

    To insert a new field dynamically,
     - The field must be declared in schema_type._meta.fields as a graphene.Field.mounted
     - A Callable attribute name "resolver_<field_name>" must be defined at the schema_type level
    """

    model = schema_type._meta.model

    #
    # Queryset
    #
    setattr(schema_type, "get_queryset", generate_restricted_queryset())

    #
    # Custom Fields
    #
    schema_type = extend_schema_type_custom_field(schema_type, model)

    #
    # Tags
    #
    schema_type = extend_schema_type_tags(schema_type, model)

    #
    # Config Context
    #
    schema_type = extend_schema_type_config_context(schema_type, model)

    #
    # Relationships
    #
    schema_type = extend_schema_type_relationships(schema_type, model)

    #
    # Computed Fields
    #
    schema_type = extend_schema_type_computed_field(schema_type, model)

    #
    # Add resolve_{field.name} that has null=False, blank=True, and choices defined to return null
    #
    schema_type = extend_schema_type_null_field_choice(schema_type, model)

    #
    # Add multiple layers of filtering
    #
    schema_type = extend_schema_type_filter(schema_type, model)

    return schema_type


def extend_schema_type_null_field_choice(schema_type, model):
    """Extends the schema fields to add fields that can be null, blank=True, and choices are defined.

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model
        model (Model): Django model

    Returns:
        schema_type (DjangoObjectType)
    """
    # This is a workaround implemented for https://github.com/nautobot/nautobot/issues/466#issuecomment-877991184
    # We want to iterate over fields and see if they meet the criteria: null=False, blank=True, and choices defined
    for field in model._meta.fields:
        # Continue onto the next field if it doesn't match the criteria
        if not all((not field.null, field.blank, field.choices)):
            continue

        field_name = f"{str_to_var_name(field.name)}"
        resolver_name = f"resolve_{field_name}"

        if hasattr(schema_type, resolver_name):
            logger.warning(
                f"Unable to add {field.name} to {schema_type._meta.name} "
                f"because there is already an attribute with the same name ({field_name})"
            )
            continue

        setattr(
            schema_type,
            resolver_name,
            generate_null_choices_resolver(field.name, resolver_name),
        )

    return schema_type


def extend_schema_type_filter(schema_type, model):
    """Extend schema_type object to be able to filter on multiple levels of a query

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model
        model (Model): Django model

    Returns:
        schema_type (DjangoObjectType)
    """
    for field in model._meta.get_fields():
        # Check attribute is a ManyToOne field
        # OneToOneRel is a subclass of ManyToOneRel, but we don't want to treat is as a list
        if not isinstance(field, ManyToOneRel) or isinstance(field, OneToOneRel):
            continue
        child_schema_type = registry["graphql_types"].get(field.related_model._meta.label_lower)
        if child_schema_type:
            resolver_name = f"resolve_{field.name}"
            search_params = generate_list_search_parameters(child_schema_type)
            # Add OneToMany field to schema_type
            schema_type._meta.fields[field.name] = graphene.Field.mounted(
                graphene.List(child_schema_type, **search_params)
            )
            # Add resolve function to schema_type
            setattr(schema_type, resolver_name, generate_filter_resolver(child_schema_type, resolver_name, field.name))
    return schema_type


def extend_schema_type_custom_field(schema_type, model):
    """Extend schema_type object to had attribute and resolver around custom_fields.
    Each custom field will be defined as a first level attribute.

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model
        model (Model): Django model

    Returns:
        schema_type (DjangoObjectType)
    """

    cfs = CustomField.objects.get_for_model(model)
    prefix = ""
    if settings.GRAPHQL_CUSTOM_FIELD_PREFIX and isinstance(settings.GRAPHQL_CUSTOM_FIELD_PREFIX, str):
        prefix = f"{settings.GRAPHQL_CUSTOM_FIELD_PREFIX}_"

    for field in cfs:
        field_name = f"{prefix}{str_to_var_name(field.name)}"
        resolver_name = f"resolve_{field_name}"

        if hasattr(schema_type, resolver_name):
            logger.warning(
                f"Unable to add the custom field {field.name} to {schema_type._meta.name} "
                f"because there is already an attribute with the same name ({field_name})"
            )
            continue

        setattr(
            schema_type,
            resolver_name,
            generate_custom_field_resolver(field.name, resolver_name),
        )

        if field.type in CUSTOM_FIELD_MAPPING:
            schema_type._meta.fields[field_name] = graphene.Field.mounted(CUSTOM_FIELD_MAPPING[field.type])
        else:
            schema_type._meta.fields[field_name] = graphene.Field.mounted(graphene.String())

    return schema_type


def extend_schema_type_computed_field(schema_type, model):
    """Extend schema_type object to had attribute and resolver around computed_fields.
    Each computed field will be defined as a first level attribute.

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model
        model (Model): Django model

    Returns:
        schema_type (DjangoObjectType)
    """

    cfs = ComputedField.objects.get_for_model(model)
    prefix = ""
    if settings.GRAPHQL_COMPUTED_FIELD_PREFIX and isinstance(settings.GRAPHQL_COMPUTED_FIELD_PREFIX, str):
        prefix = f"{settings.GRAPHQL_COMPUTED_FIELD_PREFIX}_"

    for field in cfs:
        field_name = f"{prefix}{str_to_var_name(field.slug)}"
        resolver_name = f"resolve_{field_name}"

        if hasattr(schema_type, resolver_name):
            logger.warning(
                "Unable to add the computed field %s to %s because there is already an attribute with the same name (%s)",
                field.slug,
                schema_type._meta.slug,
                field_name,
            )
            continue

        setattr(
            schema_type,
            resolver_name,
            generate_computed_field_resolver(field.slug, resolver_name),
        )

        schema_type._meta.fields[field_name] = graphene.Field.mounted(graphene.String())

    return schema_type


def extend_schema_type_tags(schema_type, model):
    """Extend schema_type object to had a resolver for tags.

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model
        model (Model): Django model

    Returns:
        schema_type (DjangoObjectType)
    """

    fields_name = [field.name for field in model._meta.get_fields()]
    if "tags" not in fields_name:
        return schema_type

    def resolve_tags(self, args):
        return self.tags.all()

    setattr(schema_type, "resolve_tags", resolve_tags)

    return schema_type


def extend_schema_type_config_context(schema_type, model):
    """Extend schema_type object to had attribute and resolver around config_context.

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model
        model (Model): Django model

    Returns:
        schema_type (DjangoObjectType)
    """

    fields_name = [field.name for field in model._meta.get_fields()]
    if "local_context_data" not in fields_name:
        return schema_type

    def resolve_config_context(self, args):
        return self.get_config_context()

    schema_type._meta.fields["config_context"] = graphene.Field.mounted(generic.GenericScalar())
    setattr(schema_type, "resolve_config_context", resolve_config_context)

    return schema_type


def extend_schema_type_relationships(schema_type, model):
    """Extend the schema type with attributes and resolvers corresponding
    to the relationships associated with this model."""

    ct = ContentType.objects.get_for_model(model)
    relationships_by_side = {
        "source": Relationship.objects.filter(source_type=ct),
        "destination": Relationship.objects.filter(destination_type=ct),
    }

    prefix = ""
    if settings.GRAPHQL_RELATIONSHIP_PREFIX and isinstance(settings.GRAPHQL_RELATIONSHIP_PREFIX, str):
        prefix = f"{settings.GRAPHQL_RELATIONSHIP_PREFIX}_"

    for side, relationships in relationships_by_side.items():
        for relationship in relationships:
            peer_side = RelationshipSideChoices.OPPOSITE[side]

            # Generate the name of the attribute and the name of the resolver based on the slug of the relationship
            # and based on the prefix
            rel_name = f"{prefix}{str_to_var_name(relationship.slug)}"
            # Handle non-symmetric relationships where the model can be either source or destination
            if not relationship.symmetric and relationship.source_type == relationship.destination_type:
                rel_name = f"{rel_name}_{peer_side}"
            resolver_name = f"resolve_{rel_name}"

            if hasattr(schema_type, resolver_name):
                # If a symmetric relationship, and this is destination side, we already added source side, expected
                # Otherwise something is wrong and we should warn
                if side != "destination" or not relationship.symmetric:
                    logger.warning(
                        f"Unable to add the custom relationship {relationship.slug} to {schema_type._meta.name} "
                        f"because there is already an attribute with the same name ({rel_name})"
                    )
                continue

            # Identify which object needs to be on the other side of this relationship
            # and check the registry to see if it is available,
            peer_type = getattr(relationship, f"{peer_side}_type")
            peer_model = peer_type.model_class()
            if not peer_model:
                # Could happen if, for example, we have a leftover relationship defined for a model from a plugin
                # that is no longer installed/enabled
                logger.warning(f"Unable to find peer model {peer_type} to create GraphQL relationship")
                continue
            type_identifier = f"{peer_model._meta.app_label}.{peer_model._meta.model_name}"
            rel_schema_type = registry["graphql_types"].get(type_identifier)

            if not rel_schema_type:
                logger.warning(f"Unable to identify the GraphQL Object Type for {type_identifier} in the registry.")
                continue

            if relationship.has_many(peer_side):
                schema_type._meta.fields[rel_name] = graphene.Field.mounted(graphene.List(rel_schema_type))
            else:
                schema_type._meta.fields[rel_name] = graphene.Field(rel_schema_type)

            # Generate and assign the resolver
            setattr(
                schema_type,
                resolver_name,
                generate_relationship_resolver(rel_name, resolver_name, relationship, side, peer_model),
            )

    return schema_type


def generate_query_mixin():
    """Generates and returns a class definition representing a GraphQL schema."""

    logger.info("Beginning generation of Nautobot GraphQL schema")

    class_attrs = {}

    def already_present(model):
        """Check if a model and its resolvers are staged to added to the Mixin."""

        single_item_name = str_to_var_name(model._meta.verbose_name)
        list_name = str_to_var_name(model._meta.verbose_name_plural)

        if single_item_name in class_attrs:
            logger.warning(
                f"Unable to register the schema single type '{single_item_name}' in GraphQL, "
                f"there is already another type {class_attrs[single_item_name]._type} registered under this name"
            )
            return True

        if list_name in class_attrs:
            logger.warning(
                f"Unable to register the schema list type '{list_name}' in GraphQL, "
                f"there is already another type {class_attrs[list_name]._type} registered under this name"
            )
            return True

        return False

    logger.debug("Generating dynamic schemas for all models in the models_features graphql registry")
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

            type_identifier = f"{app_name}.{model_name}"

            if type_identifier in registry["graphql_types"].keys():
                # Skip models that have been added statically
                continue

            schema_type = generate_schema_type(app_name=app_name, model=model)
            registry["graphql_types"][type_identifier] = schema_type

    logger.debug("Adding plugins' statically defined graphql schema types")
    # After checking for conflict
    for schema_type in registry["plugin_graphql_types"]:
        model = schema_type._meta.model
        type_identifier = f"{model._meta.app_label}.{model._meta.model_name}"

        if type_identifier in registry["graphql_types"]:
            logger.warning(
                f'Unable to load schema type for the model "{type_identifier}" as there is already another type '
                "registered under this name. If you are seeing this message during plugin development, check to "
                "make sure that you aren't using @extras_features(\"graphql\") on the same model you're also "
                "defining a custom GraphQL type for."
            )
        else:
            registry["graphql_types"][type_identifier] = schema_type

    logger.debug("Extending all registered schema types with dynamic attributes")
    for schema_type in registry["graphql_types"].values():

        if already_present(schema_type._meta.model):
            continue

        schema_type = extend_schema_type(schema_type)
        class_attrs.update(generate_attrs_for_schema_type(schema_type))

    QueryMixin = type("QueryMixin", (object,), class_attrs)
    logger.info("Generation of Nautobot GraphQL schema complete")
    return QueryMixin
