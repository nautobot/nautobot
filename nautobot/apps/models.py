"""Data model classes and utilities for app implementation."""

from nautobot.core.models import BaseModel
from nautobot.core.models.fields import (
    AttributeSetter,
    AutoSlugField,
    ColorField,
    ForeignKeyLimitedByContentTypes,
    ForeignKeyWithAutoRelatedName,
    JSONArrayField,
    mac_unix_expanded_uppercase,
    MACAddressCharField,
    NaturalOrderingField,
    slugify_dashes_to_underscores,
    slugify_dots_to_dashes,
    TagsField,
)
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.models.managers import BaseManager, TagsManager
from nautobot.core.models.name_color_content_types import ContentTypeRelatedQuerySet, NameColorContentTypesModel
from nautobot.core.models.ordering import naturalize, naturalize_interface
from nautobot.core.models.query_functions import CollateAsChar, EmptyGroupByJSONBAgg, JSONBAgg
from nautobot.core.models.querysets import CompositeKeyQuerySetMixin, count_related, RestrictedQuerySet
from nautobot.core.models.tree_queries import TreeManager, TreeModel, TreeQuerySet
from nautobot.core.models.utils import (
    array_to_string,
    construct_composite_key,
    construct_natural_slug,
    deconstruct_composite_key,
    find_models_with_matching_fields,
    get_all_concrete_models,
    is_taggable,
    pretty_print_query,
    serialize_object,
    serialize_object_v2,
)
from nautobot.core.models.validators import EnhancedURLValidator, ExclusionValidator, ValidRegexValidator
from nautobot.extras.models import (
    ChangeLoggedModel,
    ConfigContextModel,
    CustomFieldModel,
    RelationshipModel,
    StatusField,
    StatusModel,
)
from nautobot.extras.models.mixins import DynamicGroupMixin, NotesMixin
from nautobot.extras.models.models import ConfigContextSchemaValidationMixin
from nautobot.extras.plugins import CustomValidator
from nautobot.extras.utils import extras_features
from nautobot.ipam.fields import VarbinaryIPField
from nautobot.ipam.models import get_default_namespace, get_default_namespace_pk

__all__ = (
    "array_to_string",
    "AttributeSetter",
    "AutoSlugField",
    "BaseManager",
    "BaseModel",
    "ChangeLoggedModel",
    "CollateAsChar",
    "ColorField",
    "CompositeKeyQuerySetMixin",
    "ConfigContextModel",
    "ConfigContextSchemaValidationMixin",
    "construct_composite_key",
    "construct_natural_slug",
    "ContentTypeRelatedQuerySet",
    "count_related",
    "CustomFieldModel",
    "CustomValidator",
    "deconstruct_composite_key",
    "DynamicGroupMixin",
    "EmptyGroupByJSONBAgg",
    "EnhancedURLValidator",
    "ExclusionValidator",
    "extras_features",
    "find_models_with_matching_fields",
    "ForeignKeyLimitedByContentTypes",
    "ForeignKeyWithAutoRelatedName",
    "get_all_concrete_models",
    "get_default_namespace",
    "get_default_namespace_pk",
    "is_taggable",
    "JSONArrayField",
    "JSONBAgg",
    "mac_unix_expanded_uppercase",
    "MACAddressCharField",
    "NameColorContentTypesModel",
    "naturalize_interface",
    "naturalize",
    "NaturalOrderingField",
    "NotesMixin",
    "OrganizationalModel",
    "pretty_print_query",
    "PrimaryModel",
    "RelationshipModel",
    "RestrictedQuerySet",
    "serialize_object_v2",
    "serialize_object",
    "slugify_dashes_to_underscores",
    "slugify_dots_to_dashes",
    "StatusField",
    "StatusModel",
    "TagsField",
    "TagsManager",
    "TreeManager",
    "TreeModel",
    "TreeQuerySet",
    "ValidRegexValidator",
    "VarbinaryIPField",
)
