import logging
import uuid

from django.core.exceptions import (
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.db.models import AutoField, ManyToManyField
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from nautobot.utilities.utils import dict_to_filter_params, normalize_querydict


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


class BaseModelSerializer(OptInFieldsMixin, serializers.ModelSerializer):
    """
    This base serializer implements common fields and logic for all ModelSerializers.

    Namely, it:

    - defines the `display` field which exposes a human friendly value for the given object.
    - ensures that `id` field is always present on the serializer as well
    - ensures that `created` and `last_updated` fields are always present if applicable to this model and serializer.
    """

    display = serializers.SerializerMethodField(read_only=True, help_text="Human friendly display value")

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
        # Needed because we don't have a common base class for all nested serializers vs non-nested serializers
        if not self.__class__.__name__.startswith("Nested"):
            if hasattr(self.Meta.model, "created"):
                self.extend_field_names(fields, "created")
            if hasattr(self.Meta.model, "last_updated"):
                self.extend_field_names(fields, "last_updated")
        return fields


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
