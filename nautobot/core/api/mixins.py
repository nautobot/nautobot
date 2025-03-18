import logging
import uuid

from django.core.exceptions import (
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.db.models import AutoField, Model
from rest_framework.exceptions import ValidationError

from nautobot.core.api.utils import dict_to_filter_params
from nautobot.core.utils.data import is_url

logger = logging.getLogger(__name__)


class LimitQuerysetChoicesSerializerMixin:
    """Mixin field that restricts queryset choices to those accessible
    for the queryset model that implemented it."""

    def get_queryset(self):
        """Only emit options for this model/field combination."""
        queryset = super().get_queryset()
        # Get objects model e.g Location, Device... etc.
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

    def remove_non_filter_fields(self, filter_params):
        """
        Make output from a WritableSerializer "round-trip" capable by automatically stripping from the
        data any serializer fields that do not correspond to a specific model field
        """
        if hasattr(self, "fields"):
            for field_name, field_instance in self.fields.items():
                if field_name in filter_params and field_instance.source == "*":
                    logger.debug("Discarding non-filter field %s", field_name)
                    del filter_params[field_name]
        return filter_params

    def get_queryset_filter_params(self, data, queryset):
        """
        Data could be a dictionary and an int (for the User model) or a str that represents the primary key.
        If it is a dictionary, we return it after remove non-filter fields.
        If it is a primary key, we return a dictionary object formatted like this {"pk": pk}
        """

        if isinstance(data, dict):
            params = dict_to_filter_params(data)
            return self.remove_non_filter_fields(params)

        # Account for the fact that HyperlinkedIdentityFields might pass in URLs.
        if is_url(data):
            # Strip the trailing slash and split on slashes, taking the last value as the PK.
            data = data.rstrip("/").split("/")[-1]

        # If we're passing the validated_data from one serializer as input to another serializer,
        # data might already be a model instance:
        if isinstance(data, Model):
            return {"pk": data.pk}

        try:
            # The int case here is taking into account for the User model we inherit from django
            pk = int(data) if isinstance(queryset.model._meta.pk, AutoField) else uuid.UUID(str(data))
        except (TypeError, ValueError) as e:
            raise ValidationError(
                "Related objects must be referenced by ID or by dictionary of attributes. Received an "
                f"unrecognized value: {data}"
            ) from e
        return {"pk": pk}

    def get_object(self, data, queryset):
        """
        Retrieve an unique object based on a dictionary of data attributes and raise errors accordingly if the object is not found.
        """
        filter_params = self.get_queryset_filter_params(data=data, queryset=queryset)
        try:
            return queryset.get(**filter_params)
        except ObjectDoesNotExist as e:
            raise ValidationError(f"Related object not found using the provided attributes: {filter_params}") from e
        except MultipleObjectsReturned as e:
            raise ValidationError(f"Multiple objects match the provided attributes: {filter_params}") from e
        except FieldError as e:
            raise ValidationError(e) from e

    def to_internal_value(self, data):
        """
        Return an object or a list of objects based on a dictionary of data attributes or an UUID.
        """
        if data is None:
            return None
        if hasattr(self, "queryset"):
            queryset = self.queryset
        else:
            queryset = self.Meta.model.objects

        # Apply user permission on related objects
        if (
            "request" in self.context
            and self.context["request"]
            and self.context["request"].user
            and hasattr(queryset, "restrict")
        ):
            queryset = queryset.restrict(self.context["request"].user, "view")

        if isinstance(data, list):
            return [self.get_object(data=entry, queryset=queryset) for entry in data]
        return self.get_object(data=data, queryset=queryset)
