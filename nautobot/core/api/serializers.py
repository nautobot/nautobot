import uuid

from django.core.exceptions import (
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.db.models import AutoField, ManyToManyField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from nautobot.utilities.utils import dict_to_filter_params


class ValidatedModelSerializer(serializers.ModelSerializer):
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


class WritableNestedSerializer(serializers.ModelSerializer):
    """
    Returns a nested representation of an object on read, but accepts only a primary key on write.
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
                pk = uuid.UUID(str(data), version=4)
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
