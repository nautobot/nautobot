import logging
import uuid

from django.core.exceptions import (
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ValidationError as DjangoValidationError,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import AutoField, ManyToManyField
from django.urls import NoReverseMatch
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field, PolymorphicProxySerializer as _PolymorphicProxySerializer
from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework.fields import CreateOnlyDefault
from rest_framework.serializers import SerializerMethodField
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.utils.field_mapping import get_nested_relation_kwargs

from nautobot.core.api.fields import ObjectTypeField
from nautobot.core.api.mixins import WritableSerializerMixin
from nautobot.core.api.utils import dict_to_filter_params, get_serializer_for_model
from nautobot.core.utils.deprecation import class_deprecated_in_favor_of
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.core.utils.requests import normalize_querydict
from nautobot.extras.api.relationships import RelationshipsDataField
from nautobot.extras.api.customfields import CustomFieldsDataField, CustomFieldDefaultValues
from nautobot.extras.choices import RelationshipSideChoices
from nautobot.extras.models import RelationshipAssociation, Tag

logger = logging.getLogger(__name__)


class OptInFieldsMixin:
    """
    A serializer mixin that takes an additional `opt_in_fields` argument that controls
    which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__pruned_fields = None

    @property
    def fields(self):
        """
        Removes all serializer fields specified in a serializers `opt_in_fields` list that aren't specified in the
        `include` query parameter.

        As an example, if the serializer specifies that `opt_in_fields = ["computed_fields"]`
        but `computed_fields` is not specified in the `?include` query parameter, `computed_fields` will be popped
        from the list of fields.
        """
        if self.__pruned_fields is None:
            fields = dict(super().fields)
            serializer_opt_in_fields = getattr(self.Meta, "opt_in_fields", None)

            if not serializer_opt_in_fields:
                # This serializer has no defined opt_in_fields, so we never need to go further than this
                self.__pruned_fields = fields
                return self.__pruned_fields

            if not hasattr(self, "_context"):
                # We are being called before a request cycle
                return fields

            try:
                request = self.context["request"]
            except KeyError:
                # No available request?
                return fields

            # opt-in fields only applies on GET requests, for other methods we support these fields regardless
            if request is not None and request.method != "GET":
                return fields

            # NOTE: drf test framework builds a request object where the query
            # parameters are found under the GET attribute.
            params = normalize_querydict(getattr(request, "query_params", getattr(request, "GET", None)))

            try:
                user_opt_in_fields = params.get("include", [])
            except AttributeError:
                # include parameter was not specified
                user_opt_in_fields = []

            # Drop any fields that are not specified in the users opt in fields
            for field in serializer_opt_in_fields:
                if field not in user_opt_in_fields:
                    fields.pop(field, None)

            self.__pruned_fields = fields

        return self.__pruned_fields


class NautobotPrimaryKeyRelatedField(WritableSerializerMixin, serializers.PrimaryKeyRelatedField):
    """DRF's built-in PrimaryKeyRelatedField combined with custom to_internal_value() function"""


class BaseModelSerializer(OptInFieldsMixin, serializers.ModelSerializer):
    """
    This base serializer implements common fields and logic for all ModelSerializers.

    Namely, it:

    - defines the `display` field which exposes a human friendly value for the given object.
    - ensures that `id` field is always present on the serializer as well
    - ensures that `created` and `last_updated` fields are always present if applicable to this model and serializer.
    """

    display = serializers.SerializerMethodField(read_only=True, help_text="Human friendly display value")
    url = serializers.HyperlinkedIdentityField(read_only=True, view_name="")
    serializer_related_field = NautobotPrimaryKeyRelatedField
    object_type = ObjectTypeField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If it is not a NestedSerializer, we should set the depth argument to whatever is in the request's context
        if "NautobotNestedSerializer" not in self.__class__.__name__:
            # We set our default depth value here to 1 because in OpenAPISchema
            # get_serializer_context() (where we get the depth from self.request.query_params) is not called
            # so in order to have enough information present in the OpenAPISchema, we set depth here to 1
            # RestAPI serializer is not affected by this because get_serializer_context() is always called
            # and depth is either passed into the request.query_params, or default to 0.
            self.Meta.depth = self.context.get("depth", 1)

    @extend_schema_field(serializers.CharField)
    def get_display(self, instance):
        """
        Return either the `display` property of the instance or `str(instance)`
        """
        return getattr(instance, "display", str(instance))

    def extend_field_names(self, fields, field_name, at_start=False, opt_in_only=False):
        """Prepend or append the given field_name to `fields` and optionally self.Meta.opt_in_fields as well."""
        if field_name not in fields:
            if at_start:
                fields.insert(0, field_name)
            else:
                fields.append(field_name)
        if opt_in_only:
            if not getattr(self.Meta, "opt_in_fields", None):
                self.Meta.opt_in_fields = [field_name]
            elif field_name not in self.Meta.opt_in_fields:
                self.Meta.opt_in_fields.append(field_name)
        return fields

    def eliminate_field_names(self, fields, field_name):
        """Eliminate non-user-facing field_name from `fields` e.g. `_custom_field_data`, `_name`"""
        if field_name not in fields:
            return fields
        fields.remove(field_name)
        return fields

    def get_field_names(self, declared_fields, info):
        """
        Override get_field_names() to ensure certain fields are present even when not explicitly stated in Meta.fields.

        DRF does not automatically add declared fields to `Meta.fields`, nor does it require that declared fields
        on a super class be included in `Meta.fields` to allow for a subclass to include only a subset of declared
        fields from the super. This means either we intercept and ensure the fields at this level, or
        enforce by convention that all consumers of BaseModelSerializer include each of these standard fields in their
        `Meta.fields` which would surely lead to errors of omission; therefore we have chosen the former approach.

        Adds "id" and "display" to the start of `fields` for all models; also appends "created" and "last_updated"
        to the end of `fields` if they are applicable to this model and this is not a Nested serializer.
        """
        fields = list(super().get_field_names(declared_fields, info))  # Meta.fields could be defined as a tuple
        self.extend_field_names(fields, "display", at_start=True)
        self.extend_field_names(fields, "id", at_start=True)
        self.eliminate_field_names(fields, "_custom_field_data")
        self.eliminate_field_names(fields, "_name")
        # Needed because we don't have a common base class for all nested serializers vs non-nested serializers
        if not self.__class__.__name__.startswith("Nested"):
            if hasattr(self.Meta.model, "created"):
                self.extend_field_names(fields, "created")
            if hasattr(self.Meta.model, "last_updated"):
                self.extend_field_names(fields, "last_updated")
        # append non-default model api fields to display in Nautobot API
        # e.g. for annotated fields `circuit_count`, `device_count` and etc.
        if getattr(self.Meta, "extra_fields", None):
            return fields + self.Meta.extra_fields
        # This is here for the PolymorphicProxySerializers which
        # are looking for an object_type field (originally on WritableNestedSerializer now BaseModelSerializer)
        if "object_type" not in fields:
            fields.append("object_type")
        return fields

    def build_field(self, field_name, info, model_class, nested_depth):
        """
        Return a two tuple of (cls, kwargs) to build a serializer field with.
        """
        from rest_framework.utils.model_meta import RelationInfo, _get_to_field

        # For tags field, DRF does not recognize the relationship between tags and the model itself (?)
        # so instead of calling build_nested_field() it will call build_property_field() which
        # makes the field impervious to the `?depth` parameter.
        # So we intercept it here to call build_nested_field()
        # which will make the tags field be rendered with TagSerializer() and respect the `depth` parameter.
        if field_name == "tags":
            if nested_depth > 0:
                relation_info = RelationInfo(
                    model_field=getattr(model_class, "tags"),
                    related_model=Tag,
                    to_many=True,
                    has_through_model=True,
                    to_field=_get_to_field(getattr(model_class, "tags")),
                    reverse=False,
                )
                return self.build_nested_field(field_name, relation_info, nested_depth)

        return super().build_field(field_name, info, model_class, nested_depth)

    def build_property_field(self, field_name, model_class):
        """
        Create a property field for model methods and properties.
        """
        if field_name == "tags":
            field_class = NautobotPrimaryKeyRelatedField
            field_kwargs = {
                "queryset": Tag.objects.filter(content_types=ContentType.objects.get_for_model(model_class)),
                "required": False,
            }

            return field_class, field_kwargs
        return super().build_property_field(field_name, model_class)

    def build_nested_field(self, field_name, relation_info, nested_depth):
        field = get_serializer_for_model(relation_info.related_model)

        class NautobotNestedSerializer(field):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                if hasattr(field.Meta, "fields"):
                    fields = field.Meta.fields
                if hasattr(field.Meta, "exclude"):
                    exclude = field.Meta.exclude

        # This is a very hacky way to avoid name collisions in OpenAPISchema Generations
        # The exact error output can be seen in this issue https://github.com/tfranzel/drf-spectacular/issues/90
        # Apparently drf-spectacular does not support the `?depth` argument that comes with DRF
        # So auto-generating NestedSerializers with the default class names that are the same when depth > 0
        # does not make our schema happy.
        NautobotNestedSerializer.__name__ = "NautobotNestedSerializer" + f"{uuid.uuid1()}"
        field_class = NautobotNestedSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)

        return field_class, field_kwargs


class TreeModelSerializerMixin(BaseModelSerializer):
    """Add a `tree_depth` field to model serializers based on django-tree-queries."""

    tree_depth = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_tree_depth(self, obj):
        """The `tree_depth` is not a database field, but an annotation automatically added by django-tree-queries."""
        return getattr(obj, "tree_depth", None)


class ValidatedModelSerializer(BaseModelSerializer):
    """
    Extends the built-in ModelSerializer to enforce calling full_clean() on a copy of the associated instance during
    validation. (DRF does not do this by default; see https://github.com/encode/django-rest-framework/issues/3144)
    """

    def validate(self, data):
        # Remove custom fields data and tags (if any) prior to model validation
        attrs = data.copy()
        attrs.pop("custom_fields", None)
        attrs.pop("relationships", None)
        attrs.pop("tags", None)

        # Skip ManyToManyFields
        for field in self.Meta.model._meta.get_fields():
            if isinstance(field, ManyToManyField):
                attrs.pop(field.name, None)

        # Run clean() on an instance of the model
        if self.instance is None:
            instance = self.Meta.model(**attrs)
        else:
            instance = self.instance
            for k, v in attrs.items():
                setattr(instance, k, v)
        instance.full_clean()
        return data


class WritableNestedSerializer(BaseModelSerializer):
    """
    Returns a nested representation of an object on read, but accepts either the nested representation or the
    primary key value on write operations.

    Note that subclasses will always have a read-only `object_type` field, which represents the content-type of this
    serializer's associated model (e.g. "dcim.device"). This is required as the OpenAPI schema, using the
    PolymorphicProxySerializer class defined below, relies upon this field as a way to identify to the client
    which of several possible nested serializers are in use for a given attribute.
    """

    object_type = ObjectTypeField()

    def get_field_names(self, declared_fields, info):
        """Ensure that the "object_type" field is always included in self.fields."""
        fields = list(super().get_field_names(declared_fields, info))
        if "object_type" not in fields:
            fields.append("object_type")
        return fields

    def get_queryset(self):
        return self.Meta.model.objects

    def to_internal_value(self, data):
        if data is None:
            return None

        # Dictionary of related object attributes
        if isinstance(data, dict):
            params = dict_to_filter_params(data)

            # Make output from a WritableNestedSerializer "round-trip" capable by automatically stripping from the
            # data any serializer fields that do not correspond to a specific model field
            for field_name, field_instance in self.fields.items():
                if field_name in params and field_instance.source == "*":
                    logger.debug("Discarding non-database field %s", field_name)
                    del params[field_name]

            queryset = self.get_queryset()
            try:
                return queryset.get(**params)
            except ObjectDoesNotExist:
                raise ValidationError(f"Related object not found using the provided attributes: {params}")
            except MultipleObjectsReturned:
                raise ValidationError(f"Multiple objects match the provided attributes: {params}")
            except FieldError as e:
                raise ValidationError(e)

        queryset = self.get_queryset()
        pk = None

        if isinstance(self.Meta.model._meta.pk, AutoField):
            # PK is an int for this model. This is usually the User model
            try:
                pk = int(data)
            except (TypeError, ValueError):
                raise ValidationError(
                    "Related objects must be referenced by ID or by dictionary of attributes. Received an "
                    f"unrecognized value: {data}"
                )

        else:
            # We assume a type of UUIDField for all other models

            # PK of related object
            try:
                # Ensure the pk is a valid UUID
                pk = uuid.UUID(str(data))
            except (TypeError, ValueError):
                raise ValidationError(
                    "Related objects must be referenced by ID or by dictionary of attributes. Received an "
                    f"unrecognized value: {data}"
                )

        try:
            return queryset.get(pk=pk)
        except ObjectDoesNotExist:
            raise ValidationError(f"Related object not found using the provided ID: {pk}")


class PolymorphicProxySerializer(_PolymorphicProxySerializer):
    """
    Like the base class from drf-spectacular, this is a pseudo-serializer used to represent multiple possibilities.

    Use with `@extend_schema_field` on the method associated with a SerializerMethodField that can return one of
    several different possible nested serializers. For example:

        @extend_schema_field(
            PolymorphicProxySerializer(
                component_name="some_field",   # must be the same as the serializer field being decorated
                serializers=[
                    NestedSomeModelSerializer,
                    NestedAnotherModelSerializer,
                ],
                allow_null=True,  # optional!
            )
        )
        def get_some_field(self, obj):
            ...

    This enhances the base class with:

    1. Supports `allow_null` as an init parameter, similar to real serializers.
    """

    def __init__(self, *args, allow_null=False, **kwargs):
        """Intercept the `allow_null` parameter that's not understood by the base class."""
        super().__init__(*args, **kwargs)
        self.allow_null = allow_null


class BulkOperationSerializer(serializers.Serializer):
    """
    Representation of bulk-DELETE request for most models; also used to validate required ID field for bulk-PATCH/PUT.
    """

    id = serializers.UUIDField()


class BulkOperationIntegerIDSerializer(serializers.Serializer):
    """As BulkOperationSerializer, but for models such as users.Group that have an integer ID field."""

    id = serializers.IntegerField()


#
# GraphQL, used by the openapi doc, not by the view
#


class GraphQLAPISerializer(serializers.Serializer):
    query = serializers.CharField(required=True, help_text="GraphQL query")
    variables = serializers.JSONField(required=False, help_text="Variables in JSON Format")


class CustomFieldModelSerializerMixin(ValidatedModelSerializer):
    """
    Extends ModelSerializer to render any CustomFields and their values associated with an object.
    """

    computed_fields = SerializerMethodField(read_only=True)
    custom_fields = CustomFieldsDataField(
        source="_custom_field_data",
        default=CreateOnlyDefault(CustomFieldDefaultValues()),
    )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_computed_fields(self, obj):
        return obj.get_computed_fields()

    def get_field_names(self, declared_fields, info):
        """Ensure that "custom_fields" and "computed_fields" are always included appropriately."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "custom_fields")
        self.extend_field_names(fields, "computed_fields", opt_in_only=True)
        return fields


# TODO: remove in 2.2
@class_deprecated_in_favor_of(CustomFieldModelSerializerMixin)
class CustomFieldModelSerializer(CustomFieldModelSerializerMixin):
    pass


class RelationshipModelSerializerMixin(ValidatedModelSerializer):
    """Extend ValidatedModelSerializer with a `relationships` field."""

    # TODO # 3024 need to change this as well to show just pks in depth=0
    relationships = RelationshipsDataField(required=False, source="*")

    def create(self, validated_data):
        relationships_data = validated_data.pop("relationships", {})
        required_relationships_errors = self.Meta().model.required_related_objects_errors(
            output_for="api", initial_data=relationships_data
        )
        if required_relationships_errors:
            raise ValidationError({"relationships": required_relationships_errors})
        instance = super().create(validated_data)
        if relationships_data:
            try:
                self._save_relationships(instance, relationships_data)
            except DjangoValidationError as error:
                raise ValidationError(str(error))
        return instance

    def update(self, instance, validated_data):
        relationships_key_specified = "relationships" in self.context["request"].data
        relationships_data = validated_data.pop("relationships", {})
        required_relationships_errors = self.Meta().model.required_related_objects_errors(
            output_for="api",
            initial_data=relationships_data,
            relationships_key_specified=relationships_key_specified,
            instance=instance,
        )
        if required_relationships_errors:
            raise ValidationError({"relationships": required_relationships_errors})

        instance = super().update(instance, validated_data)
        if relationships_data:
            self._save_relationships(instance, relationships_data)
        return instance

    def _save_relationships(self, instance, relationships):
        """Create/update RelationshipAssociations corresponding to a model instance."""
        # relationships has already passed RelationshipsDataField.to_internal_value(), so we can skip some try/excepts
        logger.debug("_save_relationships: %s : %s", instance, relationships)
        for relationship, relationship_data in relationships.items():
            for other_side in ["source", "destination", "peer"]:
                if other_side not in relationship_data:
                    continue

                other_type = getattr(relationship, f"{other_side}_type")
                other_side_model = other_type.model_class()
                # other_side_serializer = get_serializer_for_model(other_side_model)
                # serializer_instance = other_side_serializer(context={"request": self.context.get("request")})

                expected_objects_data = relationship_data[other_side]
                expected_objects = [
                    other_side_model.objects.get(**object_data) for object_data in expected_objects_data
                ]

                this_side = RelationshipSideChoices.OPPOSITE[other_side]

                if this_side != RelationshipSideChoices.SIDE_PEER:
                    existing_associations = relationship.relationship_associations.filter(
                        **{f"{this_side}_id": instance.pk}
                    )
                    existing_objects = [assoc.get_peer(instance) for assoc in existing_associations]
                else:
                    existing_associations_1 = relationship.relationship_associations.filter(source_id=instance.pk)
                    existing_objects_1 = [assoc.get_peer(instance) for assoc in existing_associations_1]
                    existing_associations_2 = relationship.relationship_associations.filter(destination_id=instance.pk)
                    existing_objects_2 = [assoc.get_peer(instance) for assoc in existing_associations_2]
                    existing_associations = list(existing_associations_1) + list(existing_associations_2)
                    existing_objects = existing_objects_1 + existing_objects_2

                add_objects = []
                remove_assocs = []

                for obj, assoc in zip(existing_objects, existing_associations):
                    if obj not in expected_objects:
                        remove_assocs.append(assoc)
                for obj in expected_objects:
                    if obj not in existing_objects:
                        add_objects.append(obj)

                for add_object in add_objects:
                    if "request" in self.context and not self.context["request"].user.has_perm(
                        "extras.add_relationshipassociation"
                    ):
                        raise PermissionDenied("This user does not have permission to create RelationshipAssociations.")
                    if other_side != RelationshipSideChoices.SIDE_SOURCE:
                        assoc = RelationshipAssociation(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            source_id=instance.id,
                            destination_type=relationship.destination_type,
                            destination_id=add_object.id,
                        )
                    else:
                        assoc = RelationshipAssociation(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            source_id=add_object.id,
                            destination_type=relationship.destination_type,
                            destination_id=instance.id,
                        )
                    assoc.validated_save()  # enforce relationship filter logic, etc.
                    logger.debug("Created %s", assoc)

                for remove_assoc in remove_assocs:
                    if "request" in self.context and not self.context["request"].user.has_perm(
                        "extras.delete_relationshipassociation"
                    ):
                        raise PermissionDenied("This user does not have permission to delete RelationshipAssociations.")
                    logger.debug("Deleting %s", remove_assoc)
                    remove_assoc.delete()

    def get_field_names(self, declared_fields, info):
        """Ensure that "relationships" is always included as an opt-in field."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "relationships", opt_in_only=True)
        return fields


class NotesSerializerMixin(BaseModelSerializer):
    """Extend Serializer with a `notes` field."""

    notes_url = serializers.SerializerMethodField()

    def get_field_names(self, declared_fields, info):
        """Ensure that fields includes "notes_url" field if applicable."""
        fields = list(super().get_field_names(declared_fields, info))
        if hasattr(self.Meta.model, "notes"):
            self.extend_field_names(fields, "notes_url")
        return fields

    @extend_schema_field(serializers.URLField())
    def get_notes_url(self, instance):
        try:
            notes_url = get_route_for_model(instance, "notes", api=True)
            return reverse(notes_url, args=[instance.id], request=self.context["request"])
        except NoReverseMatch:
            model_name = type(instance).__name__
            logger.warning(
                (
                    f"Notes feature is not available for model {model_name}. "
                    "Please make sure to: "
                    f"1. Include NotesMixin from nautobot.extras.model.mixins in the {model_name} class definition "
                    f"2. Include NotesViewSetMixin from nautobot.extras.api.mixins in the {model_name}ViewSet "
                    "before including NotesSerializerMixin in the model serializer"
                )
            )

            return None


class NautobotModelSerializer(
    RelationshipModelSerializerMixin, CustomFieldModelSerializerMixin, NotesSerializerMixin, ValidatedModelSerializer
):
    """Base class to use for serializers based on OrganizationalModel or PrimaryModel.

    Can also be used for models derived from BaseModel, so long as they support custom fields and relationships.
    """
