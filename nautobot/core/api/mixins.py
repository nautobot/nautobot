import logging
import uuid

from django.core.exceptions import (
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.db.models import AutoField
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from nautobot.core.api.utils import dict_to_filter_params, get_serializer_for_model
from nautobot.core.utils.data import is_url

logger = logging.getLogger(__name__)


class DetailViewConfigMixin:
    @action(detail=True, url_path="detail-view-config")
    def detail_view_config(self, request, pk):
        """
        Return a JSON of the ObjectDetailView configuration
        """
        obj = get_object_or_404(self.queryset, pk=pk)
        obj_serializer_class = get_serializer_for_model(obj)
        obj_serializer = obj_serializer_class(data=None)
        response = self.get_detail_view_config(obj_serializer)
        response = Response(response)
        return response

    def get_detail_view_config(self, obj_serializer):
        all_fields = list(obj_serializer.get_fields().keys())
        header_fields = ["display", "status", "created", "last_updated"]
        extra_fields = ["object_type", "relationships", "computed_fields", "custom_fields"]
        advanced_fields = ["id", "url", "display", "natural_key_slug", "slug", "notes_url"]
        plugin_tab_1_fields = ["field_1", "field_2", "field_3"]
        plugin_tab_2_fields = ["field_1", "field_2", "field_3"]
        main_fields = [
            field
            for field in all_fields
            if field not in header_fields and field not in extra_fields and field not in advanced_fields
        ]
        response = {
            "main": [
                {
                    "name": obj_serializer.Meta.model._meta.model_name,
                    "fields": main_fields,
                    "colspan": 2,
                    "rowspan": len(main_fields),
                },
                {
                    "name": "extra",
                    "fields": extra_fields,
                    "colspan": 2,
                    "rowspan": len(extra_fields),
                },
            ],
            "advanced": [
                {
                    "name": "advanced data",
                    "fields": advanced_fields,
                    "colspan": 3,
                    "rowspan": len(advanced_fields),
                    "advanced": "true",
                }
            ],
            "plugin_tab_1": [
                {
                    "name": "plugin_data",
                    "fields": plugin_tab_1_fields,
                    "colspan": 3,
                    "rowspan": len(plugin_tab_1_fields),
                },
                {
                    "name": "extra_plugin_data",
                    "fields": plugin_tab_1_fields,
                    "colspan": 1,
                    "rowspan": len(plugin_tab_1_fields),
                },
            ],
            "plugin_tab_2": [
                {
                    "name": "plugin_data",
                    "fields": plugin_tab_2_fields,
                    "colspan": 3,
                    "rowspan": len(plugin_tab_2_fields),
                }
            ],
        }
        return response


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
        if isinstance(data, list):
            return [self.get_object(data=entry, queryset=queryset) for entry in data]
        return self.get_object(data=data, queryset=queryset)
