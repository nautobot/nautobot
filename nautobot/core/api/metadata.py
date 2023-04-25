from typing import Any, Dict, List

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.encoding import force_str
from drf_react_template.schema_form_encoder import SchemaProcessor, SerializerType, UiSchemaProcessor
from rest_framework import exceptions
from rest_framework import fields as drf_fields
from rest_framework import serializers as drf_serializers
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request

from nautobot.core.api import ContentTypeField


class NautobotMetadataV1(SimpleMetadata):
    def determine_actions(self, request, view):
        """
        Replace the stock determine_actions() method to assess object permissions only
        when viewing a specific object. This is necessary to support OPTIONS requests
        with bulk update in place (see #5470).
        """
        actions = {}
        for method in {"PUT", "POST"} & set(view.allowed_methods):
            view.request = clone_request(request, method)
            try:
                # Test global permissions
                if hasattr(view, "check_permissions"):
                    view.check_permissions(view.request)
                # Test object permissions (if viewing a specific object)
                if method == "PUT" and view.lookup_url_kwarg and hasattr(view, "get_object"):
                    view.get_object()
            except (exceptions.APIException, PermissionDenied, Http404):
                pass
            else:
                # If user has appropriate permissions for the view, include
                # appropriate metadata about the fields that should be supplied.
                serializer = view.get_serializer()
                actions[method] = self.get_serializer_info(serializer)
            finally:
                view.request = request

        return actions

    def get_field_info(self, field):
        """
        Fixup field information:

        - Set choices for ContentTypeField.
        - Replace DRF choices `display_name` to `display` to match new pattern.
        """
        field_info = super().get_field_info(field)
        for choice in field_info.get("choices", []):
            choice["display"] = choice.pop("display_name")
        if hasattr(field, "queryset") and not field_info.get("read_only") and isinstance(field, ContentTypeField):
            field_info["choices"] = [
                {
                    "value": choice_value,
                    "display": force_str(choice_name, strings_only=True),
                }
                for choice_value, choice_name in field.choices.items()
            ]
            field_info["choices"].sort(key=lambda item: item["display"])
        return field_info


class NautobotSchemaProcessor(SchemaProcessor):
    """
    SchemaProcessor to account for custom field types and behaviors for Nautobot.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # FIXME(jathan): These custom type maps can go into # settings.DRF_REACT_TEMPLATE_TYPE_MAP.
        self.TYPE_MAP.update(
            {
                "ContentTypeField": {"type": "string", "enum": "choices"},
                "CustomFieldsDataField": {"type": "object"},
                "ManyRelatedField": {"type": "array", "required": []},
                "NautobotPrimaryKeyRelatedField": {"type": "string", "enum": "choices"},
                "PrimaryKeyRelatedField": {"type": "string", "enum": "choices"},
                "RelationshipsDataField": {"type": "object"},
                "SlugField": {"type": "string"},
                "TimeZoneSerializerField": {"type": "string"},
                "UUIDField": {"type": "string"},
            }
        )

    # FIXME(jathan): For these methods there was a need to account for certain field types/values
    # such a "required" fields and "array" types. Need tox revisit the original source from
    # drf_react_template to see if we can reduct the overloaded code back down.
    def _get_type_map_value(self, field: SerializerType):
        result = {
            "type": field.style.get("schema:type"),
            "enum": field.style.get("schema:enum"),
            "widget": field.style.get("ui:widget"),
            "required": field.style.get("schema:required"),
        }
        result_default = self.TYPE_MAP.get(type(field).__name__, {})
        for k in result_default:
            if result[k] is None:
                result[k] = result_default[k]
        return result

    def _get_field_properties(self, field: SerializerType, name: str) -> Dict[str, Any]:
        result = {}
        type_map_obj = self._get_type_map_value(field)
        result["type"] = type_map_obj["type"]
        result["title"] = self._get_title(field, name)

        if isinstance(field, drf_serializers.ListField):
            if field.allow_empty:
                result["required"] = not getattr(field, "allow_empty", True)
            result["items"] = self._get_field_properties(field.child, "")
            result["uniqueItems"] = True
        elif isinstance(field, drf_serializers.ManyRelatedField):
            if field.allow_empty:
                result["required"] = type_map_obj.get("required", [])
            result["items"] = self._get_field_properties(field.child_relation, "")
            result["uniqueItems"] = True
        else:
            if field.allow_null:
                result["type"] = [result["type"], "null"]
            enum = type_map_obj.get("enum")
            if enum:
                if enum == "choices":
                    choices = field.choices
                    result["enum"] = list(choices.keys())
                    result["enumNames"] = list(choices.values())
                if isinstance(enum, (list, tuple)):
                    if isinstance(enum, (list, tuple)):
                        result["enum"] = [item[0] for item in enum]
                        result["enumNames"] = [item[1] for item in enum]
                    else:
                        result["enum"] = enum
                        result["enumNames"] = list(enum)
            try:
                result["default"] = field.get_default()
            except drf_fields.SkipField:
                pass

        result = self._set_validation_properties(field, result)

        return result


class NautobotUiSchemaProcessor(UiSchemaProcessor):
    """
    UiSchemaProcessor to account for custom field types and behaviors for Nautobot.
    """

    def _field_order(self) -> List[str]:
        """
        Overload the base which just returns `Meta.fields` and doesn't play nicely with "__all__".

        This instead calls `get_fields()` and returns the keys.
        """
        if self._is_list_serializer(self.serializer):
            return list(self.serializer.child.get_fields())
        return list(self.serializer.get_fields())

    # FIXME(jathan): For this method there was a need to account for certain field types/values
    # such a "required" fields. Need tox revisit the original source from drf_react_template to see
    # if we can reduct the overloaded code back down.
    def _get_type_map_value(self, field: SerializerType):
        result = {
            "type": field.style.get("schema:type"),
            "enum": field.style.get("schema:enum"),
            "widget": field.style.get("ui:widget"),
            "required": field.style.get("schema:required"),
        }
        result_default = self.TYPE_MAP.get(type(field).__name__, {})
        for k in result_default:
            if result[k] is None:
                result[k] = result_default[k]
        return result


class NautobotMetadata(SimpleMetadata):
    """
    Metadata class that emits JSON schema. It contains `schema` and `uiSchema` keys where:

    - schema: The object JSON schema
    - uiSchema: The object UI schema which describes the form layout in the UI
    """

    def determine_metadata(self, request, view):
        # If there's a serializer, do the needful.
        if hasattr(view, "get_serializer"):
            serializer = view.get_serializer()
            return {
                "schema": NautobotSchemaProcessor(serializer, request.parser_context).get_schema(),
                "uiSchema": NautobotUiSchemaProcessor(serializer, request.parser_context).get_ui_schema(),
            }
        # Otherwise return the default DRF metadata for this view.
        return super().determine_metadata(request, view)
