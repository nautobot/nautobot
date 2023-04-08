import logging
import uuid

from django.core.exceptions import (
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.db.models import AutoField
from rest_framework.exceptions import ValidationError

from nautobot.core.api.utils import dict_to_filter_params

logger = logging.getLogger(__name__)


class LimitQuerysetChoicesSerializerMixin:
    """Mixin field that restricts queryset choices to those accessible
    for the queryset model that implemented it."""

    def get_queryset(self):
        """Only emit options for this model/field combination."""
        queryset = super().get_queryset()
        # Get objects model e.g Site, Device... etc.
        # Tags model can be gotten using self.parent.parent, while others uses self.parent
        try:
            model = self.parent.Meta.model
        except AttributeError:
            model = self.parent.parent.Meta.model
        return queryset.get_for_model(model)


class WritableSerializerMixin:
    """
    WritableSerializerMixin provides the to_internal_value() function.
    The function provides the ability to write API requests that identify unique objects based on
    combinations of fields other than the primary key.
    e.g:
    "parent": { "location_type__parent": {"name": "Campus"}, "parent__name": "Campus-29" }
    vs
    "parent": "10dff139-7333-46b0-bef6-f6a5a7b5497c"
    """

    def get_unique_object_from_data(self, data):
        if isinstance(data, dict):
            params = dict_to_filter_params(data)
        else:
            params = {"id": uuid.UUID(data)}
        if hasattr(self, "fields"):
            for field_name, field_instance in self.fields.items():
                if field_name in params and field_instance.source == "*":
                    logger.debug("Discarding non-database field %s", field_name)
                    del params[field_name]

        if hasattr(self, "queryset"):
            queryset = self.queryset
        else:
            queryset = self.Meta.model.objects
        model_name = queryset.model._meta.model_name
        try:
            return queryset.get(**params)
        except ObjectDoesNotExist:
            raise ValidationError(
                {f"{model_name}": f"Related object not found using the provided attributes: {params}"}
            )
        except MultipleObjectsReturned:
            raise ValidationError({f"{model_name}": f"Multiple objects match the provided attributes: {params}"})
        except FieldError as e:
            raise ValidationError({f"{model_name}": e})

    def to_internal_value(self, data):
        if data is None:
            return None

        # Dictionary of related object attributes
        if isinstance(data, dict):
            result = self.get_unique_object_from_data(data)
            return result

        # List of dictionary objects like tags or contenttypes
        if isinstance(data, list):
            result = []
            for entry in data:
                result.append(self.get_unique_object_from_data(entry))
            return result

        if hasattr(self, "queryset"):
            queryset = self.queryset
        else:
            queryset = self.Meta.model.objects
        model_name = queryset.model._meta.model_name
        pk = None

        if isinstance(queryset.model._meta.pk, AutoField):
            # PK is an int for this model. This is usually the User model
            try:
                pk = int(data)
            except (TypeError, ValueError):
                raise ValidationError(
                    {
                        f"{model_name}": "Related objects must be referenced by ID or by dictionary of attributes. Received an "
                        f"unrecognized value: {data}"
                    }
                )

        else:
            # We assume a type of UUIDField for all other models

            # PK of related object
            try:
                # Ensure the pk is a valid UUID
                pk = uuid.UUID(str(data))
            except (TypeError, ValueError):
                raise ValidationError(
                    {
                        f"{model_name}": "Related objects must be referenced by ID or by dictionary of attributes. Received an "
                        f"unrecognized value: {data}"
                    }
                )
        try:
            return queryset.get(pk=pk)
        except ObjectDoesNotExist:
            raise ValidationError({f"{model_name}": f"Related object not found using the provided ID: {pk}"})
