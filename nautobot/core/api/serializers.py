import uuid

from django.core.exceptions import (
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.db.models import AutoField, ManyToManyField
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from nautobot.utilities.utils import dict_to_filter_params


class OptInFieldsMixin:
    """
    A serializer mixin that takes an additional `opt_in_fields` argument that controls
    which fields should be displayed.
    """

    @property
    def fields(self):
        """
        Removes all serializer fields specified in a serializers `opt_in_fields` list that aren't specified in the
        `include` query parameter.

        As an example, if the serializer specifies that `opt_in_fields = ["computed_fields"]`
        but `computed_fields` is not specified in the `?include` query parameter, `computed_fields` will be popped
        from the list of fields.
        """
        fields = super().fields
        serializer_opt_in_fields = getattr(self.Meta, "opt_in_fields", None)

        if not serializer_opt_in_fields:
            return fields

        if not hasattr(self, "_context"):
            # We are being called before a request cycle
            return fields

        try:
            request = self.context["request"]
        except KeyError:
            return fields

        request = self.context["request"]

        # NOTE: drf test framework builds a request object where the query
        # parameters are found under the GET attribute.
        params = getattr(request, "query_params", getattr(request, "GET", None))

        try:
            user_opt_in_fields = params.get("include", None).split(",")
        except AttributeError:
            user_opt_in_fields = []

        # Drop any fields that are not specified in the users opt in fields
        for field in serializer_opt_in_fields:
            if field not in user_opt_in_fields:
                fields.pop(field, None)

        return fields


class BaseModelSerializer(OptInFieldsMixin, serializers.ModelSerializer):
    """
    This base serializer implements common fields and logic for all ModelSerializers.
    Namely it defines the `display` field which exposes a human friendly value for the given object.
    """

    display = serializers.SerializerMethodField(read_only=True, help_text="Human friendly display value")

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_display(self, instance):
        """
        Return either the `display` property of the instance or `str(instance)`
        """
        return getattr(instance, "display", str(instance))

    def get_field_names(self, declared_fields, info):
        """
        Override get_field_names() to append the `display` field so it is always included in the
        serializer's `Meta.fields`.

        DRF does not automatically add declared fields to `Meta.fields`, nor does it require that declared fields
        on a super class be included in `Meta.fields` to allow for a subclass to include only a subset of declared
        fields from the super. This means either we intercept and append the display field at this level, or
        enforce by convention that all consumers of BaseModelSerializer include `display` in their `Meta.fields`
        which would surely lead to errors of omission; therefore we have chosen the former approach.
        """
        fields = list(super().get_field_names(declared_fields, info))  # Meta.fields could be defined as a tuple
        fields.append("display")

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

    def to_internal_value(self, data):

        if data is None:
            return None

        # Dictionary of related object attributes
        if isinstance(data, dict):
            params = dict_to_filter_params(data)
            queryset = self.Meta.model.objects
            try:
                return queryset.get(**params)
            except ObjectDoesNotExist:
                raise ValidationError("Related object not found using the provided attributes: {}".format(params))
            except MultipleObjectsReturned:
                raise ValidationError("Multiple objects match the provided attributes: {}".format(params))
            except FieldError as e:
                raise ValidationError(e)

        queryset = self.Meta.model.objects
        pk = None

        if isinstance(self.Meta.model._meta.pk, AutoField):
            # PK is an int for this model. This is usually the User model
            try:
                pk = int(data)
            except (TypeError, ValueError):
                raise ValidationError(
                    "Related objects must be referenced by ID or by dictionary of attributes. Received an "
                    "unrecognized value: {}".format(data)
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
                    "unrecognized value: {}".format(data)
                )

        try:
            return queryset.get(pk=pk)
        except ObjectDoesNotExist:
            raise ValidationError("Related object not found using the provided ID: {}".format(pk))


class BulkOperationSerializer(serializers.Serializer):
    id = serializers.CharField()  # This supports both UUIDs and numeric ID for the User model


#
# GraphQL, used by the openapi doc, not by the view
#


class GraphQLAPISerializer(serializers.Serializer):
    query = serializers.CharField(required=True, help_text="GraphQL query")
    variables = serializers.JSONField(required=False, help_text="Variables in JSON Format")
