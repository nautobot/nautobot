import contextlib
import logging
import uuid

from django.contrib.contenttypes.fields import GenericRel
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (
    FieldDoesNotExist,
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ValidationError as DjangoValidationError,
)
from django.db import models
from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from django.db.models.functions import Cast
from django.urls import NoReverseMatch
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field, PolymorphicProxySerializer as _PolymorphicProxySerializer
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.fields import CreateOnlyDefault
from rest_framework.reverse import reverse
from rest_framework.serializers import SerializerMethodField
from rest_framework.utils.model_meta import _get_to_field, RelationInfo

from nautobot.core import constants
from nautobot.core.api.fields import LaxURLField, NautobotHyperlinkedRelatedField, ObjectTypeField
from nautobot.core.api.utils import (
    dict_to_filter_params,
    nested_serializer_factory,
)
from nautobot.core.models.fields import LaxURLField as LaxURLModelField
from nautobot.core.models.managers import TagsManager
from nautobot.core.models.utils import construct_composite_key, construct_natural_slug
from nautobot.core.settings_funcs import is_truthy
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.core.utils.requests import normalize_querydict
from nautobot.extras.api.customfields import CustomFieldDefaultValues, CustomFieldsDataField
from nautobot.extras.api.relationships import RelationshipsDataField
from nautobot.extras.choices import RelationshipSideChoices
from nautobot.extras.models import RelationshipAssociation, Tag
from nautobot.ipam.fields import VarbinaryIPField

logger = logging.getLogger(__name__)


class OptInFieldsMixin:
    """
    Serializer mixin that adjusts its fields based on the `include` and `exclude_m2m` query parameters in a request.

    The serializer's `Meta.opt_in_fields` controls which fields are influenced by `include`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__pruned_fields = None

    @property
    def fields(self):
        """
        Dynamically adjust the dictionary of fields attributed to this serializer instance.

        - Removes all serializer fields specified in `Meta.opt_in_fields` list that aren't specified in the
          `include` query parameter. (applies to GET requests only)
        - If the `exclude_m2m` query parameter is truthy, remove all many-to-many serializer fields for performance.

        As an example, if the serializer specifies that `opt_in_fields = ["computed_fields"]`
        but `computed_fields` is not specified in the `?include` query parameter, `computed_fields` will be popped
        from the list of fields.
        """
        if self.__pruned_fields is None:
            fields = dict(super().fields)
            serializer_opt_in_fields = getattr(self.Meta, "opt_in_fields", [])

            if not hasattr(self, "_context"):
                # We are being called before a request cycle
                return fields

            try:
                request = self.context["request"]
            except KeyError:
                # No available request?
                return fields

            # NOTE: drf test framework builds a request object where the query
            # parameters are found under the GET attribute.
            params = normalize_querydict(getattr(request, "query_params", getattr(request, "GET", None)))

            # opt-in fields only applies on GET requests, for other methods we support these fields regardless
            if request is None or request.method == "GET":
                try:
                    user_opt_in_fields = params.get("include", [])
                except AttributeError:
                    # include parameter was not specified
                    user_opt_in_fields = []

                # Drop any fields that are not specified in the users opt in fields
                for field in serializer_opt_in_fields:
                    if field not in user_opt_in_fields:
                        fields.pop(field, None)

            # If exclude_m2m is present and truthy, mark any many-to-many fields as write-only so they
            # don't get included in the response.
            if is_truthy(params.get("exclude_m2m", "false")):
                for field_instance in fields.values():
                    if isinstance(field_instance, (serializers.ManyRelatedField, serializers.ListSerializer)):
                        field_instance.write_only = True

            self.__pruned_fields = fields

        return self.__pruned_fields


class BaseModelSerializer(OptInFieldsMixin, serializers.HyperlinkedModelSerializer):
    """
    This base serializer implements common fields and logic for all ModelSerializers.

    Namely, it:

    - defines the `display` field which exposes a human friendly value for the given object.
    - ensures that `id` field is always present on the serializer as well.
    - ensures that `created` and `last_updated` fields are always present if applicable to this model and serializer.
    - ensures that `object_type` field is always present on the serializer which represents the content-type of this
      serializer's associated model (e.g. "dcim.device"). This is required as the OpenAPI schema, using the
      PolymorphicProxySerializer class defined below, relies upon this field as a way to identify to the client
      which of several possible serializers are in use for a given attribute.
    - supports `?depth` query parameter. It is passed in as `nested_depth` to the `build_nested_field()` function
      to enable the dynamic generation of nested serializers.
    """

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        LaxURLModelField: LaxURLField,
    }

    serializer_related_field = NautobotHyperlinkedRelatedField

    id = serializers.UUIDField(read_only=False, default=serializers.CreateOnlyDefault(uuid.uuid4))
    display = serializers.SerializerMethodField(read_only=True, help_text="Human friendly display value")
    object_type = ObjectTypeField()
    # composite_key = serializers.SerializerMethodField()  # TODO: Revisit if we reintroduce composite keys
    natural_keys_values = None
    natural_slug = serializers.SerializerMethodField()

    def __init__(self, *args, force_csv=False, **kwargs):
        """
        Instantiate a BaseModelSerializer.

        The force_csv kwarg allows you to force _is_csv_request() to evaluate True without passing a Request object,
        which is necessary to be able to export appropriately structured CSV from a Job that doesn't have a Request.
        """
        self._force_csv = force_csv

        super().__init__(*args, **kwargs)
        # If it is not a Nested Serializer, we should set the depth argument to whatever is in the request's context
        if not self.is_nested:
            self.Meta.depth = self.context.get("depth", 0)

        # Check if the request is related to CSV export;
        if self._is_csv_request() and self.instance:
            # Retrieve the natural key values of related fields in an optimized way.
            all_related_fields_natural_key_lookups = self._get_related_fields_natural_key_field_lookups()
            case_query = self._build_query_case_for_natural_key_field_lookup(all_related_fields_natural_key_lookups)
            if isinstance(self.instance, models.QuerySet):
                queryset = self.instance
            else:
                # We would only need to run one additional query, making this a more efficient method of
                # obtaining all the natural key values for this instance;
                queryset = self.Meta.model.objects.filter(pk=self.instance.pk)
            self.natural_keys_values = queryset.annotate(**case_query).values(
                *all_related_fields_natural_key_lookups, "pk"
            )

    def _get_lookup_field_name_and_output_field(self, lookup_field):
        """Get lookup field name and its corresponding output_field.

        Used in building this lookup Case in `_build_query_case_for_natural_key_field_lookup`.

        Example:
            >>> self._get_lookup_field_name_and_output_field("device__location__name")
            ("device__location", CharField)
            >>> self._get_lookup_field_name_and_output_field("ipaddress__parent__network")
            ("ipaddress__parent", VarbinaryIPField)
        """
        *field_names, lookup = lookup_field.split("__")
        model = self.Meta.model
        for field_component in field_names:
            model = model._meta.get_field(field_component).remote_field.model

        lookup = "id" if lookup == "pk" else lookup
        field = model._meta.get_field(lookup)
        # VarbinaryIPField needs to be handled specially in `_build_query_case_for_natural_key_field_lookup`
        output_field = field.__class__ if field.__class__ is VarbinaryIPField else models.CharField

        field_name = "__".join(field_names)
        return field_name, output_field

    def _build_query_case_for_natural_key_field_lookup(self, lookups):
        """
        Build a query using Case expressions to handle natural key field instances that do not exist.

        This function constructs a database query with Case expressions to handle natural key lookup fields
        that may have missing instances. In cases where the natural key field instance does not exist
        (i.e., is None), this function replaces it with the value 'NoObject'. This is particularly
        useful for CSV Export processes, as it allows fields with missing instances to be safely ignored.
        Such handling is essential for CSV Import processes, as attempting to import missing instances can
        lead to 'Object Not Found' errors, potentially causing the import to fail.

        Example:
            Consider a Device model with a related field 'tenant' and a 'name' attribute. In this case, the
            function can be used as follows:

            Device.objects.annotate(
                tenant__name=Case(
                    When(tenant__isnull=False, then=F("tenant__name")),
                    default="NoObject"
                )
            ).values("tenant__name")

        Explanation:
            - If `device.tenant` is None, the 'tenant__name' field is set to "NoObject".
            - If `device.tenant` is not None, the 'tenant__name' field is set to the actual tenant name.

        Args:
            lookups: List of natural key lookups
        """
        case_query = {}
        for lookup_field in lookups:
            field_name, output_field = self._get_lookup_field_name_and_output_field(lookup_field)

            # Since VarbinaryIPField cant be cast into CharField we would have to set the output_field as
            # `VarbinaryIPField`
            when_case = {
                f"{field_name}__isnull": False,
                "then": models.F(lookup_field)
                if output_field == VarbinaryIPField
                else Cast(models.F(lookup_field), models.CharField()),
            }
            case_query[lookup_field] = models.Case(
                models.When(**when_case),
                default=models.Value(constants.CSV_NO_OBJECT),
                output_field=output_field(),
            )
        return case_query

    def _get_related_fields_natural_key_field_lookups(self):
        """Retrieve a list of field lookups for natural key fields of related models.

        This method iterates through the related fields of the Serializer model,
        retrieves the natural_key_field_lookups for each related model, and prepends the field name
        to create a list of field lookups.

        Examples:
            >>> # Example usage on Device
            >>> self._get_related_fields_natural_key_field_lookups()
            [
                "tenant__name",
                "status__name",
                "role__name",
                "location__name",
                "location__parent__name",
                "location__parent__parent__name"
                ...
            ]

        """
        model = self.Meta.model
        field_lookups = []
        # NOTE: M2M and One2M fields field are ignored in csv export
        fields = [
            field
            for field in model._meta.get_fields()
            if field.is_relation
            and not field.many_to_many
            and not field.one_to_many
            # Ignore GenericRel since its `fk` and `content_type` would be used.
            and not isinstance(field, GenericRel)
        ]
        # Get each related field model's natural_key_fields and prepend field name
        for field in fields:
            # ContentType and Group are not Nautobot Model hence do not have the `natural_key_field_lookups` attr.
            # fallback to using default behavior for these fields
            with contextlib.suppress(AttributeError):
                field_lookups.extend(
                    f"{field.name}__{lookup}" for lookup in field.related_model.csv_natural_key_field_lookups()
                )
        return field_lookups

    def _is_csv_request(self):
        """Return True if this a CSV export request"""
        if self._force_csv:
            return True
        request = self.context.get("request")
        return hasattr(request, "accepted_media_type") and "text/csv" in request.accepted_media_type

    @property
    def is_nested(self):
        """Return whether this is a nested serializer."""
        return getattr(self.Meta, "is_nested", False)

    @extend_schema_field(serializers.CharField)
    def get_display(self, instance):
        """
        Return either the `display` property of the instance or `str(instance)`
        """
        return getattr(instance, "display", str(instance))

    # TODO(jathan): Rip out composite key after natural key fields for import/export work has been
    # completed (See: https://github.com/nautobot/nautobot/issues/4367)
    @extend_schema_field(
        {
            "type": "string",
            "example": constants.COMPOSITE_KEY_SEPARATOR.join(["attribute1", "attribute2"]),
        }
    )
    def get_composite_key(self, instance):
        try:
            return getattr(instance, "composite_key", construct_composite_key(instance.natural_key()))
        except (AttributeError, NotImplementedError):
            return "unknown"

    @extend_schema_field(
        {
            "type": "string",
            "example": constants.NATURAL_SLUG_SEPARATOR.join(["attribute1", "attribute2"]),
        }
    )
    def get_natural_slug(self, instance):
        try:
            return getattr(instance, "natural_slug", construct_natural_slug(instance.natural_key(), pk=instance.pk))
        except (AttributeError, NotImplementedError):
            return "unknown"

    def extend_field_names(self, fields, field_name, at_start=False, opt_in_only=False):
        """Prepend or append the given field_name to `fields` and optionally self.Meta.opt_in_fields as well."""
        if field_name in fields:
            fields.remove(field_name)
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

    def get_field_names(self, declared_fields, info):
        """
        Override get_field_names() to add some custom logic.

        Assuming that we follow the pattern where `fields = "__all__" for the vast majority of serializers in Nautobot,
        we do not strictly need to use this method to protect against inadvertently omitting standard fields
        like `display`, `created`, and `last_updated`. However, we continue to do as a bit of redundant safety.

        The other purpose of this method now is to manipulate the set of fields that "__all__" actually means as a
        way of *excluding* fields that we *don't* want to include by default for performance or data exposure reasons.
        """
        fields = list(super().get_field_names(declared_fields, info))  # Meta.fields could be defined as a tuple

        # Add initial fields in "reverse" order since they're each inserted at the start of the list.
        self.extend_field_names(fields, "display", at_start=True)
        self.extend_field_names(fields, "object_type", at_start=True)
        # Since we use HyperlinkedModelSerializer as our base class, "url" is auto-included by "__all__" but "id" isn't.
        self.extend_field_names(fields, "id", at_start=True)

        # Move these fields to the end
        fields_to_include = ["created", "last_updated"]
        for field in fields_to_include:
            if hasattr(self.Meta.model, field):
                self.extend_field_names(fields, field)

        def filter_field(field):
            # Eliminate all field names that start with "_" as those fields are not user-facing
            if field.startswith("_"):
                return False
            # These are expensive to look up, so we have decided not to include them on nested serializers
            if self.is_nested and isinstance(getattr(self.Meta.model, field, None), ManyToManyDescriptor):
                return False

            # Ignore M2M fields
            with contextlib.suppress(FieldDoesNotExist):
                if self._is_csv_request():
                    field = self.Meta.model._meta.get_field(field)
                    # ContentType is ManyToMany Field that is specially handled, Hence it can be exported/imported
                    if field.many_to_many and field.related_model is not ContentType:
                        return False
            return True

        fields = [field for field in fields if filter_field(field)]
        return fields

    def build_field(self, field_name, info, model_class, nested_depth):
        """
        Return a two tuple of (cls, kwargs) to build a serializer field with.
        """
        request = self.context.get("request")
        # Make sure that PATCH/POST/PUT method response serializers are consistent
        # with depth of 0
        if request is not None and request.method != "GET":
            nested_depth = 0
        # For tags field, DRF does not recognize the relationship between tags and the model itself (?)
        # so instead of calling build_nested_field() it will call build_property_field() which
        # makes the field impervious to the `?depth` parameter.
        # So we intercept it here to call build_nested_field()
        # which will make the tags field be rendered with TagSerializer() and respect the `depth` parameter.
        if isinstance(getattr(model_class, field_name, None), TagsManager) and nested_depth > 0:
            tags_field = getattr(model_class, field_name)
            relation_info = RelationInfo(
                model_field=tags_field,
                related_model=Tag,
                to_many=True,
                has_through_model=True,
                to_field=_get_to_field(tags_field),
                reverse=False,
            )
            return self.build_nested_field(field_name, relation_info, nested_depth)

        return super().build_field(field_name, info, model_class, nested_depth)

    def _get_natural_key_lookups_value_for_field(self, field_name, natural_key_field_instance):
        """Extract natural key field lookups for a specific field name.

        Args:
            field_name (str): The field name to extract lookups for.
            natural_key_field_instance (dict): The dict containing natural key field values.

        Example:
            >>> natural_key_field_instance = Device.objects.values("tenant__name", "location__name", "location__parent__name", ...)
            >>> _get_natural_key_lookups_value_for_field("location", natural_key_field_instance)
            {
                "location__name": "Sample Location",
                "location__parent__name": "Sample Location Parent Name",
                "location__parent__parent__name": "NoObject"
                ...
            }

        """
        data = {}
        for key, value in natural_key_field_instance.items():
            if key.startswith(f"{field_name}__"):
                if isinstance(value, uuid.UUID):
                    data[key] = str(value)
                elif value == constants.VARBINARY_IP_FIELD_REPR_OF_CSV_NO_OBJECT:
                    data[key] = constants.CSV_NO_OBJECT
                elif value == "":
                    data[key] = value
                elif not value:
                    data[key] = constants.CSV_NULL_TYPE
                else:
                    data[key] = value
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        altered_data = {}

        if self._is_csv_request() and self.natural_keys_values is not None:
            if natural_key_field_instance := [item for item in self.natural_keys_values if item["pk"] == instance.pk]:
                cleaned_natural_key_field_instance = natural_key_field_instance[0]
                for key, value in data.items():
                    # FK field with natural_field_lookups
                    if natural_key_field_lookups_for_field := self._get_natural_key_lookups_value_for_field(
                        key, cleaned_natural_key_field_instance
                    ):
                        altered_data.update(natural_key_field_lookups_for_field)
                    else:
                        # Not FK field
                        altered_data[key] = constants.CSV_NULL_TYPE if value is None else value
        else:
            altered_data = data

        return altered_data

    def build_relational_field(self, field_name, relation_info):
        """Override DRF's default relational-field construction to be app-aware."""
        field_class, field_kwargs = super().build_relational_field(field_name, relation_info)
        if "view_name" in field_kwargs:
            field_kwargs["view_name"] = get_route_for_model(relation_info.related_model, "detail", api=True)
        return field_class, field_kwargs

    def build_property_field(self, field_name, model_class):
        """
        Create a property field for model methods and properties.
        """
        if isinstance(getattr(model_class, field_name, None), TagsManager):
            field_class = NautobotHyperlinkedRelatedField
            field_kwargs = {
                "queryset": Tag.objects.get_for_model(model_class),
                "many": True,
                "required": False,
            }

            return field_class, field_kwargs
        return super().build_property_field(field_name, model_class)

    def build_nested_field(self, field_name, relation_info, nested_depth):
        return nested_serializer_factory(relation_info, nested_depth)

    def build_url_field(self, field_name, model_class):
        """Override DRF's default 'url' field construction to be app-aware."""
        field_class, field_kwargs = super().build_url_field(field_name, model_class)
        if "view_name" in field_kwargs:
            field_kwargs["view_name"] = get_route_for_model(model_class, "detail", api=True)
        return field_class, field_kwargs


class TreeModelSerializerMixin(BaseModelSerializer):
    """Add a `tree_depth` field to non-nested model serializers based on django-tree-queries."""

    tree_depth = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_tree_depth(self, obj):
        """The `tree_depth` is not a database field, but an annotation automatically added by django-tree-queries."""
        return getattr(obj, "tree_depth", None)

    def get_field_names(self, declared_fields, info):
        """Ensure that "tree_depth" is included on root serializers only, as nested objects are not annotated."""
        fields = list(super().get_field_names(declared_fields, info))
        if self.is_nested and "tree_depth" in fields:
            fields.remove("tree_depth")
        return fields


class ValidatedModelSerializer(BaseModelSerializer):
    """
    Extends the built-in ModelSerializer to enforce calling full_clean() on a copy of the associated instance during
    validation. (DRF does not do this by default; see https://github.com/encode/django-rest-framework/issues/3144)
    """

    def validate(self, attrs):
        # Remove custom fields data and tags (if any) prior to model validation
        local_attrs = attrs.copy()
        local_attrs.pop("custom_fields", None)
        local_attrs.pop("relationships", None)
        local_attrs.pop("tags", None)

        # Skip ManyToManyFields
        for field in self.Meta.model._meta.get_fields():
            if isinstance(field, models.ManyToManyField):
                local_attrs.pop(field.name, None)

        # Run clean() on an instance of the model
        if self.instance is None:
            instance = self.Meta.model(**local_attrs)
        else:
            instance = self.instance
            for k, v in local_attrs.items():
                setattr(instance, k, v)
        instance.full_clean()
        return attrs


class WritableNestedSerializer(BaseModelSerializer):
    """
    Returns a nested representation of an object on read, but accepts either the nested representation or the
    primary key value on write operations.

    Note that subclasses will always have a read-only `object_type` field, which represents the content-type of this
    serializer's associated model (e.g. "dcim.device"). This is required as the OpenAPI schema, using the
    PolymorphicProxySerializer class defined below, relies upon this field as a way to identify to the client
    which of several possible nested serializers are in use for a given attribute.
    """

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

        if isinstance(self.Meta.model._meta.pk, models.AutoField):
            # PK is an int for this model. This is usually the Group or Content-Type model
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
        """Ensure that "custom_fields" and "computed_fields" are included appropriately."""
        fields = list(super().get_field_names(declared_fields, info))
        # Ensure that custom_fields field appears at the end, not the start, of the fields
        self.extend_field_names(fields, "custom_fields")
        if not self.is_nested:
            # Only include computed_fields as opt-in.
            self.extend_field_names(fields, "computed_fields", opt_in_only=True)
        else:
            # As computed fields are expensive, do not include them in nested serializers even if opted-in at the root
            if "computed_fields" in fields:
                fields.remove("computed_fields")
        return fields


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
                raise ValidationError(str(error)) from error
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
            try:
                self._save_relationships(instance, relationships_data)
            except DjangoValidationError as error:
                raise ValidationError(str(error)) from error
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
        """Ensure that "relationships" is included as an opt-in field on root serializers."""
        fields = list(super().get_field_names(declared_fields, info))
        if not self.is_nested:
            # Only include relationships as opt-in.
            self.extend_field_names(fields, "relationships", opt_in_only=True)
        else:
            # As relationships are expensive, do not include them on nested serializers even if opted in.
            if "relationships" in fields:
                fields.remove("relationships")
        return fields


class NotesSerializerMixin(BaseModelSerializer):
    """Extend Serializer with a `notes` field."""

    notes_url = serializers.SerializerMethodField()

    def get_field_names(self, declared_fields, info):
        """Ensure that fields includes "notes_url" field if applicable."""
        fields = list(super().get_field_names(declared_fields, info))
        if hasattr(self.Meta.model, "notes"):
            # Make sure the field is at the end of fields, instead of the beginning
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
                    f"2. Include NotesViewSetMixin from nautobot.extras.api.views in the {model_name}ViewSet "
                    "before including NotesSerializerMixin in the model serializer"
                )
            )

            return None


class NautobotModelSerializer(
    RelationshipModelSerializerMixin, CustomFieldModelSerializerMixin, NotesSerializerMixin, ValidatedModelSerializer
):
    """Base class to use for serializers based on OrganizationalModel or PrimaryModel.

    Can also be used for models derived from BaseModel, so long as they support custom fields, notes, and relationships.
    """


#
# Tools
#


class RenderJinjaSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """Serializer for RenderJinjaView."""

    template_code = serializers.CharField(required=True)
    context = serializers.DictField(default=dict)
    rendered_template = serializers.CharField(read_only=True)
    rendered_template_lines = serializers.ListField(read_only=True, child=serializers.CharField())
