"""Schema module for GraphQL."""

from collections import OrderedDict
import logging

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import ValidationError
from django.db.models import ManyToManyField
from django.db.models.fields.reverse_related import ManyToManyRel, ManyToOneRel, OneToOneRel
import graphene
from graphene.types import generic

from nautobot.circuits.graphql.types import CircuitTerminationType
from nautobot.core.graphql.generators import (
    generate_attrs_for_schema_type,
    generate_computed_field_resolver,
    generate_custom_field_resolver,
    generate_filter_resolver,
    generate_list_search_parameters,
    generate_null_choices_resolver,
    generate_relationship_resolver,
    generate_restricted_queryset,
    generate_schema_type,
)
from nautobot.core.graphql.types import ContentTypeType, DateType, JSON
from nautobot.core.graphql.utils import str_to_var_name
from nautobot.dcim.graphql.types import (
    CablePathType,
    CableType,
    ConsolePortType,
    ConsoleServerPortType,
    DeviceType,
    FrontPortType,
    InterfaceType,
    LocationType,
    ModuleBayType,
    ModuleType,
    PlatformType,
    PowerFeedType,
    PowerOutletType,
    PowerPortType,
    RackType,
    RearPortType,
)
from nautobot.extras.choices import CustomFieldTypeChoices, RelationshipSideChoices
from nautobot.extras.graphql.types import ContactAssociationType, DynamicGroupType, JobType, ScheduledJobType, TagType
from nautobot.extras.models import ComputedField, CustomField, Relationship
from nautobot.extras.registry import registry
from nautobot.extras.utils import check_if_key_is_graphql_safe
from nautobot.ipam.graphql.types import IPAddressType, PrefixType, VLANType
from nautobot.virtualization.graphql.types import VirtualMachineType, VMInterfaceType

logger = logging.getLogger(__name__)

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
registry["graphql_types"]["dcim.modulebay"] = ModuleBayType
registry["graphql_types"]["dcim.module"] = ModuleType
registry["graphql_types"]["dcim.platform"] = PlatformType
registry["graphql_types"]["dcim.powerfeed"] = PowerFeedType
registry["graphql_types"]["dcim.poweroutlet"] = PowerOutletType
registry["graphql_types"]["dcim.powerport"] = PowerPortType
registry["graphql_types"]["dcim.rack"] = RackType
registry["graphql_types"]["dcim.rearport"] = RearPortType
registry["graphql_types"]["dcim.location"] = LocationType
registry["graphql_types"]["extras.contactassociation"] = ContactAssociationType
registry["graphql_types"]["extras.dynamicgroup"] = DynamicGroupType
registry["graphql_types"]["extras.job"] = JobType
registry["graphql_types"]["extras.scheduledjob"] = ScheduledJobType
registry["graphql_types"]["extras.tag"] = TagType
registry["graphql_types"]["ipam.ipaddress"] = IPAddressType
registry["graphql_types"]["ipam.prefix"] = PrefixType
registry["graphql_types"]["ipam.vlan"] = VLANType
registry["graphql_types"]["virtualization.virtualmachine"] = VirtualMachineType
registry["graphql_types"]["virtualization.vminterface"] = VMInterfaceType


STATIC_TYPES = registry["graphql_types"].keys()

CUSTOM_FIELD_MAPPING = {
    CustomFieldTypeChoices.TYPE_INTEGER: graphene.Int(),
    CustomFieldTypeChoices.TYPE_TEXT: graphene.String(),
    CustomFieldTypeChoices.TYPE_BOOLEAN: graphene.Boolean(),
    CustomFieldTypeChoices.TYPE_DATE: DateType(),
    CustomFieldTypeChoices.TYPE_URL: graphene.String(),
    CustomFieldTypeChoices.TYPE_SELECT: graphene.String(),
    CustomFieldTypeChoices.TYPE_JSON: JSON(),
    CustomFieldTypeChoices.TYPE_MULTISELECT: graphene.List(graphene.String),
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
    # Global features (contacts, teams, dynamic groups)
    #
    schema_type = extend_schema_type_global_features(schema_type, model)

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
        (DjangoObjectType): The extended schema_type object
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
                'Unable to add "%s" to %s because there is already an attribute mapped to the same name ("%s")',
                field.name,
                schema_type._meta.name,
                field_name,
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
        (DjangoObjectType): The extended schema_type object
    """
    for field in model._meta.get_fields():
        if not isinstance(field, (ManyToManyField, ManyToManyRel, ManyToOneRel, GenericRelation)):
            continue
        # OneToOneRel is a subclass of ManyToOneRel, but we don't want to treat it as a list
        if isinstance(field, OneToOneRel):
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
        (DjangoObjectType): The extended schema_type object
    """

    custom_fields = CustomField.objects.get_for_model(model, get_queryset=False)
    prefix = ""
    if settings.GRAPHQL_CUSTOM_FIELD_PREFIX and isinstance(settings.GRAPHQL_CUSTOM_FIELD_PREFIX, str):
        prefix = f"{settings.GRAPHQL_CUSTOM_FIELD_PREFIX}_"

    for field in custom_fields:
        # Since we guaranteed cf.key's uniqueness in CustomField data migration
        # We can safely field_key this in our GraphQL without duplication
        # For new CustomField instances, we also make sure that duplicate key does not exist.
        field_key = f"{prefix}{field.key}"
        resolver_name = f"resolve_{field_key}"

        if hasattr(schema_type, resolver_name):
            logger.warning(
                'Unable to add the custom field "%s" to %s '
                'because there is already an attribute mapped to the same name ("%s")',
                field,
                schema_type._meta.name,
                field_key,
            )
            continue

        setattr(
            schema_type,
            resolver_name,
            generate_custom_field_resolver(field.key, resolver_name),
        )

        if field.type in CUSTOM_FIELD_MAPPING:
            schema_type._meta.fields[field_key] = graphene.Field.mounted(CUSTOM_FIELD_MAPPING[field.type])
        else:
            schema_type._meta.fields[field_key] = graphene.Field.mounted(graphene.String())

    return schema_type


def extend_schema_type_computed_field(schema_type, model):
    """Extend schema_type object to had attribute and resolver around computed_fields.

    Each computed field will be defined as a first level attribute.

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model
        model (Model): Django model

    Returns:
        (DjangoObjectType): The extended schema_type object
    """

    computed_fields = ComputedField.objects.get_for_model(model, get_queryset=False)
    prefix = ""
    if settings.GRAPHQL_COMPUTED_FIELD_PREFIX and isinstance(settings.GRAPHQL_COMPUTED_FIELD_PREFIX, str):
        prefix = f"{settings.GRAPHQL_COMPUTED_FIELD_PREFIX}_"

    for field in computed_fields:
        field_name = f"{prefix}{field.key}"
        try:
            check_if_key_is_graphql_safe("Computed Field", field.key)
        except ValidationError:
            logger.warning(
                'Unable to add the computed field "%s" to %s because computed field key "%s" is not GraphQL safe',
                field,
                schema_type._meta.name,
                field_name,
            )
            continue

        resolver_name = f"resolve_{field_name}"

        if hasattr(schema_type, resolver_name):
            logger.warning(
                'Unable to add the computed field "%s" to %s because '
                'there is already an attribute mapped to the same name ("%s")',
                field,
                schema_type._meta.name,
                field_name,
            )
            continue

        setattr(
            schema_type,
            resolver_name,
            generate_computed_field_resolver(field.key, resolver_name),
        )

        schema_type._meta.fields[field_name] = graphene.Field.mounted(graphene.String())

    return schema_type


def extend_schema_type_tags(schema_type, model):
    """Extend schema_type object to had a resolver for tags.

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model
        model (Model): Django model

    Returns:
        (DjangoObjectType): The extended schema_type object
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
        (DjangoObjectType): The extended schema_type object
    """

    fields_name = [field.name for field in model._meta.get_fields()]
    if "local_config_context_data" not in fields_name:
        return schema_type

    def resolve_config_context(self, args):
        return self.get_config_context()

    schema_type._meta.fields["config_context"] = graphene.Field.mounted(generic.GenericScalar())
    setattr(schema_type, "resolve_config_context", resolve_config_context)

    return schema_type


def extend_schema_type_global_features(schema_type, model):
    """
    Extend schema_type object to have attributes and resolvers for global features (dynamic groups, etc.).
    """
    # associated_contacts and associated_object_metadata are handled elsewhere by extend_schema_type_filter()
    if getattr(model, "is_dynamic_group_associable_model", False):

        def resolve_dynamic_groups(self, args):
            return self.dynamic_groups

        setattr(schema_type, "resolve_dynamic_groups", resolve_dynamic_groups)
        schema_type._meta.fields["dynamic_groups"] = graphene.Field.mounted(graphene.List(DynamicGroupType))

    return schema_type


def extend_schema_type_relationships(schema_type, model):
    """
    Extend the schema type with attributes and resolvers for the relationships associated with this model.

    Args:
        schema_type (DjangoObjectType): GraphQL Object type for a given model
        model (Model): Django model
    """
    relationships_by_side = {
        "source": Relationship.objects.get_for_model_source(model, get_queryset=False),
        "destination": Relationship.objects.get_for_model_destination(model, get_queryset=False),
    }

    prefix = ""
    if settings.GRAPHQL_RELATIONSHIP_PREFIX and isinstance(settings.GRAPHQL_RELATIONSHIP_PREFIX, str):
        prefix = f"{settings.GRAPHQL_RELATIONSHIP_PREFIX}_"

    for side, relationships in relationships_by_side.items():
        for relationship in relationships:
            peer_side = RelationshipSideChoices.OPPOSITE[side]

            # Generate the name of the attribute and the name of the resolver based on the key of the relationship
            # and based on the prefix
            rel_name = f"{prefix}{relationship.key}"
            # Handle non-symmetric relationships where the model can be either source or destination
            if not relationship.symmetric and relationship.source_type == relationship.destination_type:
                rel_name = f"{rel_name}_{peer_side}"
            resolver_name = f"resolve_{rel_name}"

            if hasattr(schema_type, resolver_name):
                # If a symmetric relationship, and this is destination side, we already added source side, expected
                # Otherwise something is wrong and we should warn
                if side != "destination" or not relationship.symmetric:
                    logger.warning(
                        'Unable to add the custom relationship "%s" to %s '
                        'because there is already an attribute mapped to the same name ("%s")',
                        relationship,
                        schema_type._meta.name,
                        rel_name,
                    )
                continue

            # Identify which object needs to be on the other side of this relationship
            # and check the registry to see if it is available,
            peer_type = getattr(relationship, f"{peer_side}_type")
            peer_model = peer_type.model_class()
            if not peer_model:
                # Could happen if, for example, we have a leftover relationship defined for a model from a plugin
                # that is no longer installed/enabled
                logger.warning("Unable to find peer model %s to create GraphQL relationship", peer_type)
                continue
            type_identifier = f"{peer_model._meta.app_label}.{peer_model._meta.model_name}"
            rel_schema_type = registry["graphql_types"].get(type_identifier)

            if not rel_schema_type:
                logger.warning("Unable to identify the GraphQL Object Type for %s in the registry.", type_identifier)
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
                'Unable to register the schema single type "%s" in GraphQL, '
                'as there is already another type "%s" registered under this name',
                single_item_name,
                class_attrs[single_item_name]._type,
            )
            return True

        if list_name in class_attrs:
            logger.warning(
                'Unable to register the schema list type "%s" in GraphQL, '
                'as there is already another type "%s" registered under this name',
                list_name,
                class_attrs[list_name]._type,
            )
            return True

        return False

    logger.debug("Generating dynamic schemas for all models in the models_features graphql registry")
    #  - Ensure an attribute/schematype with the same name doesn't already exist
    registered_models = registry.get("feature_models", {}).get("graphql", [])
    for model in registered_models:
        type_identifier = model._meta.label_lower

        if type_identifier in registry["graphql_types"].keys():
            # Skip models that have been added statically
            continue

        schema_type = generate_schema_type(app_name=model._meta.app_label, model=model)
        registry["graphql_types"][type_identifier] = schema_type

    logger.debug("Adding plugins' statically defined graphql schema types")
    # After checking for conflict
    for schema_type in registry["plugin_graphql_types"]:
        model = schema_type._meta.model
        type_identifier = f"{model._meta.app_label}.{model._meta.model_name}"

        if type_identifier in registry["graphql_types"]:
            logger.warning(
                'Unable to load schema type for the model "%s" as there is already another type '
                "registered under this name. If you are seeing this message during plugin development, check to "
                "make sure that you aren't using @extras_features(\"graphql\") on the same model you're also "
                "defining a custom GraphQL type for.",
                type_identifier,
            )
        else:
            registry["graphql_types"][type_identifier] = schema_type

    logger.debug("Extending all registered schema types with dynamic attributes")

    # Precache all content-types as we'll need them for filtering and the like
    for content_type in ContentType.objects.all():
        ContentType.objects._add_to_cache(ContentType.objects.db, content_type)

    CustomField.objects.populate_list_caches()
    ComputedField.objects.populate_list_caches()
    Relationship.objects.populate_list_caches()

    for schema_type in registry["graphql_types"].values():
        if already_present(schema_type._meta.model):
            continue

        schema_type = extend_schema_type(schema_type)
        class_attrs.update(generate_attrs_for_schema_type(schema_type))

    QueryMixin = type("QueryMixin", (object,), class_attrs)
    logger.info("Generation of Nautobot GraphQL schema complete")
    return QueryMixin
