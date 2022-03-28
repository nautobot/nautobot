from django.db.models import JSONField
from drf_yasg import openapi
from drf_yasg.inspectors import (
    FieldInspector,
    NotHandled,
    PaginatorInspector,
    RelatedFieldInspector,
)

from nautobot.core.api import (
    ChoiceField,
    SerializedPKRelatedField,
)
from nautobot.extras.api.customfields import CustomFieldsDataField
from nautobot.extras.api.fields import StatusSerializerField


class SerializedPKRelatedFieldInspector(FieldInspector):
    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, use_references, **kwargs)
        if isinstance(field, SerializedPKRelatedField):
            return self.probe_field_inspectors(field.serializer(), ChildSwaggerType, use_references)

        return NotHandled


class ChoiceFieldInspector(FieldInspector):
    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        # this returns a callable which extracts title, description and other stuff
        # https://drf-yasg.readthedocs.io/en/stable/_modules/drf_yasg/inspectors/base.html#FieldInspector._get_partial_types
        SwaggerType, _ = self._get_partial_types(field, swagger_object_type, use_references, **kwargs)

        if isinstance(field, ChoiceField):
            choices = field._choices
            choice_value = list(choices.keys())
            choice_label = list(choices.values())
            value_schema = openapi.Schema(type=openapi.TYPE_STRING, enum=choice_value)

            if set([None] + choice_value) == {None, True, False}:
                # DeviceType.subdevice_role and Device.face need to be differentiated since they each have
                # subtly different values in their choice keys.
                # - subdevice_role and connection_status are booleans, although subdevice_role includes None
                # - face is an integer set {0, 1} which is easily confused with {False, True}
                schema_type = openapi.TYPE_STRING
                if all(isinstance(x, bool) for x in [c for c in choice_value if c is not None]):
                    schema_type = openapi.TYPE_BOOLEAN
                value_schema = openapi.Schema(type=schema_type, enum=choice_value)
                value_schema["x-nullable"] = True

            if all(isinstance(x, int) for x in [c for c in choice_value if c is not None]):
                # Change value_schema for IPAddressFamilyChoices, RackWidthChoices
                value_schema = openapi.Schema(type=openapi.TYPE_INTEGER, enum=choice_value)

            schema = SwaggerType(
                type=openapi.TYPE_OBJECT,
                required=["label", "value"],
                properties={
                    "label": openapi.Schema(type=openapi.TYPE_STRING, enum=choice_label),
                    "value": value_schema,
                },
            )

            return schema

        return NotHandled


class NullableBooleanFieldInspector(FieldInspector):
    def process_result(self, result, method_name, obj, **kwargs):

        if isinstance(result, openapi.Schema) and isinstance(obj, ChoiceField) and result.type == "boolean":
            keys = obj.choices.keys()
            if set(keys) == {None, True, False}:
                result["x-nullable"] = True
                result.type = "boolean"

        return result


class CustomFieldsDataFieldInspector(FieldInspector):
    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, use_references, **kwargs)

        if isinstance(field, CustomFieldsDataField) and swagger_object_type == openapi.Schema:
            return SwaggerType(type=openapi.TYPE_OBJECT)

        return NotHandled


class JSONFieldInspector(FieldInspector):
    """Required because by default, Swagger sees a JSONField as a string and not dict"""

    def process_result(self, result, method_name, obj, **kwargs):
        if isinstance(result, openapi.Schema) and isinstance(obj, JSONField):
            result.type = "dict"
        return result


class NullablePaginatorInspector(PaginatorInspector):
    def process_result(self, result, method_name, obj, **kwargs):
        if method_name == "get_paginated_response" and isinstance(result, openapi.Schema):
            next = result.properties["next"]
            if isinstance(next, openapi.Schema):
                next["x-nullable"] = True
            previous = result.properties["previous"]
            if isinstance(previous, openapi.Schema):
                previous["x-nullable"] = True

        return result


class StatusFieldInspector(RelatedFieldInspector):
    """
    Inspector for status fields, since they are writable slug-related fields
    that have choices.
    """

    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        dataobj = super().field_to_swagger_object(field, swagger_object_type, use_references, **kwargs)
        if (
            isinstance(field, StatusSerializerField)
            and hasattr(field, "choices")
            and getattr(field, "show_choices", False)
            and "enum" not in dataobj
        ):
            dataobj["enum"] = [k for k, v in field.choices.items()]

        return dataobj
